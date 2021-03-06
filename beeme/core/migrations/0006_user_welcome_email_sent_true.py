# Generated by Django 2.1.7 on 2019-03-11 04:59

from django.db import migrations


def set_existing_true(apps, schema_editor):
    User = apps.get_model('core', 'User')

    for user in User.objects.all():
        user.welcome_email_sent = True
        user.save()
        pass

    return

def noop(apps, schema_editor):
    return

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_user_welcome_email_sent'),
    ]

    operations = [
        migrations.RunPython(set_existing_true, noop),
    ]
