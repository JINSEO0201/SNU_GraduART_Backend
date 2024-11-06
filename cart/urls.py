from django.urls import path
from . import views

urlpatterns = [
    path('insert/<uuid:item_id>/', views.insert_cart, name='insert_cart'),
    path('items/', views.get_cart_items, name='get_cart_items'),
    path('delete/<uuid:item_id>/', views.delete_cart_item, name='delete_cart_item'),
]

