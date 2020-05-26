# stdlib imports
from functools import wraps
import datetime
import logging ; logger = logging.getLogger(__name__)
import os
import tempfile
import uuid
# django imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as AuthLoginView
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.db import models
from django.db import transaction
from django.db.models import Count
from django.db.models import F
from django.db.models import OuterRef
from django.db.models import Subquery
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.template import loader
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.decorators.cache import cache_control
# third-party imports
from PIL import Image
from constance import config
from libcloud.storage.providers import get_driver
from libcloud.storage.types import Provider, ContainerDoesNotExistError
import pusher
import requests
# project imports
from beeme.core.models import BannedEmailDomain
from beeme.core.models import Command
from beeme.core.models import Gallery
from beeme.core.models import GalleryItem
from beeme.core.models import Message
from beeme.core.models import Task
from beeme.core.models import VoteDown
from beeme.core.models import VoteUp
from beeme.core.models import user_random_team
# local imports
from .forms import AuthenticationForm
from .forms import SignUpForm


RATELIMIT_COUNT = 1 # occurrences per period
RATELIMIT_PERIOD = 1 # seconds


# pusher service client

pusher_client = pusher.Pusher(
    app_id=settings.PUSHER_APP_ID,
    key=settings.PUSHER_KEY,
    secret=settings.PUSHER_SECRET,
    cluster=settings.PUSHER_CLUSTER,
    ssl=settings.PUSHER_SSL
)


# helper methods

def command_to_dict(command):
    timezone.now()

    c = {
        'id': str(command.id),
        'by': str(command.created_by),
        'text': command.text,
        'timestamp': command.timestamp.isoformat(),

        'votes': {
            'up': command.upvotes_count,
            'down': command.downvotes_count,
            'value': command.votes_count,
        }
    }

    return c

def ratelimit_exceeded(key):
    # choose now
    now = datetime.datetime.utcnow()
    # expired date
    expired = now - datetime.timedelta(seconds=RATELIMIT_PERIOD)
    # get current values
    values = cache.get(key, [])
    # filter expired values
    values = list( filter(lambda d: d >= expired, values) )
    # count values
    count = len(values)
    # check if things were exceeded
    return count >= RATELIMIT_COUNT

def ratelimit_increment(key):
    # choose now
    now = datetime.datetime.utcnow()
    # expired date
    expired = now - datetime.timedelta(seconds=RATELIMIT_PERIOD)
    # get current values
    values = cache.get(key, [])
    # filter expired values
    values = list( filter(lambda d: d >= expired, values) )
    # increment
    values.append(now)
    # set cache
    cache.set(key, values, RATELIMIT_PERIOD)
    return len(values)


class PrivateView(View):

    @method_decorator( cache_control(private=True) )
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    pass

class PublicView(View):

    @method_decorator( cache_control(max_age=3600, public=True) )
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    pass


# class views

class AboutView(PublicView):

    def get(self, request):
        return render(request, 'frontend/about.html', {
            'title': 'About BeeMe',
        })

    pass

class CommandHistoryView(LoginRequiredMixin, PrivateView):

    def get(self, request):
        command_timediff = config.COMMAND_EXPIRATION * 4
        command_timediff = datetime.timedelta(minutes=command_timediff)

        # get current time
        now = timezone.now()
        # calculate cutoff time
        command_cutoff = now - command_timediff

        commands = Command.objects \
            .filter(teamno=request.user.teamno, is_performed=True) \
            .order_by('-timestamp') \
            .select_related('created_by')[:100]

        return render(request, 'frontend/command-history.html', {
            'title': 'BeeMe Hive History',

            'commands': commands,
        })

    pass

class CreditsView(PublicView):

    def get(self, request):
        return render(request, 'frontend/credits.html', {
            'title': 'BeeMe Credits',
        })

    pass

class DIYView(PrivateView):

    def get(self, request):
        return render(request, 'frontend/diy.html', {
            'title': 'DIY Instructions',
            
            'html': config.DIY_INSTRUCTIONS,
        })

    pass

class GalleryItemView(PublicView):

    def get(self, request, item_id):
        item = get_object_or_404(GalleryItem, id=item_id)

        return render(request, 'frontend/gallery_item.html', {
            'title': '{} - BeeMe Gallery'.format(item.title),

            'item': item,
        })

    pass

class GalleryView(PublicView):

    def get(self, request):
        gallery = get_object_or_404(Gallery, title='Default')

        items = GalleryItem.objects \
            .filter(gallery=gallery) \
            .order_by('ord','title')

        return render(request, 'frontend/gallery.html', {
            'title': 'BeeMe Gallery',

            'items': items,
        })

    pass

class HistoryView(LoginRequiredMixin, PrivateView):

    def get(self, request):
        messages = Message.objects \
            .filter(teamno=request.user.teamno) \
            .order_by('-created_at') \
            .select_related('created_by')

        return render(request, 'frontend/history.html', {
            'title': 'BeeMe Hive History',

            'messages': messages,
        })

    pass

class IntroView(PrivateView):

    def get(self, request):
        return render(request, 'frontend/intro.html', {
            'title': 'BeeMe Story',
        })

    pass

class LoginView(AuthLoginView):
    
    authentication_form = AuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        form_signup = SignUpForm(auto_id='signup_%s')

        context.update({
            'form_signup': form_signup,
        })

        return context

    def get_success_url(self):
        url = self.get_redirect_url()

        if not url:
            if self.request.user.is_staff:
                url = reverse( 'frontend:manage' )
            else:
                url = reverse( 'frontend:room' )
            pass

        return url or resolve_url(settings.LOGIN_REDIRECT_URL)

    pass

class ManageView(LoginRequiredMixin, PrivateView):

    team_count = 2

    def get(self, request, section=None):
        if not request.user.is_staff: return HttpResponseForbidden()

        recent = request.POST.get('recent','0') == '1'

        UserModel = get_user_model()

        section_html = None

        if section:
            section_html = 'frontend/manage-{}.html'.format(section)
            pass

        users = UserModel.objects \
            .filter(is_active=True) \
            .order_by('email')


        if recent:
            earliest = timezone.now() - datetime.timedelta(seconds=settings.SESSION_COOKIE_AGE)
            users = users.filter(last_login__gte=earliest)
            pass

        users_voteups = VoteUp.objects \
            .order_by() \
            .filter(user_id__in=users.values_list('id', flat=True)) \
            .values_list('user_id') \
            .annotate(num=Count('id')) \
            .values_list('user_id','num')
        users_votedowns = VoteDown.objects \
            .order_by() \
            .filter(user_id__in=users.values_list('id', flat=True)) \
            .values_list('user_id') \
            .annotate(num=Count('id')) \
            .values_list('user_id','num')

        users_voteups = dict(users_voteups)
        users_votedowns = dict(users_votedowns)

        users = list(users)

        team_counts = {}
        for u in users:
            team_counts[ u.teamno ] = team_counts.get(u.teamno, 0) + 1

            u.count_voteup = users_voteups.get(u.id, 0)
            u.count_votedown = users_votedowns.get(u.id, 0)
            pass

        team_one = ( team_counts[1] / ( team_counts[1] + team_counts[2] ) ) * 100.0
        team_two = ( team_counts[2] / ( team_counts[1] + team_counts[2] ) ) * 100.0

        return render(request, 'frontend/manage.html', {
            'title': 'Management Area',

            'command_expiration': config.COMMAND_EXPIRATION,
            'command_vote_expiration': config.COMMAND_VOTE_EXPIRATION,

            'config': config,
            'section_html': section_html,

            'minutes': list( i*5 for i in range(1, 24+1) ),

            'recent': recent,
            'users': users,

            'team_one': team_one,
            'team_two': team_two,
        })

    def post(self, request, section=None):
        if section == 'profile':
            teamno = int( request.POST['teamno'] )

            user = request.user
            user.teamno = teamno
            user.save()
            return self.get(request, section)

        if section == 'command-parmeters':
            command_expiration = int( request.POST['command_expiration'] )
            command_vote_expiration = int( request.POST['command_vote_expiration'] )

            config.COMMAND_EXPIRATION = command_expiration
            config.COMMAND_VOTE_EXPIRATION = command_vote_expiration

            return self.get(request, section)

        if section == 'diy-instructions':
            html = request.POST['html'].strip().replace('\t', ' '*4)
            changed = config.DIY_INSTRUCTIONS != html

            if changed:
                config.DIY_INSTRUCTIONS = html
                pass

            return self.get(request, section)

        if section == 'story-intro':
            html = request.POST['html'].strip().replace('\t', ' '*4)
            changed = config.STORY_INTRO != html

            if changed:
                config.STORY_INTRO = html
                pass

            return self.get(request, section)

        if section == 'team1-media':
            html = request.POST['html'].strip().replace('\t', ' '*4)
            reload = request.POST.get('reload', '0') == '1'
            changed = config.TEAM1_MEDIA != html

            if changed:
                config.TEAM1_MEDIA = html
                self.send_reload()
                pass

            return self.get(request, section)

        if section == 'team1-story':
            html = request.POST['html'].strip().replace('\t', ' '*4)
            reload = request.POST.get('reload', '0') == '1'
            changed = config.TEAM1_STORY != html

            if changed:
                config.TEAM1_STORY = html
                self.send_reload()
                pass

            return self.get(request, section)

        if section == 'team2-media':
            html = request.POST['html'].strip().replace('\t', ' '*4)
            reload = request.POST.get('reload', '0') == '1'
            changed = config.TEAM2_MEDIA != html

            if changed:
                config.TEAM2_MEDIA = html
                self.send_reload()
                pass

            return self.get(request, section)

        if section == 'team2-story':
            html = request.POST['html'].strip().replace('\t', ' '*4)
            reload = request.POST.get('reload', '0') == '2'
            changed = config.TEAM2_STORY != html

            if changed:
                config.TEAM2_STORY = html
                self.send_reload()
                pass

            return self.get(request, section)

        if section == 'users':
            UserModel = get_user_model()

            if 'change_team' in request.POST:
                user_id = int( request.POST['change_team'] )
                user = get_object_or_404(UserModel, id=user_id, is_active=True)

                if user.teamno == 1:
                    user.teamno = 2
                else:
                    user.teamno = 1

                user.save()

                self.send_reload(user)
                pass
            elif 'ban' in request.POST:
                user_id = int( request.POST['ban'] )
                user = get_object_or_404(UserModel, id=user_id, is_active=True)

                user.is_banned = True
                user.save()
                pass
            elif 'unban' in request.POST:
                user_id = int( request.POST['unban'] )
                user = get_object_or_404(UserModel, id=user_id, is_active=True)

                user.is_banned = False
                user.save()
                pass
            elif 'delete' in request.POST:
                user_id = int( request.POST['delete'] )
                user = get_object_or_404(UserModel, id=user_id, is_active=True)

                user.is_active = False
                user.save()
                pass

            return self.get(request, section)

        pass

    def send_reload(self, user=None, teamno=None):
        if user:
            channel = 'private-{}'.format(user.code)
            event = 'reload'

            pusher_client.trigger(channel, event, {})
            return

        if teamno:
            channel = 'room-{}'.format(teamno)
            event = 'reload'

            pusher_client.trigger(channel, event, {})
            return

        for i in range(self.team_count):
            channel = 'room-{}'.format(i+1)
            event = 'reload'

            pusher_client.trigger(channel, event, {})
            pass
        return

    pass

class ManageGalleryView(LoginRequiredMixin, PrivateView):

    THUMB_SIZE = (300,300)

    def get(self, request):
        gallery = Gallery.objects.first()

        if gallery is None:
            gallery,_ = Gallery.objects.get_or_create(title='Default')
            pass

        items = GalleryItem.objects \
            .filter(gallery=gallery) \
            .order_by('ord','title')

        return render(request, 'frontend/manage-gallery.html', {
            'title': 'Manage Gallery',

            'gallery': gallery,
            'items': items,
        })

    def post(self, request):
        action = request.POST.get('action')
        title = request.POST.get('title','').strip()
        type = request.POST.get('type')

        gallery = Gallery.objects.get(title='Default')

        ord = GalleryItem.objects.filter(gallery=gallery).count() + 1

        if action == 'delete':
            id_ = request.POST.get('id')

            item = get_object_or_404(GalleryItem, gallery=gallery, id=id_)
            pass
        elif action == 'reorder':
            ordering = {}

            for k in request.POST.keys():
                if not k.startswith('ord_'): continue

                id_ = k.replace('ord_', '')
                o = int( request.POST[k] )

                ordering[id_] = o
                pass

            items = GalleryItem.objects.in_bulk(id_list=list(ordering.keys()))

            for item in items.values():
                item.ord = ordering[ str(item.id) ]
                item.save()
                pass
            pass
        elif type == 'image':
            image = request.FILES['image']

            image_name = image.name
            image_name_base,image_name_ext = os.path.splitext(image_name)
            image_name = image_name_base + image_name_ext.lower()
            thumb_name = image_name_base + '.thumb' + image_name_ext.lower()

            uid = uuid.uuid4()
            image_key = str(uid) + image_name_ext.lower()
            thumb_key = str(uid) + '.thumb' + image_name_ext.lower()

            # save memory file to tmp
            if isinstance(image, InMemoryUploadedFile):
                fd,image_path = tempfile.mkstemp(prefix='gallery-image-', suffix=image_name_ext.lower(), text=False)

                for chunk in image.chunks():
                    os.write(fd, chunk)

                os.close(fd)
                pass
            elif isinstance(image, TemporaryUploadedFile):
                image_path = image.temporary_file_path()
            else:
                raise Exception( 'Unexpected upload file type: %s' % image.__class__.__name__ )

            # create thumbnail
            fd,thumb_path = tempfile.mkstemp(prefix='gallery-thumb-', suffix='.jpg', text=False)
            os.close(fd)
            im = Image.open(image_path)
            im.thumbnail(ManageGalleryView.THUMB_SIZE)
            im.save(thumb_path, 'JPEG')

            # connect to storage
            cloudfiles_driver = get_driver(Provider.CLOUDFILES)
            driver = cloudfiles_driver(
                settings.CLOUDFILES['gallery']['username'],
                settings.CLOUDFILES['gallery']['api_key'],
                region= settings.CLOUDFILES['gallery']['region']
            )
            container = driver.get_container(container_name=settings.CLOUDFILES['gallery']['name'])

            # upload original
            obj_image = driver.upload_object(
                file_path=image_path,
                container=container,
                object_name=image_key
            )

            # upload thumbnail
            obj_thumb = driver.upload_object(
                file_path=thumb_path,
                container=container,
                object_name=thumb_key
            )

            gitem = GalleryItem.objects.create(
                gallery=gallery,
                ord=ord,
                title=title,
                name=image_name,
                type=type,
                image_url=driver.get_object_cdn_url(obj_image)
            )

            pass
        elif type == 'vimeo':
            vimeo_id = request.POST[type].strip()

            r = requests.get('http://vimeo.com/api/v2/video/{}.json'.format(vimeo_id))

            if r.status_code == 200:
                image_url = r.json()[0]['thumbnail_large']

                gitem = GalleryItem.objects.create(
                    gallery=gallery,
                    ord=ord,
                    title=title,
                    type=type,
                    vimeo_id=request.POST[type].strip(),
                    image_url=image_url
                )
                pass
            pass
        elif type == 'youtube':
            gitem = GalleryItem.objects.create(
                gallery=gallery,
                ord=ord,
                title=title,
                type=type,
                youtube_id=request.POST[type].strip()
            )
            pass
        else:
            raise Exception( 'unexpected type: %s' % type )

        return self.get(request)

    pass

class PrivacyPolicyView(PrivateView):

    def get(self, request):
        return render(request, 'frontend/privacy-policy.html', {
            'title': 'BeeMe Privacy Policy',
        })

    pass

class PusherAuthView(PrivateView):

    def post(self, request):
        channel_name = request.POST['channel_name']
        socket_id = request.POST['socket_id']

        if not request.user.is_authenticated:
            return HttpResponseForbidden()
        if channel_name != 'private-{user_code}'.format(user_code=request.user.code):
            return HttpResponseForbidden()

        auth = pusher_client.authenticate(
            channel=channel_name,
            socket_id=socket_id
        )

        return JsonResponse(auth)

    pass

class ReadMoreView(PrivateView):

    def get(self, request):
        return render(request, 'frontend/read-more.html', {
            'title': 'Read more about it',
        })

    pass

class RoomView(PrivateView):

    channel = 'room-{}'

    def get(self, request):
        if request.user.is_authenticated:
            teamno = request.user.teamno
            pass
        else:
            teamno = request.session.get('teamno')

            if not teamno:
                teamno = user_random_team()
                request.session['teamno'] = teamno
                pass
            pass

        if request.GET.get('action') == 'refresh_latest_five':
            commands = self.commands(teamno)

            if commands['queue_changed']:
                self.send_queue_change(self.channel.format(teamno), teamno)

            last_five = commands['last_five']

            return JsonResponse(last_five, safe=False)

        if request.GET.get('action') == 'refresh_top_five':
            commands = self.commands(teamno)

            if commands['queue_changed']:
                self.send_queue_change(self.channel.format(teamno), teamno)

            top_five = commands['top_five']

            return JsonResponse(top_five, safe=False)

        commands_queue = Command.objects \
            .filter(is_accepted=True, is_performed=False) \
            .order_by('-ord')

        team = {
            'no': teamno,
            'media': getattr(config, 'TEAM{}_MEDIA'.format(teamno))
        }

        commands = self.commands(teamno)

        if commands['queue_changed']:
            self.send_queue_change(self.channel.format(teamno), teamno)

        return render(request, 'frontend/room.html', {
            'channel': self.channel.format(teamno),

            'commands': commands,
            'team': team,

            'message': Message.objects.filter(teamno=teamno, created_at__gte=(timezone.now() - datetime.timedelta(minutes=15))).order_by('-created_at').first(),
            'task': Task.objects.filter(teamno=teamno, is_completed=False).order_by('created_at').first(),

            'pusher_config': {
                'key': settings.PUSHER_KEY,
                'cluster': settings.PUSHER_CLUSTER,
            }
        })

    def post(self, request):
        """
        Handle user actions.
        """
        # only authenticated users are allowed to make changes.
        if not request.user.is_authenticated: return HttpResponseForbidden()

        action = request.POST.get('action')

        if request.user.is_authenticated:
            teamno = request.user.teamno
            pass
        else:
            teamno = request.session.get('teamno')

            if not teamno:
                teamno = user_random_team()
                request.session['teamno'] = teamno
                pass
            pass

        # handle command being added
        if action == 'command':
            text = request.POST.get('text', '').strip()
            text = text.rstrip('.')

            if len(text) < 2:
                error = 'command too short (min_length=1)'
                return JsonResponse({ 'error':error }, status=400)
            if len(text) > 50:
                error = 'command too long (max_length=50)'
                return JsonResponse({ 'error':error }, status=400)

            # check for shadow banning
            if request.user.is_banned:
                commands = self.commands(request.user.teamno)
                return JsonResponse({ 'status':'success', 'commands':commands }, status=200)

            command_timediff = config.COMMAND_EXPIRATION
            if not isinstance(command_timediff, datetime.timedelta): command_timediff = datetime.timedelta(minutes=command_timediff)
            command_cutoff = timezone.now() - command_timediff

            command = Command.objects.filter(
                is_flagged=False,
                is_performed=False,
                teamno=teamno,
                timestamp__gte=command_cutoff,
                text__iexact=text
            ).order_by('-timestamp').first()

            with transaction.atomic():
                # create command
                if command is None:
                    command = Command.objects.create(
                        text=text,
                        teamno=teamno,
                        created_by=request.user,
                        created_from=request.META['REMOTE_ADDR']
                    )

                # add upvote
                changed = command.vote_up(user=request.user, created_from=request.META['REMOTE_ADDR'])

                if changed:
                    transaction.on_commit(lambda: self.send_votes_change(self.channel.format(teamno), teamno))
                pass

            commands = self.commands(request.user.teamno)

            if commands['queue_changed']:
                self.send_queue_change(self.channel.format(request.user.teamno), request.user.teamno)

            return JsonResponse({ 'status':'success', 'commands':commands }, status=202)

        # handle command is done
        if action == 'done':
            # only superusers users are allowed to accept commands
            if not request.user.is_staff: return HttpResponseForbidden()

            pk = request.POST.get('id')
            command = get_object_or_404(Command, pk=pk)

            with transaction.atomic():
                command.is_performed = True
                command.save()

                user = command.created_by
                user.xp += 1
                user.save()

                transaction.on_commit(lambda: self.send_queue_change(self.channel.format(teamno), teamno))
                pass

            commands = self.commands(request.user.teamno)

            return JsonResponse({ 'status':'success', 'commands':commands })

        # handle command is flag
        if action == 'flag':
            # only superusers users are allowed to flag commands
            if not request.user.is_staff: return HttpResponseForbidden()

            pk = request.POST.get('id')
            command = get_object_or_404(Command, pk=pk)

            with transaction.atomic():
                command.is_flagged = True
                command.save()

                count_user_flagged = Command.objects.filter(is_flagged=True, created_by_id=command.created_by_id).count()

                if count_user_flagged >= config.COMMAND_FLAGS_TO_BAN:
                    user = command.created_by
                    user.is_banned = True
                    user.save()
                    pass

                transaction.on_commit(lambda: self.send_votes_change(self.channel.format(teamno), teamno))
                pass

            commands = self.commands(request.user.teamno)

            return JsonResponse({ 'status':'success', 'commands':commands })

        # handle up/down vote
        if action == 'up' or action == 'down':
            pk = request.POST.get('id')
            command = get_object_or_404(Command, pk=pk)

            # check for shadow banning
            if request.user.is_banned:
                commands = self.commands(request.user.teamno)
                return JsonResponse({ 'status':'success', 'commands':commands })

            with transaction.atomic():
                if action == 'up':
                    changed = command.vote_up(user=request.user, created_from=request.META['REMOTE_ADDR'])
                    pass
                elif action == 'down':
                    changed = command.vote_down(user=request.user, created_from=request.META['REMOTE_ADDR'])
                    pass

                if changed:
                    transaction.on_commit(lambda: self.send_votes_change(self.channel.format(teamno), teamno))
                pass

            commands = self.commands(request.user.teamno)

            if commands['queue_changed']:
                self.send_queue_change(self.channel.format(request.user.teamno), request.user.teamno)

            return JsonResponse({ 'status':'success', 'commands':commands }, status=202)

        # handle message from experimenter
        if action == 'current_task':
            # only superusers users are allowed to set current task
            if not request.user.is_staff: return HttpResponseForbidden()

            text = request.POST.get('text', '').strip()

            if len(text) < 2:
                error = 'task too short (min_length=2)'
                return JsonResponse({ 'error':error }, status=400)
            if len(text) > 250:
                error = 'task too long (max_length=250)'
                return JsonResponse({ 'error':error }, status=400)

            with transaction.atomic():
                # create task
                task = Task.objects.create(
                    teamno=request.user.teamno,
                    text=text,
                    created_by=request.user,
                    created_from=request.META['REMOTE_ADDR']
                )

                transaction.on_commit(lambda: self.send_task(self.channel.format(request.user.teamno), task))
                pass

            return JsonResponse({ 'status':'success' }, status=202)

        # handle message from experimenter
        if action == 'current_task_done':
            # only superusers users are allowed to send messages.
            if not request.user.is_staff: return HttpResponseForbidden()

            task_id = request.POST.get('id')

            task = get_object_or_404(Task, teamno=request.user.teamno, id=task_id)

            with transaction.atomic():
                task.is_completed = True
                task.save()

                next_task = Task.objects.filter(teamno=teamno, is_completed=False).order_by('created_at').first()

                transaction.on_commit(lambda: self.send_task(self.channel.format(request.user.teamno), next_task))
                pass

            return JsonResponse({ 'status':'success' }, status=202)

        # handle message from experimenter
        if action == 'hive_msg':
            # only superusers users are allowed to send messages.
            if not request.user.is_staff: return HttpResponseForbidden()

            text = request.POST.get('text', '').strip()

            if len(text) < 2:
                error = 'command too short (min_length=1)'
                return JsonResponse({ 'error':error }, status=400)
            if len(text) > 10000:
                error = 'command too long (max_length=10000)'
                return JsonResponse({ 'error':error }, status=400)

            with transaction.atomic():
                # create command
                message = Message.objects.create(
                    teamno=request.user.teamno,
                    text=text,
                    created_by=request.user,
                    created_from=request.META['REMOTE_ADDR']
                )

                transaction.on_commit(lambda: self.send_message(self.channel.format(request.user.teamno), message))
                pass

            return JsonResponse({ 'status':'success' }, status=202)

        return JsonResponse({ 'error':'unknown action' }, status=400)

    def commands(self, teamno, limit=5, command_timediff=None, vote_timediff=None):
        """
        build complex queries to get the commands, and the count of their votes within a specific time window.
        """
        queue_changed = False

        if command_timediff is None: command_timediff = config.COMMAND_EXPIRATION
        if vote_timediff is None: vote_timediff = config.COMMAND_VOTE_EXPIRATION

        if not isinstance(command_timediff, datetime.timedelta): command_timediff = datetime.timedelta(minutes=command_timediff)
        if not isinstance(vote_timediff, datetime.timedelta): vote_timediff = datetime.timedelta(minutes=vote_timediff)

        # get current time
        now = timezone.now()
        # calculate cutoff time
        command_cutoff = now - command_timediff
        vote_cutoff = now - vote_timediff

        # get downvotes by command, within cutoff, and disable sorting
        downvotes = VoteDown.objects.filter(removed=False, timestamp__gte=vote_cutoff, command=OuterRef('pk')).order_by().values('command')
        # count downvotes by command
        downvotes_count = downvotes.annotate(downvotes_count=Count('pk')).values('downvotes_count')
        # get upvotes by command, within cutoff, and disable sorting
        upvotes = VoteUp.objects.filter(removed=False, timestamp__gte=vote_cutoff, command=OuterRef('pk')).order_by().values('command')
        # count upvotes by command
        upvotes_count = upvotes.annotate(upvotes_count=Count('pk')).values('upvotes_count')

        # only show unaccepted commands
        # add downvotes, with 0 if none available, as an int
        # add upvotes, with 0 if none available, as an int
        # calculate net total votes
        # return the id,text, and three calculated fields as a named tuple
        commands = Command.objects \
            .filter(is_flagged=False, is_performed=False, teamno=teamno, timestamp__gte=command_cutoff) \
            .annotate(
                downvotes_count=Coalesce(Subquery(downvotes_count),Value(0), output_field=models.IntegerField()) ,
                upvotes_count=Coalesce(Subquery(upvotes_count),Value(0), output_field=models.IntegerField())
            ) \
            .annotate(votes_count=(F('upvotes_count') - F('downvotes_count')))

        # order and limit
        commands_top_five = commands.filter(is_queued=False).order_by('-votes_count')[:limit]
        commands_last_five = commands.filter(is_queued=False).order_by('-timestamp')[:limit]
        commands_queued = commands.filter(is_queued=True).order_by('timestamp')

        if not commands_queued.exists():
            command = commands_top_five.first()

            if command:
                command.is_queued = True
                command.save()

                queue_changed = True
                pass
            pass

        # only get values
        commands_top_five = commands_top_five.values_list('id','created_by','text','timestamp','votes_count','downvotes_count','upvotes_count', named=True)
        commands_last_five = commands_last_five.values_list('id','created_by','text','timestamp','votes_count','downvotes_count','upvotes_count', named=True)
        commands_queued = commands_queued.values_list('id','created_by','text','timestamp','votes_count','downvotes_count','upvotes_count', named=True)

        # convert to dicts
        commands_top_five = tuple( map( command_to_dict, commands_top_five ) )
        commands_last_five = tuple( map(command_to_dict, commands_last_five ) )
        commands_queued = tuple( map(command_to_dict, commands_queued ) )

        data = {
            'top_five': commands_top_five,
            'last_five': commands_last_five,
            'queued': commands_queued,
            'queue_changed': queue_changed,
        }

        return data

    def send_message(self, channel, message):
        """
        Publish messages from experimenter
        """

        event = 'message-change'

        pusher_client.trigger(channel, event, {
            'id': str( message.id ),
            'msg': message.text,
        })

        return

    def send_task(self, channel, task):
        """
        Publish messages from experimenter
        """

        event = 'task-change'

        if task:
            pusher_client.trigger(channel, event, {
                'id': str( task.id ),
                'msg': task.text,
            })
            pass
        else:
            pusher_client.trigger(channel, event, {
                'id': '',
                'msg': '',
            })
            pass
        return

    #@ratelimit
    def send_queue_change(self, channel, teamno):
        """
        Publish vote changes to all subscribers.

        Respects rate limits to flooding clients with vote changes.
        """

        event = 'queue-change'

        pusher_client.trigger(channel, event, self.commands(teamno))
        return

    def send_votes_change(self, channel, teamno):
        """
        Publish vote changes to all subscribers.

        Respects rate limits to flooding clients with vote changes.
        """

        event = 'votes-change'
        ratelimit_key = '{}:{}'.format( channel, event )

        pusher_client.trigger(channel, event, self.commands(teamno))
        return

    pass

class RulesView(PublicView):

    def get(self, request):
        return render(request, 'frontend/rules.html', {
            'title': 'BeeMe Rules',
        })

    pass

class SignupView(PrivateView):

    def get(self, request):
        form_login = AuthenticationForm()
        form_signup = SignUpForm(auto_id='signup_%s')

        if request.user.is_authenticated:
            return redirect('frontend:room')

        return render(request, 'registration/login.html', {
            'title': 'BeeMe Sign Up',

            'form': form_login,
            'form_signup': form_signup,

            'is_signup': True,
        })

    def post(self, request):
        User = get_user_model()

        form_login = AuthenticationForm()
        form_signup = SignUpForm(request.POST, auto_id='signup_%s')

        if form_signup.is_valid():
            email = form_signup.cleaned_data['email']
            password = form_signup.cleaned_data['password']

            user = User.objects.create_user(username=email, email=email, password=password)

            self.send_welcome(request, user)

            auth_login(request, user)

            return redirect( 'frontend:story' )

        return render(request, 'registration/login.html', {
            'title': 'BeeMe Sign Up',

            'form': form_login,
            'form_signup': form_signup,

            'is_signup': True,
        })

    def send_welcome(self, request, user):
        # TODO: Move this to model
        # TODO: create management command to send pending welcome emails

        email_subject = 'Welcome to BeeMe'
        email_message = """
We’re glad you could join us.

Now that you are signed up, join the story: {url}
        """.strip().format(
            url=request.build_absolute_uri('/story')
        )

        email = EmailMessage(
            email_subject,
            email_message,
            to=[user.email]
        )

        try:
            email.send()

            user.welcome_email_sent = True
            user.save()
            pass
        except Exception as e:
            logger.exception('Error sending welcome email', e, user.id) # TODO: add more context to error
            pass
        return

    pass

class StoryView(PrivateView):

    def get(self, request):
        html1 = config.STORY_INTRO
        
        if not request.user.is_authenticated:
            html2 = ''
        elif request.user.teamno == 1:
            html2 = config.TEAM1_STORY
        elif request.user.teamno == 2:
            html2 = config.TEAM2_STORY
        else:
            html2 = ''

        return render(request, 'frontend/story.html', {
            'title': 'BeeMe Story',

            'html1': html1,
            'html2': html2,
        })

    pass

class TermsOfServiceView(PrivateView):

    def get(self, request):
        return render(request, 'frontend/terms-of-service.html', {
            'title': 'BeeMe Rules',
            'notos': True,
        })

    def post(self, request):
        if not request.user.is_authenticated: return HttpResponseForbidden()

        if request.POST.get('accept') == '1':
            request.user.tos = True
            request.user.save()
            pass

        if request.is_ajax():
            return JsonResponse({ 'success':True })

        return redirect('frontend:story')

    pass


def empty(request):
    return HttpResponse('')


__all__ = (
    'CreditsView',
    'ManageView',
    'RoomView',
    'RulesView',
    'SignupView',
    'StoryView',
    'PusherAuth',
    'empty',
)
