from django.contrib.auth import get_user_model
from django.core.management import execute_from_command_line
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'classroom_scheduling.settings')
django.setup()

User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@gmail.com', '123')
    print("Superuser created successfully!")
else:
    print("Superuser already exists!")
