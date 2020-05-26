# stdlib imports
import datetime
# django imports
from django.conf import settings
from django.core.cache import cache
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
from django.utils import timezone
from django.views import View
# third-party imports
import pusher
# local imports
from beeme.core.models import Command
from beeme.core.models import Message
from beeme.core.models import VoteDown
from beeme.core.models import VoteUp


RATELIMIT_COUNT = 1 # occurrences per period
RATELIMIT_PERIOD = 1 # seconds
VOTE_EXPIRATION = datetime.timedelta(minutes=15) # time window during which votes are valid


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


# function views

class IndexView(View):

    channel = 'controlroom'

    def get(self, request):
        commands_queue = Command.objects \
            .filter(is_accepted=True, is_performed=False) \
            .order_by('-ord')

        return render(request, 'controlroom/index.html', {
            'channel': self.channel,

            'commands': self.commands(),
            #'queue': tuple( map( command_to_dict, commands_queue.values_list('id','command_text','votes', named=True) ) ),

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
    
        # handle command being added
        if action == 'command':
            text = request.POST.get('text', '').strip()

            if len(text) < 2:
                error = 'command too short (min_length=1)'
                return JsonResponse({ 'error':error }, status=400)
            if len(text) > 50:
                error = 'command too long (max_length=50)'
                return JsonResponse({ 'error':error }, status=400)

            with transaction.atomic():
                # create command
                command = Command.objects.create(text=text)
                # add initial upvote
                command.vote_up(user=request.user)

                transaction.on_commit(lambda: self.send_votes_change(self.channel))
                pass

            return JsonResponse({ 'status':'success' }, status=202)

        # handle up/down vote
        if action == 'up' or action == 'down':
            pk = request.POST.get('id')
            command = get_object_or_404(Command, pk=pk)

            with transaction.atomic():
                if action == 'up':
                    command.vote_up(user=request.user)
                    pass
                elif action == 'down':
                    command.vote_down(user=request.user)
                    pass

                transaction.on_commit(lambda: self.send_votes_change(self.channel))
                pass

            return JsonResponse({ 'status':'success' }, status=202)

        # handle message from experimenter
        if action == 'experimenter_msg':
            # only superusers users are allowed to send messages.
            if not request.user.is_superuser: return HttpResponseForbidden()

            text = request.POST.get('text', '').strip()

            if len(text) < 2:
                error = 'command too short (min_length=1)'
                return JsonResponse({ 'error':error }, status=400)
            if len(text) > 250:
                error = 'command too long (max_length=250)'
                return JsonResponse({ 'error':error }, status=400)

            with transaction.atomic():
                # create command
                message = Message.objects.create(text=text, user=request.user)

                transaction.on_commit(lambda: self.send_message(self.channel, message))
                pass

            return JsonResponse({ 'status':'success' }, status=202)

        return JsonResponse({ 'error':'unknown action' }, status=400)

    def commands(self, limit=5, timediff=VOTE_EXPIRATION):
        """
        build complex queries to get the commands, and the count of their votes within a specific time window.
        """

        # get current time
        now = timezone.now()
        # calculate cutoff time
        cutoff = now - timediff

        # get downvotes by command, within cutoff, and disable sorting
        downvotes = VoteDown.objects.filter(command=OuterRef('pk')).order_by().values('command')
        # count downvotes by command
        downvotes_count = downvotes.annotate(downvotes_count=Count('pk')).values('downvotes_count')
        # get upvotes by command, within cutoff, and disable sorting
        upvotes = VoteUp.objects.filter(command=OuterRef('pk')).order_by().values('command')
        # count upvotes by command
        upvotes_count = upvotes.annotate(upvotes_count=Count('pk')).values('upvotes_count')

        # only show unaccepted commands
        # add downvotes, with 0 if none available, as an int
        # add upvotes, with 0 if none available, as an int
        # calculate net total votes
        # return the id,text, and three calculated fields as a named tuple
        commands = Command.objects \
            .filter(is_accepted=False) \
            .annotate(
                downvotes_count=Coalesce(Subquery(downvotes_count),Value(0), output_field=models.IntegerField()) ,
                upvotes_count=Coalesce(Subquery(upvotes_count),Value(0), output_field=models.IntegerField())
            ) \
            .annotate(votes_count=(F('upvotes_count') - F('downvotes_count'))) \
            .values_list('id','text','timestamp','votes_count','downvotes_count','upvotes_count', named=True)

        # order and limit
        commands_top_five = commands.order_by('-votes_count')[:limit]
        commands_last_five = commands.order_by('-timestamp')[:limit]

        # convert to dicts
        commands_top_five = tuple( map( command_to_dict, commands_top_five ) )
        commands_last_five = tuple( map(command_to_dict, commands_last_five ) )

        data = {
            'top_five': commands_top_five,
            'last_five': commands_last_five,
        }

        return data

    def send_message(self, channel, message):
        """
        Publish messages from experimenter
        """

        event = 'experimenter-msg'

        pusher_client.trigger(channel, event, {
            'id': str( message.id ),
            'msg': message.text,
        })

        return

    def send_votes_change(self, channel):
        """
        Publish vote changes to all subscribers.
        
        Respects rate limits to flooding clients with vote changes.
        """

        event = 'votes-change'
        ratelimit_key = '{}:{}'.format( channel, event )

        if ratelimit_exceeded(ratelimit_key):
            print('RATELIMITED')
            return

        print( 'send_votes_change', channel, event )
        pusher_client.trigger(channel, event, self.commands())

        ratelimit_increment(ratelimit_key)
        return

    pass

def update_queue_table(request):
    commands = Command.objects.filter(is_accepted=True, is_performed=False).order_by('-org')
    return render(request, 'controlroom/update_queue_table.html', {'commands': commands})


__all__ = (
    'IndexView',
)
