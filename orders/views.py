import json
import base64
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMultiAlternatives, send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from .models import Order, OrderItem, OrderReview, EmailOTP, CustomerProfile
import random


def split_full_name(full_name):
    name_parts = full_name.strip().split(' ', 1)
    return (
        name_parts[0] if name_parts else '',
        name_parts[1] if len(name_parts) > 1 else '',
    )


def customer_display_name(user):
    if hasattr(user, 'customer_profile') and user.customer_profile.full_name:
        return user.customer_profile.full_name
    return user.get_full_name().strip() or user.email or user.username


@ensure_csrf_cookie
def home(request):
    return render(request, 'index.html')

@ensure_csrf_cookie
def menu(request):
    return render(request, 'menu.html')

@ensure_csrf_cookie
def about(request):
    return render(request, 'about.html')

def generate_otp():
    return str(random.randint(100000, 999999))


def send_templated_email(subject, template_name, context, recipient):
    text_body = render_to_string(f'emails/{template_name}.txt', context)
    html_body = render_to_string(f'emails/{template_name}.html', context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html_body, 'text/html')
    message.send(fail_silently=False)


def decimal_from_payload(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return Decimal('0')


def create_order_from_payload(data, user=None):
    items = data.get('items', [])
    if not items:
        raise ValueError('Your cart is empty.')

    order = Order.objects.create(
        user=user if user and user.is_authenticated else None,
        full_name=data.get('full_name'),
        email=data.get('email'),
        phone=data.get('phone'),
        address=data.get('address'),
        apartment=data.get('apartment', ''),
        city=data.get('city'),
        postal_code=data.get('postal_code'),
        shipping_method=data.get('shipping_method'),
        payment_method=data.get('payment_method'),
        gcash_reference=data.get('gcash_reference', '').strip(),
        subtotal=decimal_from_payload(data.get('subtotal')),
        shipping_fee=decimal_from_payload(data.get('shipping_fee')),
        total=decimal_from_payload(data.get('total')),
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            product_name=item.get('product_name') or 'Biko Item',
            quantity=int(item.get('quantity') or 1),
            price=decimal_from_payload(item.get('price')),
        )

    return order


def send_order_confirmation(order):
    items_text = '\n'.join([
        f"  - {item.product_name} x{item.quantity} "
        f"= ₱{item.price * item.quantity}"
        for item in OrderItem.objects.filter(order=order)
    ])

    subject = f"Order Confirmed! #{order.id} — Gagah Home Made-Biko"
    message = f"""
Hi {order.full_name},

Thank you for your order!

ORDER DETAILS
─────────────────────────────
Order ID    : #{order.id}
Date        : {order.created_at.strftime('%B %d, %Y %I:%M %p')}
Status      : {order.status.upper()}

ITEMS ORDERED
─────────────────────────────
{items_text}

─────────────────────────────
Subtotal    : ₱{order.subtotal}
Shipping    : ₱{order.shipping_fee}
TOTAL       : ₱{order.total}
─────────────────────────────

SHIPPING ADDRESS
{order.full_name}
{order.address}
{order.apartment}
{order.city} {order.postal_code}

SHIPPING METHOD
{'Standard Delivery (3-5 Business Days)' if order.shipping_method == 'standard' else 'Express Delivery (Next Day)'}

We will contact you at {order.phone}
to confirm your order shortly.

From our family kitchen to your table —
thank you for supporting Gagah Home Made-Biko!

— The Gagah Home Made-Biko Team
Espina Street, Surigao City, Surigao Del Norte
"""

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [order.email],
        fail_silently=True,
    )


def payment_amount(value):
    return int((Decimal(value).quantize(Decimal('0.01'))) * 100)


def paymongo_auth_header():
    token = base64.b64encode(f'{settings.PAYMONGO_SECRET_KEY}:'.encode('utf-8')).decode('utf-8')
    return f'Basic {token}'


def paymongo_request(path, method='GET', payload=None):
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    request_obj = Request(
        f'{settings.PAYMONGO_API_BASE_URL}{path}',
        data=data,
        headers={
            'Authorization': paymongo_auth_header(),
            'Content-Type': 'application/json',
        },
        method=method,
    )
    with urlopen(request_obj, timeout=20) as response:
        return json.loads(response.read().decode('utf-8'))


def get_paymongo_checkout_session(session_id):
    return paymongo_request(f'/v1/checkout_sessions/{session_id}')


def paymongo_status_from_session(session):
    attributes = session.get('data', {}).get('attributes', {})
    paid_statuses = {'paid', 'succeeded', 'success', 'completed', 'complete'}
    statuses = [
        attributes.get('payment_status'),
        attributes.get('status'),
    ]

    payment_intent = attributes.get('payment_intent') or {}
    payment_intent_attrs = payment_intent.get('attributes', {}) if isinstance(payment_intent, dict) else {}
    statuses.extend([
        payment_intent_attrs.get('payment_status'),
        payment_intent_attrs.get('status'),
    ])

    payments = attributes.get('payments') or {}
    payment_items = payments.get('data', []) if isinstance(payments, dict) else []
    for payment in payment_items:
        payment_attrs = payment.get('attributes', {}) if isinstance(payment, dict) else {}
        statuses.extend([
            payment_attrs.get('payment_status'),
            payment_attrs.get('status'),
        ])
        if payment_attrs.get('paid_at'):
            return 'paid'

    normalized_statuses = [
        str(status).strip().lower()
        for status in statuses
        if status
    ]
    for status in normalized_statuses:
        if status in paid_statuses:
            return status

    return normalized_statuses[0] if normalized_statuses else ''


def get_paymongo_payment_intent(payment_intent_id):
    return paymongo_request(f'/v1/payment_intents/{payment_intent_id}')


def paymongo_status_from_payment_intent(payment_intent):
    attributes = payment_intent.get('data', {}).get('attributes', {})
    status = str(attributes.get('status') or '').strip().lower()
    if status:
        return status

    payments = attributes.get('payments') or {}
    payment_items = payments.get('data', []) if isinstance(payments, dict) else []
    for payment in payment_items:
        payment_attrs = payment.get('attributes', {}) if isinstance(payment, dict) else {}
        payment_status = str(payment_attrs.get('status') or '').strip().lower()
        if payment_status:
            return payment_status
        if payment_attrs.get('paid_at'):
            return 'paid'

    return ''


def paymongo_payment_intent_id(session):
    attributes = session.get('data', {}).get('attributes', {})
    payment_intent = attributes.get('payment_intent') or {}
    if isinstance(payment_intent, dict):
        return payment_intent.get('id') or attributes.get('payment_intent_id') or ''
    return attributes.get('payment_intent_id') or ''

@require_POST
def send_email_otp(request):
    try:
        data  = json.loads(request.body)
        email = data.get('email', '').strip().lower()

        if not email:
            return JsonResponse({'success': False, 'error': 'Email address is required.'})

        # Delete old OTPs for this email
        EmailOTP.objects.filter(email=email).delete()

        # Generate new OTP
        otp = generate_otp()

        # Save to database
        EmailOTP.objects.create(
            email=email,
            otp_code=otp
        )

        subject = "Your Verification Code - Gagah Home Made-Biko"
        send_templated_email(
            subject,
            'email_otp',
            {'otp': otp},
            email,
        )

        return JsonResponse({'success': True, 'message': f'Verification code sent to {email}.'})

    except Exception as e:
        print("SEND OTP ERROR:", str(e))
        return JsonResponse({'success': False, 'error': 'Failed to send verification email.'}, status=500)

@require_POST
def verify_email_otp(request):
    try:
        data      = json.loads(request.body)
        email     = data.get('email', '').strip().lower()
        otp_input = data.get('otp_code', '').strip()

        if not email or not otp_input:
            return JsonResponse({'success': False, 'error': 'Email and code are required.'})

        try:
            otp_record = EmailOTP.objects.filter(email=email, is_verified=False).latest('created_at')
        except EmailOTP.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'No verification code found. Please request a new one.'})

        if otp_record.attempts >= 5:
            otp_record.delete()
            return JsonResponse({'success': False, 'error': 'Too many attempts. Please request a new code.'})

        if otp_record.is_expired():
            otp_record.delete()
            return JsonResponse({'success': False, 'error': 'Code has expired. Please request a new one.'})

        otp_record.attempts += 1
        otp_record.save()

        if otp_record.otp_code != otp_input:
            remaining = 5 - otp_record.attempts
            return JsonResponse({'success': False, 'error': f'Incorrect code. {remaining} attempts remaining.'})

        otp_record.is_verified = True
        otp_record.save()
        return JsonResponse({'success': True, 'message': 'Email verified successfully!'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@ensure_csrf_cookie
def contact(request):
    return render(request, 'contact.html')

@ensure_csrf_cookie
def signup_page(request):
    return render(request, 'signup.html')

@ensure_csrf_cookie
def login_page(request):
    return render(request, 'login.html')

@ensure_csrf_cookie
@login_required(login_url='/login/')
def checkout_page(request):
    return render(request, 'checkout.html', {
        'paymongo_public_key': settings.PAYMONGO_PUBLIC_KEY,
    })

@ensure_csrf_cookie
def cart_page(request):
    return render(request, 'cart.html')

@require_POST
def place_order(request):
    try:
        data = json.loads(request.body)
        payment_method = data.get('payment_method')
        if payment_method == 'gcash':
            return JsonResponse({
                'success': False,
                'error': 'Please use PayMongo GCash checkout for GCash payments.',
            }, status=400)

        order = create_order_from_payload(data, request.user)

        # After order is saved, send confirmation email:
        try:
            send_order_confirmation(order)
        except Exception as email_error:
            print("EMAIL ERROR:", str(email_error))
            # Don't fail the order if email fails
            
        return JsonResponse({'success': True, 'order_id': order.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@require_POST
@login_required(login_url='/login/')
def create_paymongo_checkout_session(request):
    if not settings.PAYMONGO_SECRET_KEY:
        return JsonResponse({
            'success': False,
            'error': 'PayMongo is not configured. Add PAYMONGO_SECRET_KEY to .env.',
        }, status=500)

    try:
        data = json.loads(request.body)
        payment_method = data.get('payment_method')
        if payment_method != 'gcash':
            return JsonResponse({'success': False, 'error': 'PayMongo checkout is only configured for GCash.'}, status=400)

        with transaction.atomic():
            order = create_order_from_payload(data, request.user)
            order.payment_status = 'pending'
            order.save(update_fields=['payment_status'])

        base_url = request.build_absolute_uri('/').rstrip('/')
        success_url = f'{base_url}/order-success/?id={order.id}&paymongo=1'
        cancel_url = f'{base_url}/checkout/?payment_cancelled=1'

        line_items = []
        for index, item in enumerate(order.items.all()):
            line_items.append({
                'currency': settings.PAYMONGO_CURRENCY,
                'amount': payment_amount(item.price),
                'name': item.product_name,
                'quantity': item.quantity,
            })

        if order.shipping_fee > 0:
            line_items.append({
                'currency': settings.PAYMONGO_CURRENCY,
                'amount': payment_amount(order.shipping_fee),
                'name': 'Delivery fee',
                'quantity': 1,
            })

        payload = {
            'data': {
                'attributes': {
                    'billing': {
                        'name': order.full_name,
                        'email': order.email,
                        'phone': order.phone,
                    },
                    'description': f'Gagah Home Made-Biko Order #{order.id}',
                    'line_items': line_items,
                    'payment_method_types': ['gcash'],
                    'reference_number': str(order.id),
                    'send_email_receipt': True,
                    'show_description': True,
                    'show_line_items': True,
                    'success_url': success_url,
                    'cancel_url': cancel_url,
                    'metadata': {
                        'order_id': str(order.id),
                    },
                }
            }
        }

        try:
            session = paymongo_request('/v1/checkout_sessions', 'POST', payload)
        except HTTPError as error:
            body = error.read().decode('utf-8')
            try:
                payload = json.loads(body)
                errors = payload.get('errors', [])
                message = errors[0].get('detail') if errors else body
            except json.JSONDecodeError:
                message = body
            return JsonResponse({'success': False, 'error': message}, status=400)
        except URLError:
            return JsonResponse({'success': False, 'error': 'Could not reach PayMongo. Please try again.'}, status=502)

        session_data = session.get('data', {})
        session_attributes = session_data.get('attributes', {})
        checkout_url = session_attributes.get('checkout_url') or session_attributes.get('url')
        order.paymongo_checkout_session_id = session_data.get('id', '')
        order.save(update_fields=['paymongo_checkout_session_id'])

        return JsonResponse({
            'success': True,
            'checkout_url': checkout_url,
            'order_id': order.id,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@ensure_csrf_cookie
def order_success(request):
    order_id = request.GET.get('id', '')
    order = None

    if order_id and request.GET.get('paymongo') == '1' and settings.PAYMONGO_SECRET_KEY:
        try:
            order = Order.objects.get(id=order_id)
            if order.paymongo_checkout_session_id:
                session = get_paymongo_checkout_session(order.paymongo_checkout_session_id)
                payment_status = paymongo_status_from_session(session)
                order.paymongo_payment_intent_id = paymongo_payment_intent_id(session)
                if payment_status not in ('paid', 'succeeded', 'success', 'completed', 'complete') and order.paymongo_payment_intent_id:
                    payment_intent = get_paymongo_payment_intent(order.paymongo_payment_intent_id)
                    payment_status = paymongo_status_from_payment_intent(payment_intent) or payment_status
                if payment_status in ('paid', 'succeeded', 'success', 'completed', 'complete'):
                    order.payment_status = 'paid'
                    order.status = 'confirmed'
                    try:
                        send_order_confirmation(order)
                    except Exception as email_error:
                        print("EMAIL ERROR:", str(email_error))
                order.save(update_fields=[
                    'paymongo_payment_intent_id',
                    'payment_status',
                    'status',
                ])
        except Exception as paymongo_error:
            print("PAYMONGO SUCCESS SYNC ERROR:", str(paymongo_error))
    elif order_id:
        order = Order.objects.filter(id=order_id).first()

    return render(request, 'order_success.html', {
        'order_id': order_id,
        'order': order,
    })

@login_required(login_url='/login/')
@ensure_csrf_cookie
def order_history(request):
    orders = Order.objects.filter(
        Q(user=request.user) | Q(email__iexact=request.user.email)
    ).select_related('review').prefetch_related('items').order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})


@login_required(login_url='/login/')
@require_POST
def submit_order_review(request, order_id):
    order = get_object_or_404(
        Order,
        Q(user=request.user) | Q(email__iexact=request.user.email),
        id=order_id,
    )

    if order.status != 'delivered':
        return redirect('order_history')

    if hasattr(order, 'review'):
        return redirect('order_history')

    try:
        rating = int(request.POST.get('rating', '0'))
    except ValueError:
        rating = 0

    comment = request.POST.get('comment', '').strip()

    if 1 <= rating <= 5 and comment:
        OrderReview.objects.create(
            order=order,
            user=request.user,
            rating=rating,
            comment=comment[:1000],
        )

    return redirect('order_history')

@require_POST
def register_user(request):
    try:
        data       = json.loads(request.body)
        full_name  = data.get('full_name', '').strip()
        email      = data.get('email', '').strip().lower()
        password   = data.get('password', '')
        confirm    = data.get('confirm_password', '')
        marketing_opt_in = bool(data.get('marketing_opt_in', False))

        if not all([full_name, email, password, confirm]):
            return JsonResponse({'success': False, 'error': 'All fields are required.'})

        if password != confirm:
            return JsonResponse({'success': False, 'error': 'Passwords do not match.'})

        # Check if email was verified
        verified = EmailOTP.objects.filter(email=email, is_verified=True).exists()
        if not verified:
            return JsonResponse({'success': False, 'error': 'Please verify your email address first.'})

        if User.objects.filter(email__iexact=email).exists():
            return JsonResponse({'success': False, 'error': 'Email already registered.'})

        first_name, last_name = split_full_name(full_name)

        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            CustomerProfile.objects.update_or_create(
                user=user,
                defaults={
                    'full_name': full_name,
                    'marketing_opt_in': marketing_opt_in,
                },
            )

            # Clean up verified OTP only after both records are saved.
            EmailOTP.objects.filter(email=email).delete()

        return JsonResponse({'success': True, 'message': 'Account created successfully!'})

    except Exception as e:
        print("REGISTER ERROR:", str(e))
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
def login_user(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body)
        email    = data.get('email', '').strip().lower()
        password = data.get('password', '')
        keep_logged_in = bool(data.get('keep_logged_in', False))

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            request.session.set_expiry(60 * 60 * 24 * 14 if keep_logged_in else 0)
            return JsonResponse({
                'success': True,
                'message': 'Login successful!',
                'full_name': customer_display_name(user),
                'email': user.email,
            })
        else:
            return JsonResponse({'success': False, 'error': 'Invalid email or password.'})

    except Exception as e:
        print("LOGIN ERROR:", str(e))
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
def logout_user(request):
    logout(request)
    return JsonResponse({'success': True})


# ── Password Reset ────────────────────────────────────────────────────────────

@ensure_csrf_cookie
def forgot_password(request):
    return render(request, 'forgot_password.html')

@ensure_csrf_cookie
def forgot_password_done(request):
    return render(request, 'forgot_password_done.html')

@ensure_csrf_cookie
def reset_password(request, uidb64, token):
    return render(request, 'reset_password.html', {
        'uidb64': uidb64,
        'token': token,
    })

@require_POST
def send_reset_email(request):
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'Method not allowed'},
            status=405)
    try:
        data  = json.loads(request.body)
        email = data.get('email', '').strip()

        if not email:
            return JsonResponse(
                {'success': False, 'error': 'Email is required.'})

        # Always return success — never reveal if email exists (security)
        try:
            user = User.objects.get(email=email)

            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            reset_link = request.build_absolute_uri(
                f"/reset-password/{uid}/{token}/"
            )

            subject = "Reset Your Gagah Home Made-Biko Password"
            send_templated_email(
                subject,
                'password_reset',
                {
                    'name': user.first_name or user.username,
                    'reset_link': reset_link,
                },
                email,
            )

        except User.DoesNotExist:
            pass  # Do not reveal whether the email is registered

        return JsonResponse({
            'success': True,
            'message': 'If that email is registered, a reset link has been sent.'
        })

    except Exception as e:
        print("RESET EMAIL ERROR:", str(e))
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=500)


@require_POST
def reset_password_confirm(request):
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 'error': 'Method not allowed'},
            status=405)
    try:
        data     = json.loads(request.body)
        uidb64   = data.get('uidb64', '')
        token    = data.get('token', '')
        password = data.get('password', '')
        confirm  = data.get('confirm_password', '')

        if not password or not confirm:
            return JsonResponse(
                {'success': False, 'error': 'Both password fields are required.'})

        if password != confirm:
            return JsonResponse(
                {'success': False, 'error': 'Passwords do not match.'})

        if len(password) < 8:
            return JsonResponse(
                {'success': False, 'error': 'Password must be at least 8 characters.'})

        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)

        if not default_token_generator.check_token(user, token):
            return JsonResponse(
                {'success': False,
                 'error': 'Reset link is invalid or has expired. Please request a new one.'})

        user.set_password(password)
        user.save()

        return JsonResponse({
            'success': True,
            'message': 'Password reset successfully! You can now log in.'
        })

    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User not found.'})
    except Exception as e:
        print("RESET CONFIRM ERROR:", str(e))
        return JsonResponse(
            {'success': False, 'error': str(e)},
            status=500)

@login_required(login_url='/login/')
@ensure_csrf_cookie
def profile_page(request):
    return render(request, 'profile.html',
                  {'user': request.user,
                   'full_name': customer_display_name(request.user)})

@login_required(login_url='/login/')
@require_POST
def update_profile(request):
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 
             'error': 'Method not allowed'}, status=405)
    try:
        data       = json.loads(request.body)
        user       = request.user
        full_name  = data.get('full_name', '').strip()
        email      = data.get('email', '').strip().lower()

        if not full_name or not email:
            return JsonResponse(
                {'success': False, 
                 'error': 'Name and email are required.'})

        # Check email not taken by another user
        if User.objects.filter(email__iexact=email).exclude(
            pk=user.pk).exists():
            return JsonResponse(
                {'success': False, 
                 'error': 'Email already in use.'})

        first_name, last_name = split_full_name(full_name)
        user.first_name = first_name
        user.last_name  = last_name
        user.email      = email
        user.username   = email
        user.save(update_fields=['first_name', 'last_name', 'email', 'username'])
        CustomerProfile.objects.update_or_create(
            user=user,
            defaults={'full_name': full_name},
        )

        return JsonResponse(
            {'success': True, 
             'name': full_name,
             'message': 'Profile updated successfully!'})

    except Exception as e:
        return JsonResponse(
            {'success': False, 'error': str(e)}, 
            status=500)

@login_required(login_url='/login/')
@require_POST
def change_password(request):
    if request.method != 'POST':
        return JsonResponse(
            {'success': False, 
             'error': 'Method not allowed'}, status=405)
    try:
        data         = json.loads(request.body)
        user         = request.user
        current      = data.get('current_password', '')
        new_pass     = data.get('new_password', '')
        confirm      = data.get('confirm_password', '')

        if not user.check_password(current):
            return JsonResponse(
                {'success': False, 
                 'error': 'Current password is incorrect.'})

        if new_pass != confirm:
            return JsonResponse(
                {'success': False, 
                 'error': 'New passwords do not match.'})

        if len(new_pass) < 8:
            return JsonResponse(
                {'success': False, 
                 'error': 'Password must be at least '
                          '8 characters.'})

        user.set_password(new_pass)
        user.save()

        # Keep user logged in after password change
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, user)

        return JsonResponse(
            {'success': True, 
             'message': 'Password changed successfully!'})

    except Exception as e:
        return JsonResponse(
            {'success': False, 'error': str(e)}, 
            status=500)

@ensure_csrf_cookie
@staff_member_required
def admin_dashboard(request):
    # Summary stats
    total_orders   = Order.objects.count()
    total_revenue  = Order.objects.filter(
                         status='delivered'
                     ).aggregate(
                         total=Sum('total')
                     )['total'] or 0
    pending_orders = Order.objects.filter(
                         status='pending'
                     ).count()
    recent_orders  = Order.objects.order_by('-created_at')[:10]

    # Best selling products
    best_sellers = OrderItem.objects.values(
        'product_name'
    ).annotate(
        total_qty=Sum('quantity'),
        total_sales=Sum('price')
    ).order_by('-total_qty')[:5]

    # Orders by status
    status_counts = Order.objects.values(
        'status'
    ).annotate(count=Count('id'))

    context = {
        'total_orders'  : total_orders,
        'total_revenue' : total_revenue,
        'pending_orders': pending_orders,
        'recent_orders' : recent_orders,
        'best_sellers'  : best_sellers,
        'status_counts' : status_counts,
    }

    return render(request, 'dashboard.html', context)

# ── Info Pages ────────────────────────────────────────────────
@ensure_csrf_cookie
def privacy_policy(request):
    return render(request, 'privacy_policy.html')

@ensure_csrf_cookie
def terms_of_service(request):
    return render(request, 'terms_of_service.html')

@ensure_csrf_cookie
def shipping_info(request):
    return render(request, 'shipping_info.html')

@ensure_csrf_cookie
def sustainability(request):
    return render(request, 'sustainability.html')

@ensure_csrf_cookie
def faq_page(request):
    return render(request, 'faq.html')

@ensure_csrf_cookie
def page_not_found(request, exception):
    return render(request, '404.html', status=404)
