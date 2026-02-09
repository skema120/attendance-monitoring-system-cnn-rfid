from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from scheduling.models import User
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Debug superuser login attempt'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username to test')
        parser.add_argument('password', type=str, help='Password to test')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        
        # Enable console logging for this test
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
        logger.setLevel(logging.DEBUG)
        
        # See if the user exists
        try:
            user = User.objects.get(username=username)
            self.stdout.write(f"Found user: {username}")
            self.stdout.write(f"Is superuser: {user.is_superuser}")
            self.stdout.write(f"Is active: {user.is_active}")
            self.stdout.write(f"Is staff: {user.is_staff}")
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No user found with username: {username}"))
            return
        
        # Try to authenticate
        self.stdout.write(f"Attempting to authenticate with username: {username}")
        user = authenticate(username=username, password=password)
        
        if user is not None:
            self.stdout.write(self.style.SUCCESS(f"Authentication successful for {username}"))
            self.stdout.write(f"Authenticated user is_superuser: {user.is_superuser}")
            self.stdout.write(f"Authenticated user is_active: {user.is_active}")
            self.stdout.write(f"Authenticated user is_staff: {user.is_staff}")
        else:
            self.stdout.write(self.style.ERROR("Authentication failed")) 