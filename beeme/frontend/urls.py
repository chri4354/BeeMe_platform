# django imports
from django.urls import path
# local imports
from . import views


app_name = 'frontend'

urlpatterns = [
    path('about', views.AboutView.as_view(), name='about'),
    path('command-history', views.CommandHistoryView.as_view(), name='command_history'),
    path('credits', views.CreditsView.as_view(), name='credits'),
    path('diy', views.DIYView.as_view(), name='diy'),
    path('gallery', views.GalleryView.as_view(), name='gallery'),
    path('gallery/<uuid:item_id>', views.GalleryItemView.as_view(), name='gallery_item'),
    path('history', views.HistoryView.as_view(), name='history'),
    path('intro', views.IntroView.as_view(), name='intro'),
    path('manage', views.ManageView.as_view(), name='manage'),
    path('manage/gallery', views.ManageGalleryView.as_view(), name='manage_gallery'), # order matters
    path('manage/<slug:section>', views.ManageView.as_view(), name='manage_section'),
    path('privacy-policy', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('pusher/auth', views.PusherAuthView.as_view(), name='privacy_policy'),
    path('read-more', views.ReadMoreView.as_view(), name='read-more'),
    path('room', views.RoomView.as_view(), name='room'),
    path('rules', views.RulesView.as_view(), name='rules'),
    path('signup', views.SignupView.as_view(), name='signup'),
    path('story', views.StoryView.as_view(), name='story'),
    path('tos', views.TermsOfServiceView.as_view(), name='tos'),
    path('empty', views.empty, name='empty'),
]
