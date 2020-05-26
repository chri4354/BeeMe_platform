from django.urls import path, re_path

from . import views


app_name = 'controlroom'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),

    path('update_queue_table/', views.update_queue_table, name='update_queue_table'),
]
