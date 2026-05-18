from django.contrib import admin
from .models import CustomerProfile, Order, OrderItem, OrderReview


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'marketing_opt_in', 'created_at']
    search_fields = ['full_name', 'user__email', 'user__username']
    list_filter = ['marketing_opt_in', 'created_at']
    ordering = ['-created_at']

    @admin.display(ordering='user__email')
    def email(self, obj):
        return obj.user.email

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'email', 'account_email', 'city', 'total', 'payment_method', 'payment_status', 'status', 'created_at']
    list_filter = ['status', 'payment_status', 'shipping_method', 'payment_method', 'created_at']
    search_fields = ['full_name', 'email', 'phone', 'user__email', 'gcash_reference', 'paymongo_checkout_session_id', 'paymongo_payment_intent_id']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'subtotal', 'shipping_fee', 'total', 'paymongo_checkout_session_id', 'paymongo_payment_intent_id']
    inlines = [OrderItemInline]

    @admin.display(ordering='user__email')
    def account_email(self, obj):
        return obj.user.email if obj.user else '-'


@admin.register(OrderReview)
class OrderReviewAdmin(admin.ModelAdmin):
    list_display = ['order', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['order__id', 'user__email', 'comment']
    readonly_fields = ['order', 'user', 'rating', 'comment', 'created_at']

from .models import EmailOTP

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = [
        'email', 
        'otp_code', 
        'is_verified', 
        'created_at'
    ]
    list_filter  = ['is_verified']
