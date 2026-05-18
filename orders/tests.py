import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings

from .models import CustomerProfile, EmailOTP, Order, OrderReview


EMAIL_TEST_SETTINGS = {
    'EMAIL_BACKEND': 'django.core.mail.backends.locmem.EmailBackend',
    'DEFAULT_FROM_EMAIL': 'Gagah Home Made-Biko <sender@example.com>',
}


@override_settings(**EMAIL_TEST_SETTINGS)
class EmailSendingTests(TestCase):
    def post_json(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_send_email_otp_creates_code_and_sends_email(self):
        response = self.post_json('/send-email-otp/', {'email': 'Customer@Example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        otp = EmailOTP.objects.get(email='customer@example.com')
        self.assertEqual(len(otp.otp_code), 6)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['customer@example.com'])
        self.assertIn(otp.otp_code, mail.outbox[0].body)

    def test_password_reset_email_uses_current_host(self):
        User.objects.create_user(
            username='customer@example.com',
            email='customer@example.com',
            password='password12345',
            first_name='Customer',
        )

        response = self.post_json(
            '/send-reset-email/',
            {'email': 'customer@example.com'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('http://testserver/reset-password/', mail.outbox[0].body)


class AuthProfileTests(TestCase):
    def post_json(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_update_profile_preserves_full_name(self):
        user = User.objects.create_user(
            username='old@example.com',
            email='old@example.com',
            password='password12345',
        )
        self.client.login(username='old@example.com', password='password12345')

        response = self.post_json('/update-profile/', {
            'full_name': 'Jistin Gwapo',
            'email': 'jistin@example.com',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(response.json()['name'], 'Jistin Gwapo')
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Jistin')
        self.assertEqual(user.last_name, 'Gwapo')
        self.assertEqual(user.customer_profile.full_name, 'Jistin Gwapo')

    def test_login_can_create_persistent_session(self):
        user = User.objects.create_user(
            username='buyer@example.com',
            email='buyer@example.com',
            password='password12345',
            first_name='Jistin',
            last_name='Gwapo',
        )
        CustomerProfile.objects.update_or_create(
            user=user,
            defaults={'full_name': 'Jistin Gwapo'},
        )

        response = self.post_json('/login-user/', {
            'email': 'buyer@example.com',
            'password': 'password12345',
            'keep_logged_in': True,
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(response.json()['full_name'], 'Jistin Gwapo')
        self.assertFalse(self.client.session.get_expire_at_browser_close())


@override_settings(
    PAYMONGO_SECRET_KEY='sk_test_example',
    PAYMONGO_API_BASE_URL='https://api.paymongo.test',
    PAYMONGO_CURRENCY='PHP',
)
class PayMongoCheckoutTests(TestCase):
    def post_json(self, path, payload):
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type='application/json',
        )

    @patch('orders.views.urlopen')
    def test_gcash_checkout_creates_paymongo_session(self, mock_urlopen):
        user = User.objects.create_user(
            username='buyer@example.com',
            email='buyer@example.com',
            password='password12345',
        )
        self.client.login(username='buyer@example.com', password='password12345')

        response_obj = MagicMock()
        response_obj.read.return_value = json.dumps({
            'data': {
                'id': 'cs_test_123',
                'attributes': {'checkout_url': 'https://checkout.paymongo.test/cs_test_123'},
            }
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = response_obj

        response = self.post_json('/create-paymongo-checkout-session/', {
            'full_name': 'Test Buyer',
            'email': 'buyer@example.com',
            'phone': '09171234567',
            'address': 'Espina Street',
            'apartment': '',
            'city': 'Surigao City',
            'postal_code': '8400',
            'shipping_method': 'standard',
            'payment_method': 'gcash',
            'subtotal': 100,
            'shipping_fee': 50,
            'total': 150,
            'items': [{'product_name': 'Biko Bilao', 'quantity': 1, 'price': 100}],
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(response.json()['checkout_url'], 'https://checkout.paymongo.test/cs_test_123')
        order = Order.objects.get()
        self.assertEqual(order.payment_status, 'pending')
        self.assertEqual(order.paymongo_checkout_session_id, 'cs_test_123')

    @patch('orders.views.urlopen')
    def test_order_success_marks_paid_from_nested_payment_intent_status(self, mock_urlopen):
        order = Order.objects.create(
            full_name='Test Buyer',
            email='buyer@example.com',
            phone='09171234567',
            address='Espina Street',
            city='Surigao City',
            postal_code='8400',
            shipping_method='standard',
            payment_method='gcash',
            payment_status='pending',
            paymongo_checkout_session_id='cs_test_123',
            subtotal=100,
            shipping_fee=50,
            total=150,
        )

        response_obj = MagicMock()
        response_obj.read.return_value = json.dumps({
            'data': {
                'id': 'cs_test_123',
                'attributes': {
                    'status': 'active',
                    'payment_intent': {
                        'id': 'pi_test_123',
                        'attributes': {'status': 'succeeded'},
                    },
                },
            }
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = response_obj

        response = self.client.get(f'/order-success/?id={order.id}&paymongo=1')
        order.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.paymongo_payment_intent_id, 'pi_test_123')


class OrderReviewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer@example.com',
            email='buyer@example.com',
            password='password12345',
        )
        self.client.login(username='buyer@example.com', password='password12345')

    def create_order(self, status='delivered'):
        return Order.objects.create(
            user=self.user,
            full_name='Test Buyer',
            email='buyer@example.com',
            phone='09171234567',
            address='Espina Street',
            city='Surigao City',
            postal_code='8400',
            shipping_method='standard',
            payment_method='cod',
            payment_status='paid',
            subtotal=100,
            shipping_fee=50,
            total=150,
            status=status,
        )

    def test_customer_can_review_delivered_order_once(self):
        order = self.create_order(status='delivered')

        response = self.client.post(
            f'/my-orders/{order.id}/review/',
            {'rating': '5', 'comment': 'Fresh and well packed.'},
        )

        self.assertEqual(response.status_code, 302)
        review = OrderReview.objects.get(order=order)
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.rating, 5)

        self.client.post(
            f'/my-orders/{order.id}/review/',
            {'rating': '1', 'comment': 'Second review should not replace it.'},
        )

        review.refresh_from_db()
        self.assertEqual(OrderReview.objects.filter(order=order).count(), 1)
        self.assertEqual(review.rating, 5)

    def test_customer_cannot_review_before_delivery(self):
        order = self.create_order(status='shipped')

        response = self.client.post(
            f'/my-orders/{order.id}/review/',
            {'rating': '5', 'comment': 'Too early.'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(OrderReview.objects.filter(order=order).exists())

    def test_order_history_shows_progress_and_review_form_after_delivery(self):
        order = self.create_order(status='delivered')

        response = self.client.get('/my-orders/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Order progress')
        self.assertContains(response, f'/my-orders/{order.id}/review/')
        self.assertContains(response, 'How was your order?')

    @patch('orders.views.urlopen')
    def test_order_success_retrieves_payment_intent_when_session_has_only_intent_id(self, mock_urlopen):
        order = Order.objects.create(
            full_name='Test Buyer',
            email='buyer@example.com',
            phone='09171234567',
            address='Espina Street',
            city='Surigao City',
            postal_code='8400',
            shipping_method='standard',
            payment_method='gcash',
            payment_status='pending',
            paymongo_checkout_session_id='cs_test_123',
            subtotal=100,
            shipping_fee=50,
            total=150,
        )

        session_response = MagicMock()
        session_response.read.return_value = json.dumps({
            'data': {
                'id': 'cs_test_123',
                'attributes': {
                    'status': 'active',
                    'payment_intent_id': 'pi_test_123',
                },
            }
        }).encode('utf-8')
        intent_response = MagicMock()
        intent_response.read.return_value = json.dumps({
            'data': {
                'id': 'pi_test_123',
                'attributes': {'status': 'succeeded'},
            }
        }).encode('utf-8')
        mock_urlopen.return_value.__enter__.side_effect = [
            session_response,
            intent_response,
        ]

        response = self.client.get(f'/order-success/?id={order.id}&paymongo=1')
        order.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.status, 'confirmed')
        self.assertEqual(order.paymongo_payment_intent_id, 'pi_test_123')
