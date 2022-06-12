from cmath import log
from http import client
from locale import currency
from bidict import OrderedBidictBase
from django.shortcuts import render
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest, JsonResponse, HttpResponse
from .models import Order
from django.contrib.auth.models import User
import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now

# Create RazorPay Client with our keys
razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))
razorpay_client.set_app_details({'title': "Fund Me", "version": '1'})
DONATION_AMOUNT = settings.DONATION_AMOUNT


@login_required(login_url="/accounts/login")
def landing_page(request):
    return render(request, 'payment/landing_page.html')


@login_required(login_url='/accounts/login')
def home(request):
    try:
        currency = "INR"
        new_order = razorpay_client.order.create(
            {'amount': DONATION_AMOUNT, 'currency': currency, 'payment': {'capture': 'automatic', 'capture_options': {'refund_speed': 'optimum'}}})
        order = Order(user=request.user, order_id=new_order["id"])
        order.save()
        return render(request, 'payment/home.html', context={'order': new_order, "merchant_key": settings.RAZOR_KEY_ID, 'callback': "http://localhost:8000/payment/handlepayment/"})
    except:
        return render(request, 'payment/failed_payment.html')

# Call back post payment capture attempt (Razorpay)


@ csrf_exempt
def handle_payment(request):
    if request.method == "POST":
        try:
            payment_id = request.POST.get('razorpay_payment_id')
            order_id = request.POST.get('razorpay_order_id')
            signature = request.POST.get('razorpay_signature')
            # Don't need to capture payment (config is on auto)
            result = razorpay_client.utility.verify_payment_signature(
                {'razorpay_payment_id': payment_id,
                 'razorpay_order_id': order_id,
                 'razorpay_signature': signature})
            if result:
                # if payment is verified
                try:
                    order = Order.objects.filter(order_id=order_id).first()
                    payment_details = razorpay_client.payment.fetch(payment_id)
                    if payment_details["captured"]:
                        order.payment_status = "Success"
                    order.payment_id = payment_id
                    # Our copy of having received the payment --> not razorpay time
                    order.paid_at = datetime.now()
                    order.save()
                    return render(request, 'payment/payment_succeeded.html')
                except:
                    # payment succeeded but we couldn't write it to the database
                    return render(request, 'payment/payment_succeeded.html')
            else:
                # Unauthorized/ verified payment -> don't save it + did not go through
                return render(request, 'payment/failed_payment.html')
        except:
            # failed payments :
            failure_details = dict(request.POST)
            id_dict = json.loads(failure_details["error[metadata]"][0])
            order_id, payment_id = id_dict["order_id"], id_dict["payment_id"]
            created_order = Order.objects.filter(order_id=order_id).first()
            created_order.payment_id = payment_id
            # Update Order payment_status
            if("error[reason]" in failure_details.keys()):
                payment_error_reason = failure_details["error[reason]"][0]
                if payment_error_reason.find("cancelled") >= 0:
                    created_order.payment_status = "Cancelled"
                elif payment_error_reason.find("failed") >= 0:
                    created_order.payment_status = "Declined"
                else:
                    created_order.payment_status = "Failed"
            else:
                created_order.payment_status = "Failed"
            created_order.paid_at = datetime.now()
            created_order.save()
            return render(request, 'payment/failed_payment.html', {"reason": payment_error_reason})
    else:
        return HttpResponseBadRequest


@login_required(login_url='/accounts/login')
def donations(request):
    past_transactions = []
    # Using related names to get orders of a user
    for order in request.user.user_orders.all():
        # Payment is attemtped -> else empty order
        # Payment details in Order model prevent re-query
        if order.payment_id != None:
            transaction = dict()
            transaction["id"] = order.payment_id
            transaction["amount"] = DONATION_AMOUNT
            transaction["date"] = order.paid_at
            transaction["status"] = order.payment_status
            # Dynamic styling
            if order.payment_status == "Success":
                transaction["display_color"] = "success"
            elif order.payment_status == "Pending":
                transaction["display_color"] = "pending"
            else:
                transaction["display_color"] = "failure"
            past_transactions.append(transaction)
    return render(request, 'payment/past_donations.html', context={"transactions": past_transactions})
