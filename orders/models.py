from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        related_name='customer_profile',
        on_delete=models.CASCADE,
    )
    full_name = models.CharField(max_length=255)
    marketing_opt_in = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def sync_user_name(self):
        name_parts = self.full_name.strip().split(' ', 1)
        self.user.first_name = name_parts[0] if name_parts else ''
        self.user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        self.user.save(update_fields=['first_name', 'last_name'])

    def __str__(self):
        return self.full_name or self.user.email

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='orders',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    address = models.CharField(max_length=255)
    apartment = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    
    shipping_method = models.CharField(max_length=50)
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(max_length=50, default='unpaid')
    gcash_reference = models.CharField(max_length=100, blank=True)
    paymongo_checkout_session_id = models.CharField(max_length=255, blank=True)
    paymongo_payment_intent_id = models.CharField(max_length=255, blank=True)
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Order #{self.id} - {self.full_name}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity}x {self.product_name} (Order #{self.order.id})"


class OrderReview(models.Model):
    order = models.OneToOneField(Order, related_name='review', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='order_reviews', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.rating}/5 review for Order #{self.order_id}"

from django.utils import timezone
from datetime import timedelta

class EmailOTP(models.Model):
    email        = models.EmailField()
    otp_code     = models.CharField(max_length=6)
    created_at   = models.DateTimeField(auto_now_add=True)
    is_verified  = models.BooleanField(default=False)
    attempts     = models.IntegerField(default=0)

    def is_expired(self):
        # OTP expires after 10 minutes
        expiry = self.created_at + timedelta(minutes=10)
        return timezone.now() > expiry

    def __str__(self):
        return f"{self.email} - {self.otp_code}"

    class Meta:
        ordering = ['-created_at']
