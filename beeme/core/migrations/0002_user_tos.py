# Generated by Django 2.1.1 on 2018-10-31 00:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='tos',
            field=models.BooleanField(db_index=True, default=False, verbose_name='TOS Agreement'),
        ),
    ]
