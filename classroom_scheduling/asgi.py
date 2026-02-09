"""
ASGI config for classroom_scheduling project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

# import os

# from django.core.asgi import get_asgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'classroom_scheduling.settings')

# application = get_asgi_application()


# asgi.py
import os
import django
from channels.routing import get_default_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'classroom_scheduling.settings')
django.setup()
application = get_default_application()

