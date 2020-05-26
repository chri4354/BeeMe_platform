# stdlib imports
# django imports
from django.core.management.base import BaseCommand, CommandError
# project imports
from beeme.core.models import User

class Command(BaseCommand):

    help = 'Create test users'

    def add_arguments(self, parser):
        parser.add_argument('num', default=1, nargs='?', type=int)
        return

    def handle(self, *args, **options):
        num = options['num']

        if num < 1:
            raise CommandError( 'Invalid argument NUM: %r' % num )

        emails = User.objects \
            .filter(email__startswith='user', email__endswith='@beeme.online') \
            .values_list('email', flat=True)
        numbers = set( map(int, (
            email[ len('user') : -len('@beeme.online') ]
            for email in emails
        ) ) )

        last_num = max(numbers)


        for i in range(num):
            n = last_num + i + 1

            email = 'user{}@beeme.online'.format(n)
            password = User.objects.make_random_password(length=8)

            user = User.objects.create_user(email=email, username=email, password=password)

            self.stdout.write(self.style.SUCCESS( 'Created user:' ))
            self.stdout.write(self.style.SUCCESS( '    Username: %s' % email ))
            self.stdout.write(self.style.SUCCESS( '    Password: %s' % password ))
            self.stdout.write(self.style.SUCCESS( '        Team: %s' % user.teamno ))
            self.stdout.write('')
            self.stdout.flush()
            pass
        return
