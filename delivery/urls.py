from django.urls import path
from . import views

urlpatterns = [
    path('<uuid:item_id>/', views.get_delivery_status, name='get_delivery_status'),
]

