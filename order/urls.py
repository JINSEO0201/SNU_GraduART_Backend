from django.urls import path
from . import views

urlpatterns = [
    path('detail/', views.get_order_info, name='get_order_info'),
]

