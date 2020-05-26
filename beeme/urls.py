# django imports
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
# project imports
from beeme.frontend.views import LoginView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('controlroom/', include('controlroom.urls')),

    #path('login', auth_views.LoginView.as_view(), name='login'),
    path('login', LoginView.as_view(), name='login'),
    path('logout', auth_views.LogoutView.as_view(), name='logout'),
    path('password-change', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('password-change/done', auth_views.PasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password-reset', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('', include('countdownhype.urls')),
    path('', include('beeme.frontend.urls')),
    path('accounts/', include('allauth.urls')),
]
