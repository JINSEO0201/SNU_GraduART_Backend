from django.urls import path
from . import views

urlpatterns = [
    path('insert/', views.insert_cart, name='insert_cart'),
    path('items/', views.get_cart_items, name='get_cart_items'),
    path('delete/<str:item_id>/', views.delete_cart_item, name='delete_cart_item'),
]

