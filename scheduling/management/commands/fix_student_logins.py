from django.core.management.base import BaseCommand
from scheduling.scripts import fix_student_logins

class Command(BaseCommand):
    help = 'Fix student logins by ensuring all usernames match their student IDs'

    def handle(self, *args, **options):
        count = fix_student_logins()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully fixed {count} student accounts')
        ) 