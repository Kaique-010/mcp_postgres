
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'casaa',
        'USER': 'postgres',
        'PASSWORD': '@spartacus201@',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'options': '-c search_path=public'
        }
    },
   
}


INSTALLED_APPS = [
    'django.contrib.contenttypes',
]

SECRET_KEY = 'uma-chave-secreta-para-o-django'