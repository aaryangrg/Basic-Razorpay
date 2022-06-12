from django.db import models
from django.contrib.auth.models import User
from pandas import notnull
# Create your models here.


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Success', 'Success'),
        ('Cancelled', 'Cancelled'),
        ('Declined', 'Declined'),
        ("Failed", "Failed")
    ]
    # Shouldn't delete payment details even if user is deleted
    user = models.ForeignKey(
        User, related_name="user_orders", on_delete=models.SET_NULL, null=True)
    order_id = models.TextField(default=None, unique=True)
    # Null if payment was not attempted
    payment_id = models.TextField(default=None, null=True)
    # Prevents need to re-query database to show past orderss
    payment_status = models.TextField(
        choices=STATUS_CHOICES, null=False, default="Pending")
    # date/time at which the order was paid
    paid_at = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.order_id
