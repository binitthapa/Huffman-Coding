from django.urls import path
from hc_app import views

urlpatterns = [
    path('',          views.index,    name='index'),
    path('compress/', views.compress, name='compress'),
]