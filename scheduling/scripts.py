"""
Utility scripts for the scheduling app.
"""
import logging
from .models import Student, User

logger = logging.getLogger(__name__)

def fix_student_logins():
    """
    Fix student logins by ensuring all student usernames match their student_id.
    This helps ensure students can log in with their ID numbers.
    """
    # Get all students
    students = Student.objects.all()
    count = 0
    
    for student in students:
        # If username doesn't match student_id, update it
        if student.user.username != student.student_id:
            logger.info(f"Fixing student: {student.full_name}. Old username: {student.user.username}, New username: {student.student_id}")
            
            # See if another user already has this username
            existing_user = User.objects.filter(username=student.student_id).first()
            
            if existing_user and existing_user != student.user:
                logger.warning(f"Cannot update username for {student.full_name} - username {student.student_id} already exists")
                continue
                
            # Update the username
            student.user.username = student.student_id
            student.user.save()
            count += 1
    
    return count

if __name__ == "__main__":
    # This allows the script to be run directly
    # python manage.py shell < scheduling/scripts.py
    print(f"Fixed {fix_student_logins()} student accounts.") 