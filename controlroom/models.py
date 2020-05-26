# stdlib imports
from itertools import count
# django imports
from django.db import models


# concrete models

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

    command_text = models.CharField(max_length=50)
    submit_time = models.DateTimeField(auto_now_add=True, blank=True)
    votes = models.IntegerField(default=1)
    command_order = models.IntegerField(null=True, blank=True, unique=True)
    was_performed = models.BooleanField(default=False)

    _counter = count(1)

    def __repr__(self):
        return ('id: ' + str(self.id) + '; '
              + 'submit_time: ' + str(self.submit_time) + '; '
              + 'votes: ' + str(self.votes) + '; '
              + 'command_order: ' + str(self.command_order) + '; '
              + 'was_performed: ' + str(self.was_performed) + '; '
              + 'command_text: ' + str(self.command_text) + ';\n')

    def __str__(self):
        return self.command_text

    # gives Command a command_order integer value based on the current value of _counter
    def append_to_accepted_history(self):
        self.command_order = next(self._counter)

    # returns True if Command has a command order (it was accepted to the queue)
    def was_accepted(self):
        return self.command_order is not None

    # sets was_performed to True to indicate that the Command has been performed by the actor
    def performed(self):
        if not self.was_performed:
            self.was_performed = True
        else:
            raise Exception("Command was already performed")

    def vote_down(self, commit=True):
        """
        subtract one vote from Command object
        """

        self.votes -= 1
        
        if commit: self.save()
        return

    def vote_up(self, commit=True):
        """
        add one vote to Command object
        """

        self.votes += 1

        if commit: self.save()
        return

    pass
