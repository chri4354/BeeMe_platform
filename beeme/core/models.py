# stdlib imports
import hashlib
import os
import random ; random.seed()
import uuid
# django imports
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.cache import cache
from django.db import models
from django.utils import timezone


NUM_TEAMS = 2


# helper methods

def user_alternate_team():
    if 'user_alternate_team' not in cache:
        cache.set('user_alternate_team', 0, timeout=None)

    val = cache.incr('user_alternate_team')
    team = (val % 2) + 1

    return team

def user_random_team():
    return random.randint(1, NUM_TEAMS)


# concrete models

class BannedEmailDomain(models.Model):

    domain = models.CharField(db_index=True, max_length=50, unique=True)

    pass

class Command(models.Model):
    """
    This represents the commands that users submit through the webform
    command_text represents the raw text that users submit as their command
    submit_time represents the time that the command was submitted
    votes represents how many votes the command has (each command begins with one vote)
    command_order represents the command's chronological position in the history of accepted commands
    command_order remains null if the command is never accepted and is performed by the actor
    _counter is a counter to keep track of the next available index in the history of accepted commands
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now)
    text = models.CharField(max_length=50)
    ord = models.PositiveIntegerField(default=0)
    teamno = models.PositiveSmallIntegerField('Team No.', db_index=True)
    is_accepted = models.BooleanField(default=False, db_index=True)
    is_flagged = models.BooleanField(default=False, db_index=True)
    is_performed = models.BooleanField(default=False, db_index=True)
    is_queued = models.BooleanField(default=False, db_index=True)

    #created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, related_name='+')
    created_from = models.GenericIPAddressField()

    def __str__(self):
        return self.text

    def append_to_accepted_history(self):
        """
        gives Command a command_order integer value based on the current value of _counter
        """
        self.command_order = next(self._counter)
        return

    def performed(self):
        """
        sets was_performed to True to indicate that the Command has been performed by the actor
        """
        if self.was_performed: raise Exception( 'Command was already performed' )
        self.was_performed = True
        return

    def was_accepted(self):
        """
        returns True if Command has a command order (it was accepted to the queue)
        """
        return self.command_order is not None

    def vote_down(self, user, created_from, commit=True):
        """
        subtract one vote from Command object
        """

        changed = False

        has_up = VoteUp.objects.filter(command=self, user=user).exists()
        has_down = VoteDown.objects.filter(command=self, user=user).exists()

        if user.is_staff:
            VoteDown.objects.create(command=self, user=user, created_from=created_from)

            changed = True
            pass
        elif has_up:
            VoteUp.objects.filter(command=self, user=user).update(removed=True)
            VoteDown.objects.update_or_create(
                command=self,
                user=user,

                defaults=dict(
                    created_from=created_from,
                    removed=False
                )
            )

            changed = True
            pass
        elif has_down:
            changed = False
            pass
        else:
            VoteDown.objects.create(command=self, user=user, created_from=created_from)
            changed = True
            pass

        if commit: self.save()

        return changed

    def vote_up(self, user, created_from, commit=True):
        """
        add one vote to Command object
        """

        changed = False

        has_up = VoteUp.objects.filter(command=self, user=user).exists()
        has_down = VoteDown.objects.filter(command=self, user=user).exists()

        if user.is_staff:
            VoteUp.objects.create(command=self, user=user, created_from=created_from)

            changed = True
            pass
        elif has_up:
            changed = False
            pass
        elif has_down:
            VoteDown.objects.filter(command=self, user=user).update(removed=True)
            VoteUp.objects.update_or_create(
                command=self,
                user=user,
                
                defaults=dict(
                    created_from=created_from,
                    removed=False
                )
            )

            changed = True
            pass
        else:
            VoteUp.objects.create(command=self, user=user, created_from=created_from)
            changed = True
            pass

        if commit: self.save()

        return changed

    pass

class Gallery(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=250)

    def __str__(self):
        return self.title

    pass

class GalleryItem(models.Model):

    gallery = models.ForeignKey('Gallery', models.CASCADE, related_name='items')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ord = models.PositiveIntegerField(default=0, db_index=True)
    title = models.CharField(blank=True, max_length=250)
    name = models.CharField(blank=True, max_length=250)
    type = models.CharField(max_length=50)
    image_path = models.FilePathField(blank=True, path=os.path.join(settings.MEDIA_ROOT, 'gallery', 'images'), recursive=True, allow_files=True)
    image_url = models.URLField(blank=True)
    vimeo_id = models.CharField(blank=True, max_length=50)
    youtube_id = models.CharField(blank=True, max_length=50)

    class Meta:
        ordering = ('gallery','ord','name')

    def __str__(self):
        return self.title

    def get_preview_image_src(self):
        if self.type == 'image':
            src = self.image_url
            base,ext = os.path.splitext(src)
            src = base + '.thumb' + ext
            return src
        elif self.type == 'vimeo':
            return self.image_url
        elif self.type == 'youtube':
            src = 'https://i.ytimg.com/vi/{0}/maxresdefault.jpg'.format(self.youtube_id)
            return src
        else:
            raise Exception( 'unexpected type: %s' % self.type )

        return

    pass

class Message(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    teamno = models.PositiveSmallIntegerField('Team No.', db_index=True)
    text = models.TextField(max_length=50)

    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, related_name='messages')
    created_from = models.GenericIPAddressField()

    def __str__(self):
        return self.text

    pass

class Task(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField()
    teamno = models.PositiveSmallIntegerField('Team No.', db_index=True)
    is_completed = models.BooleanField('Is Completed', db_index=True, default=False)

    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE, related_name='+')
    created_from = models.GenericIPAddressField()

    pass

class User(AbstractUser):

    email = models.EmailField('Email Address', unique=True)
    teamno = models.PositiveSmallIntegerField('Team No.', default=0, db_index=True)
    is_banned = models.BooleanField('Is Banned', db_index=True, default=False)
    tos = models.BooleanField('TOS Agreement', db_index=True, default=False)
    xp = models.PositiveIntegerField('Experience Points', default=0)
    welcome_email_sent = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    @property
    def code(self):
        s = hashlib.md5( self.email.encode('utf-8') ).hexdigest()
        return s

    pass

class VoteDown(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    command = models.ForeignKey('Command', models.PROTECT, related_name='downvotes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, related_name='downvotes')

    created_from = models.GenericIPAddressField()
    removed = models.BooleanField(db_index=True, default=False)

    pass

class VoteUp(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    command = models.ForeignKey('Command', models.PROTECT, related_name='upvotes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.PROTECT, related_name='upvotes')

    created_from = models.GenericIPAddressField()
    removed = models.BooleanField(db_index=True, default=False)

    pass


# signal receivers

from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, raw, **kwargs):
    if created and instance.teamno == 0:
        instance.teamno = user_alternate_team()
        instance.save()
        pass
    return

@receiver(pre_save, sender=User)
def user_pre_save(sender, instance, raw, **kwargs):
    instance.username = instance.email
    return
