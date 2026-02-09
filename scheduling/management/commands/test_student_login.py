from django.core.management.base import BaseCommand
from django.contrib.auth import authenticate
from scheduling.models import Student
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test student login using student ID'

    def add_arguments(self, parser):
        parser.add_argument('student_id', type=str, help='Student ID to test')
        parser.add_argument('password', type=str, help='Password to test')

    def handle(self, *args, **options):
        student_id = options['student_id']
        password = options['password']
        
        # Enable console logging for this test
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
        logger.setLevel(logging.DEBUG)
        
        # See if the student exists
        try:
            student = Student.objects.get(student_id=student_id)
            self.stdout.write(f"Found student: {student.full_name} (User ID: {student.user.id}, Username: {student.user.username})")
        except Student.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No student found with ID: {student_id}"))
            return
        
        # Try to authenticate
        self.stdout.write(f"Attempting to authenticate with student ID: {student_id}")
        user = authenticate(student_id=student_id, password=password)
        
        if user is not None:
            self.stdout.write(self.style.SUCCESS(f"Authentication successful for {user.username}"))
        else:
            self.stdout.write(self.style.ERROR("Authentication failed")) 