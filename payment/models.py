from django.db import models
from django.contrib.auth.models import User
from pandas import notnull
# Create your models here.


class Order(models.Model):
    # Shouldn't delete payment details even if user is deleted
    user = models.ForeignKey(
        User, related_name="user_orders", on_delete=models.SET_NULL, null=True)
    order_id = models.TextField(default=None, unique=True)
    # Null if payment was not attempted
    payment_id = models.TextField(default=None, null=True)

    def __str__(self):
        return self.order_id
