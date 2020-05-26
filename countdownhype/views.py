# stdlib imports
import datetime
# django imports
from django.shortcuts import render, redirect
from django.utils.timezone import utc
from django.views.decorators.cache import cache_control


# function views

def countdown(request):
    return render(request, 'countdownhype/countdown.html')

@cache_control(public=True)
def index(request):
    # modify these to change when the link to the game becomes available
    year = 2018
    month = 10
    days = 31
    hours = 23 # use 24-hour time
    minutes = 0
    seconds = 0

    release_datetime_utc = datetime.datetime(year, month, days, hours, minutes, seconds)
    eastern_time_conversion = datetime.timedelta(hours=4)
    release_datetime = release_datetime_utc + eastern_time_conversion
    now = datetime.datetime.utcnow()

    context = {}

    if release_datetime < now:
        context['game_launch'] = 'true'

    return render(request, 'countdownhype/index.html', context)

def redir(request):
    return redirect('index')
