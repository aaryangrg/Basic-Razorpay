from django.contrib import admin
from django.urls import path
from . import views
from django.http import HttpResponse
urlpatterns = [
    path('landing/', views.landing_page, name="landing_page"),
    path('donate/', views.home, name='home'),
    path('handlepayment/', views.handle_payment, name='paymenthandler'),
    path('past-donations/', views.donations, name='past-donations'),
]
