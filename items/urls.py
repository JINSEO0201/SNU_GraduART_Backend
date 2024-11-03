from django.urls import path
from . import views

urlpatterns = [
  path('', views.get_items, name='get_items'),
  path('<uuid:item_id>/', views.get_item_details, name='get_item_details'),
  path('search/', views.search_items, name='search_items'),
]
