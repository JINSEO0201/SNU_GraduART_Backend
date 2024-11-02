from django.urls import path
from . import views

urlpatterns = [
  path('<str: department>/', views.get_items, name='get_items'),
  path('<int:item_id>/', views.get_item_details, name='get_item_details'),
  path('search/', views.search_items, name='search_items'),
  # path('representative/', views.get_representative_items, name='get_representative_items'),
]
