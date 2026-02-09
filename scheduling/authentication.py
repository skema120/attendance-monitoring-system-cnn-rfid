from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from scheduling.models import Student
import logging

# Set up logger
logger = logging.getLogger(__name__)

User = get_user_model()

class StudentIDAuthBackend(ModelBackend):
    """
    Custom authentication backend that allows students to log in with their student ID
    instead of username, while maintaining regular authentication for other users.
    """
    
    def authenticate(self, request, username=None, password=None, student_id=None, **kwargs):
        if not password or not username:
            return None
            
        # Use student_id parameter if provided explicitly
        if student_id:
            username = student_id
            
        logger.info(f"Authentication attempt for: {username}")
        
        try:
            # First try to authenticate using the parent ModelBackend
            # This will handle superusers and staff properly
            user = super().authenticate(request, username=username, password=password)
            if user is not None:
                logger.info(f"Authentication successful using ModelBackend for: {username}")
                return user
                
            # If regular authentication failed, try student-specific authentication
            try:
                student = Student.objects.get(student_id=username)
                logger.info(f"Found student with ID: {username}, attempting to authenticate")
                
                # Check the password
                if student.user.check_password(password):
                    logger.info(f"Authentication successful for student ID: {username}")
                    return student.user
                else:
                    logger.info(f"Password incorrect for student ID: {username}")
            except Student.DoesNotExist:
                logger.info(f"No student found with ID: {username}")
                
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
        return None 