# stdlib imports
import csv
import os
# django imports
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
# project imports
from beeme.core.models import BannedEmailDomain


class Command(BaseCommand):

    help = 'Load list of banned domains'

    def add_arguments(self, parser):
        return

    def handle(self, *args, **options):
        # https://github.com/ivolo/disposable-email-domains
        path = os.path.join(settings.BASE_DIR, 'data', 'bannen-email-domains.csv')

        count = 0
        existing = set( BannedEmailDomain.objects.all().values_list('domain', flat=True) )
        existing_count = len(existing)

        with transaction.atomic():
            with open(path, 'r') as fin:
                reader = csv.reader(fin)

                first = True
                for row in reader:
                    if first:
                        first = False
                        continue

                    domain, = row
                    
                    if domain in existing:
                        continue

                    BannedEmailDomain.objects.create(domain=domain)

                    existing.add(domain) ; count += 1

                    self.stdout.write(domain)
                    pass
                pass
            pass

        self.stdout.write('')

        self.stdout.write(self.style.SUCCESS( '{0:,} domains before'.format( existing_count ) ))
        self.stdout.write(self.style.SUCCESS( '{0:,} domains added'.format( count ) ))
        self.stdout.write(self.style.SUCCESS( '{0:,} domains banned'.format( BannedEmailDomain.objects.all().count() ) ))
        return

    pass
