"""
URL configuration for config project.
"""
from django.contrib import admin
from django.conf import settings
from django.urls import path, re_path
from django.views import defaults
from django.views.static import serve
from orders import views

urlpatterns = [
    path('admin/',         admin.site.urls),
    path('',               views.home,          name='home'),
    path('menu/',          views.menu,          name='menu'),
    path('about/',         views.about,         name='about'),
    path('contact/',       views.contact,       name='contact'),
    path('signup/',        views.signup_page,   name='signup'),
    path('login/',         views.login_page,    name='login'),
    path('cart/',          views.cart_page,     name='cart'),
    path('checkout/',      views.checkout_page, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),
    path('my-orders/',     views.order_history, name='order_history'),
    path('my-orders/<int:order_id>/review/', views.submit_order_review, name='submit_order_review'),
    path('profile/',       views.profile_page,  name='profile'),
    path('dashboard/',     views.admin_dashboard, name='admin_dashboard'),

    # Info pages
    path('privacy-policy/',   views.privacy_policy,   name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('shipping-info/',    views.shipping_info,     name='shipping_info'),
    path('sustainability/',   views.sustainability,    name='sustainability'),
    path('faq/',              views.faq_page,          name='faq'),

    # API endpoints
    path('register/',      views.register_user,  name='register'),
    path('login-user/',    views.login_user,     name='login_user'),
    path('logout-user/',   views.logout_user,    name='logout_user'),
    path('place-order/',   views.place_order,    name='place_order'),
    path('create-paymongo-checkout-session/', views.create_paymongo_checkout_session, name='create_paymongo_checkout_session'),
    path('send-email-otp/',   views.send_email_otp,   name='send_email_otp'),
    path('verify-email-otp/', views.verify_email_otp, name='verify_email_otp'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('change-password/', views.change_password, name='change_password'),

    # Password reset
    path('forgot-password/',                  views.forgot_password,        name='forgot_password'),
    path('forgot-password/done/',             views.forgot_password_done,   name='forgot_password_done'),
    path('reset-password/<uidb64>/<token>/',  views.reset_password,         name='reset_password'),
    path('reset-password-confirm/',           views.reset_password_confirm, name='reset_password_confirm'),
    path('send-reset-email/',                 views.send_reset_email,       name='send_reset_email'),

    # Test 404 while DEBUG=True
    path('404/', lambda req: defaults.page_not_found(req, Exception()), name='test_404'),
]

handler404 = 'orders.views.page_not_found'

if settings.IS_VERCEL:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.BASE_DIR / 'static'}),
    ]
