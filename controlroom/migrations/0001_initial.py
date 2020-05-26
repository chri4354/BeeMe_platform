# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Command',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('command_text', models.CharField(max_length=50)),
                ('submit_time', models.DateTimeField(auto_now_add=True)),
                ('votes', models.IntegerField(default=1)),
                ('command_order', models.IntegerField(unique=True, null=True, blank=True)),
                ('was_performed', models.BooleanField(default=False)),
            ],
        ),
    ]
