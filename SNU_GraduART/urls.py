"""
URL configuration for SNU_GraduART project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/', include('authorize.urls')),
    path('api/v1/cart/', include('cart.urls')),
    path('api/v1/purchases/', include('purchases.urls')),
    path('api/v1/refunds/', include('refunds.urls')),
    path('api/v1/items/', include('items.urls')),
    path('api/v1/delivery/', include('delivery.urls')),
    path('api/v1/order/', include('order.urls')),
]
