from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('countdown/', views.countdown, name='countdown'),
    #re_path(r'.+', views.redir, name='redir'),
]
