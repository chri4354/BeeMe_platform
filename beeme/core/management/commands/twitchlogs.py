# stdlib imports
import pprint ; pp = pprint.PrettyPrinter(indent=4)
import urllib.parse
# django imports
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
# third-party imports
import requests
# project imports


class Twitch(object):

    """
    https://dev.twitch.tv/console/apps
    """

    def __init__(self, client_id=None, oauth_token=None):
        self.client_id = client_id
        self.oauth_token = oauth_token

        self.http = requests.Session()
        self.http.headers.update({
            'Accept': 'application/vnd.twitchtv.v5+json',
            'Authorization': 'OAuth ' + self.oauth_token,
            'Client-ID': self.client_id,
        })

        self.httpsimple = requests.Session()
        self.httpsimple.headers.update({
            'Accept': 'application/vnd.twitchtv.v5+json',
            'Client-ID': self.client_id,
        })
        return

    def channel(self, user_id=None, user_login=None):
        r = self.http.get('https://api.twitch.tv/kraken/channel')
        
        return r.json()

    def streams(self, user_id=None, user_login=None):
        params = {}

        if user_id: params['user_id'] = user_id
        if user_login: params['user_login'] = user_id

        r = self.http.get('https://api.twitch.tv/helix/streams', params=params)
        print( r.json() )
        return

    def user(self, login):
        users = self.users(login=login)
        if users: return users[0]
        return None

    def users(self, id_=None, login=None):
        params = []

        if isinstance(id_, (int,str)):
            params.append(('id', id_))
        if isinstance(login, (int,str)):
            params.append(('login', login))

        r = self.http.get('https://api.twitch.tv/kraken/users', params=params)

        data = r.json()
        data = data['users']

        return data

    def videos(self, channel_id):
        limit = 10
        offset = 0

        params = {
            'limit': limit,
            'offset': offset,
            'sort': 'time',
        }

        items = []
        
        while True:
            r = self.http.get('https://api.twitch.tv/kraken/channels/%s/videos' % channel_id, params=params)
            
            data = r.json()
            videos = data['videos']

            items.extend(videos)
            
            if len(videos) < limit: break
            
            params['offset'] += limit
            pass

        return items

    def video_comments(self, video_id):
        r = self.httpsimple.get('https://api.twitch.tv/v5/videos/%s/comments' % video_id)
        
        data = r.json()
        comments = data['comments']

        pp.pprint(data)
        return

    pass


class Command(BaseCommand):

    help = 'Get Twitch logs'

    def add_arguments(self, parser):
        return

    def handle(self, *args, **options):
        params = {
            'client_id': settings.TWITCH_CLIENT_ID,
            'redirect_uri': 'http://beeme.devpreviews.com/oauth/twitch',
            'response_type': 'token',
            'scope': ' '.join([
                'channel_feed_read',
                'channel_read',
                'chat:edit',
                'chat:read',
                'user_read',
            ])
        }

        url = 'https://id.twitch.tv/oauth2/authorize' +'?'+ urllib.parse.urlencode(params)
        #print(url)
        
        oauth = 'ks9mhq1mou5j62qaig3iaa9wacv7mm'

        twitch = Twitch(settings.TWITCH_CLIENT_ID, oauth)

        user = twitch.user('winter_beeme')
        user_id = user['_id']
        
        channel = twitch.channel()
        channel_id = channel['_id']

        videos = twitch.videos(channel_id)
        video = videos[0]
       
        video_id = video['_id']
        if video_id.startswith('v'): video_id = video_id[1:]

        print( 'video_id', video_id )

        twitch.video_comments(video_id)
        return

    pass
