from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from scheduling.models import Student
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Debug student login using student ID'

    def add_arguments(self, parser):
        parser.add_argument('student_id', type=str, help='Student ID to test')
        parser.add_argument('password', type=str, help='Password to test')

    def handle(self, *args, **options):
        student_id = options['student_id']
        password = options['password']
        
        # Enable verbose console logging for this test
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
        logger.setLevel(logging.DEBUG)
        
        self.stdout.write(self.style.SUCCESS(f"Starting debug for student login with ID: {student_id}"))
        
        # See if the student exists
        try:
            student = Student.objects.get(student_id=student_id)
            self.stdout.write(self.style.SUCCESS(f"Found student: {student.full_name}"))
            self.stdout.write(f"User ID: {student.user.id}")
            self.stdout.write(f"Username: {student.user.username}")
            self.stdout.write(f"User is_active: {student.user.is_active}")
            self.stdout.write(f"Student ID: {student.student_id}")
            self.stdout.write(f"Default password (if stored): {student.default_password}")
        except Student.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No student found with ID: {student_id}"))
            return
        
        # Try to authenticate with username field
        self.stdout.write(self.style.WARNING(f"Attempting authentication method 1 (username field)"))
        user1 = authenticate(username=student_id, password=password)
        
        if user1 is not None:
            self.stdout.write(self.style.SUCCESS(f"Method 1 successful for {user1.username}"))
        else:
            self.stdout.write(self.style.ERROR("Method 1 failed"))
            
        # Try to authenticate with student_id field
        self.stdout.write(self.style.WARNING(f"Attempting authentication method 2 (student_id field)"))
        user2 = authenticate(student_id=student_id, password=password)
        
        if user2 is not None:
            self.stdout.write(self.style.SUCCESS(f"Method 2 successful for {user2.username}"))
        else:
            self.stdout.write(self.style.ERROR("Method 2 failed"))
            
        # Try to authenticate with regular username
        self.stdout.write(self.style.WARNING(f"Attempting authentication method 3 (regular username)"))
        user3 = authenticate(username=student.user.username, password=password)
        
        if user3 is not None:
            self.stdout.write(self.style.SUCCESS(f"Method 3 successful for {user3.username}"))
        else:
            self.stdout.write(self.style.ERROR("Method 3 failed")) 