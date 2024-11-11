from django.urls import path
from . import views

urlpatterns = [
    path('prepare/', views.prepare_purchase, name='prepare_purchase'),
    path('approve/', views.approve_purchase, name='approve_purchase'),
    path('', views.get_purchases, name='get_purchases'),
    path('<uuid:item_id>/', views.get_purchase, name='get_purchase_detail'),
]

