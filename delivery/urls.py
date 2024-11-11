from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_delivery_status, name='get_delivery_status'),
]

