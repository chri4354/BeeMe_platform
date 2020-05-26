# django import
from django.conf import settings


# context processors

def debug(request):
    context_extras = {}

    if settings.DEBUG:
        context_extras['debug'] = True

    return context_extras

def team(request):
    context_extras = {}

    if request.user.is_authenticated:
        teamno = request.user.teamno
        pass
    else:
        teamno = request.session.get('teamno')
        pass

    if not teamno:
        teamno = 0
        pass

    context_extras['teamno'] = teamno

    return context_extras

