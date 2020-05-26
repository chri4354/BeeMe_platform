# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('controlroom', '0002_remove_command_was_performed'),
    ]

    operations = [
        migrations.AddField(
            model_name='command',
            name='was_performed',
            field=models.BooleanField(default=False),
        ),
    ]
