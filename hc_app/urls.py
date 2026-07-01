from django.urls import path
from hc_app import views

urlpatterns = [
    path('',
         views.index,
         name='index'),

    path('compress/',
         views.compress,
         name='compress'),

    path('download/<str:file_type>/<str:filename>/',
         views.download_file,
         name='download_file'),
]