# Generated by Django 2.1.7 on 2019-03-11 06:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_user_welcome_email_sent_true'),
    ]

    operations = [
        migrations.CreateModel(
            name='BannedEmailDomain',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('domain', models.CharField(db_index=True, max_length=50, unique=True)),
            ],
        ),
    ]
