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
    #   Consider a status field in the Orders Model -> Updated in this function
    if request.method == "POST":
        try:
            payment_id = request.POST.get('razorpay_payment_id')
            order_id = request.POST.get('razorpay_order_id')
            signature = request.POST.get('razorpay_signature')
            result = razorpay_client.utility.verify_payment_signature(
                {'razorpay_payment_id': payment_id,
                 'razorpay_order_id': order_id,
                 'razorpay_signature': signature})
            if result:
                # if payment is verified
                try:
                    order = Order.objects.filter(order_id=order_id).first()
                    order.payment_id = payment_id
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
            created_order.save()
            return render(request, 'payment/failed_payment.html')
    else:
        return HttpResponseBadRequest


@login_required(login_url='/accounts/login')
# If we add a status to Order -> Faster render on endpoint hit (no need to re-query)
def donations(request):
    past_transactions = []
    for order in request.user.user_orders.all():
        transaction = dict()
        # Payment is attemtped -> else empty order
        if order.payment_id != None:
            payment_details = razorpay_client.payment.fetch(order.payment_id)
            transaction["id"] = payment_details["id"]
            transaction["amount"] = payment_details["amount"]
            transaction["method"] = payment_details["method"]
            transaction["date"] = datetime.fromtimestamp(
                int(payment_details["created_at"]))
            if payment_details["captured"]:
                transaction["status"] = "Success"
                transaction["display_color"] = "success"
            else:
                if payment_details["error_reason"] and payment_details["error_reason"].find("cancelled") >= 0:
                    transaction["status"] = "Cancelled"
                    transaction["display_color"] = "failure"
                elif payment_details["error_reason"] and payment_details["error_reason"].find("failed") >= 0:
                    transaction["status"] = "Declined"
                    transaction["display_color"] = "failure"
                else:
                    transaction["status"] = "Failed"
                    transaction["display_color"] = "failure"
        else:
            # Making unpaid orders = Pending (not exactly true)
            #     original_order = razorpay_client.order.fetch(order.order_id)
            #     transaction["id"] = original_order["id"]
            #     transaction["amount"] = original_order["amount"]
            #     transaction["status"] = "Pending"
            #     transaction["method"] = "NA"
            #     transaction["date"] = datetime.fromtimestamp(
            #         int(original_order["created_at"]))
            #     transaction["display_color"] = "pending"
            # past_transactions.append(transaction)
            pass
        if(transaction):
            past_transactions.append(transaction)
    return render(request, 'payment/past_donations.html', context={"transactions": past_transactions})
