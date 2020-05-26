# stdlib imports
import collections
import os
# third-party imports
import environ # https://django-environ.readthedocs.io/en/latest/


root = environ.Path(__file__) - 2  # get root of the project


# create environment
env = environ.Env() 
environ.Env.read_env(env.str('ENV_PATH', root('.env')))


# set some paths

BASE_DIR = root()
SITE_ROOT = root()

BASE_URL = os.getenv('BASE_URL')
DEBUG = env.bool('DEBUG', default=True)


ADMINS = [ ] # TODO: allow import from environment
MANAGERS = ADMINS


ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'allauth',  # django-allauth
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.twitter',
    'bootstrap4', # django-bootstrap4
    'captcha', # https://github.com/praekelt/django-recaptcha
    'constance', # https://github.com/jazzband/django-constance
    'constance.backends.database', # https://github.com/jazzband/django-constance

    'beeme.core',
    'beeme.frontend',
    'countdownhype',
    'controlroom'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'beeme.middleware.RemoteAddrMiddleware',
]

if not DEBUG:
    MIDDLEWARE.extend([
        'rollbar.contrib.django.middleware.RollbarNotifierMiddleware',
    ])

ROOT_URLCONF = 'beeme.urls'
SESSION_COOKIE_AGE = 60 * 60 * 24
SITE_ID = 1
WSGI_APPLICATION = 'beeme.wsgi.application'


# Authentication
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth

AUTH_USER_MODEL = 'core.User'
LOGIN_REDIRECT_URL = 'frontend:story'
LOGOUT_REDIRECT_URL = 'frontend:room'
LOGIN_URL = 'login'


# Caching

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': env.str('CACHE_DIR', default=root('tmp/cache')),
    }
}


# Constance

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

CONSTANCE_CONFIG = collections.OrderedDict([
    ('COMMAND_EXPIRATION',
        (60, 'Time after which a command expires (minutes)', int)
    ),
    ('COMMAND_FLAGS_TO_BAN',
        (3, 'Number of user commands to flag before they are banned', int)
    ),
    ('COMMAND_VOTE_EXPIRATION',
        (15, 'Time after which a vote expires (minutes)', int)
    ),

    ('DIY_INSTRUCTIONS',
        ('', 'DIY Instructions', str)
    ),
    ('STORY_INTRO',
        ('', 'Story Intro', str)
    ),

    ('TEAM1_MEDIA',
        ('', 'Team #1 Media', str)
    ),
    ('TEAM1_STORY',
        ('', 'Team #1 Story', str)
    ),
    ('TEAM2_MEDIA',
        ('', 'Team #2 Media', str)
    ),
    ('TEAM2_STORY',
        ('', 'Team #2 Story', str)
    ),
])


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {'default': env.db('DATABASE_URL')}
DATABASES['default']['OPTIONS'] = {'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"}


# Email

EMAIL_HOST = env.str('EMAIL_HOST')
EMAIL_HOST_USER = env.str('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env.str('EMAIL_HOST_PASSWORD')
EMAIL_PORT = env.int('EMAIL_PORT')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
DEFAULT_FROM_EMAIL = env.str('DEFAULT_FROM_EMAIL', default='noreply@beeme.online')
SERVER_EMAIL = env.str('SERVER_EMAIL', default='app@beeme.online')


# File Uploads

CLOUDFILES = {
    'gallery': {
        'acount': env.int('CLOUDFILES_GALLERY_ACCOUNTID'),
        'name': env.str('CLOUDFILES_GALLERY_NAME'),
        'username': env.str('CLOUDFILES_GALLERY_USERNAME'),
        'api_key': env.str('CLOUDFILES_GALLERY_API_KEY'),
        'region': env.str('CLOUDFILES_GALLERY_REGION'),
    }
}

FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_TEMP_DIR = root('tmp/')
MEDIA_ROOT = root('uploads/')
MEDIA_URL = env.str('MEDIA_URL', default='/storage/')


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE =  env.str('LANGUAGE_CODE', default='en-us')
TIME_ZONE = env.str('TIME_ZONE', default='America/New_York')
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator' },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator' },
]


# Pusher

PUSHER_APP_ID = env.str('PUSHER_APP_ID')
PUSHER_KEY = env.str('PUSHER_KEY')
PUSHER_SECRET = env.str('PUSHER_SECRET')
PUSHER_CLUSTER = env.str('PUSHER_CLUSTER')
PUSHER_SSL = env.bool('PUSHER_SSL', default=True)


# reCaptcha

RECAPTCHA_PUBLIC_KEY = env.str('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = env.str('RECAPTCHA_PRIVATE_KEY')


# Rollbar

ROLLBAR = {
    'access_token': env.str('ROLLBAR_ACCESS_TOKEN'),
    'environment': env.str('ROLLBAR_ENVIRONMENT'),
    'root': BASE_DIR,
}
import rollbar ; rollbar.init(**ROLLBAR)


# Security

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
SECRET_KEY = env.str('SECRET_KEY')
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SOCIALACCOUNT_AUTO_SIGNUP = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/


STATICFILES_DIRS = (
    root('static/'),
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
STATIC_ROOT = env.str('STATIC_ROOT', default='')
STATIC_URL = env.str('STATIC_URL', default='/static/')


# Templating

if DEBUG:
    TEMPLATES_OPTIONS_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )
else:
    TEMPLATES_OPTIONS_LOADERS = (
        ('django.template.loaders.cached.Loader', (
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        )),
    )

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            root.path('templates/')
        ],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
    
                'beeme.frontend.context_processors.debug',
            ],
            'loaders': TEMPLATES_OPTIONS_LOADERS,
        },
    },
]


# Twitch

TWITCH_CLIENT_ID = env.str('TWITCH_CLIENT_ID')
TWITCH_CLIENT_SECRET = env.str('TWITCH_CLIENT_SECRET')
