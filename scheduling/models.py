from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractUser):
    is_superuser = models.BooleanField(default=False)
    rfid_uid = models.CharField(max_length=50, blank=True, null=True, unique=True, verbose_name='RFID UID')
    objects = CustomUserManager()

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=50, default='')
    last_name = models.CharField(max_length=50, default='')
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(unique=True)
    default_password = models.CharField(max_length=50, blank=True, null=True)  # To store the default password

    def __str__(self):
        return f"{self.last_name}, {self.first_name} {self.middle_name or ''}"
        
    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

class Classroom(models.Model):
    room_number = models.CharField(max_length=20, unique=True)
    capacity = models.IntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.room_number

class Subject(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='subjects')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

class Student(models.Model):
    YEAR_CHOICES = [
        (1, '1st Year'),
        (2, '2nd Year'),
        (3, '3rd Year'),
        (4, '4th Year'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=50, default='')
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, default='')
    email = models.EmailField(unique=True)
    course = models.CharField(max_length=100, default='')
    year_level = models.IntegerField(choices=YEAR_CHOICES, default=1)
    subjects = models.ManyToManyField(Subject, through='StudentSubject')
    is_active = models.BooleanField(default=True)
    is_face_registered = models.BooleanField(default=False)
    default_password = models.CharField(max_length=50, blank=True, null=True)  # To store the default password

    def __str__(self):
        return f"{self.student_id} - {self.full_name}"
        
    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"

class StudentSubject(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date_enrolled = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'subject')

class Schedule(models.Model):
    DAYS_OF_WEEK = [
        ('M', 'Monday'),
        ('T', 'Tuesday'),
        ('W', 'Wednesday'),
        ('Th', 'Thursday'),
        ('F', 'Friday'),
        ('S', 'Saturday'),
        ('Su', 'Sunday'),
    ]

    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    day = models.CharField(max_length=20)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ('classroom', 'day', 'start_time', 'end_time')

    def __str__(self):
        return f"{self.subject} - {self.classroom} ({self.get_days_display()} {self.start_time}-{self.end_time})"
    
    def get_days_display(self):
        """
        Returns a formatted string of selected days
        """
        if not self.day:
            return ""
        
        day_codes = self.day.split(',')
        day_names = []
        day_dict = dict(self.DAYS_OF_WEEK)
        
        for code in day_codes:
            if code in day_dict:
                day_names.append(day_dict[code])
        
        return ", ".join(day_names)


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]
    
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    remarks = models.TextField(blank=True, null=True)
    recorded_by = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='recorded_attendances')
    timestamp = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    class Meta:
        unique_together = ('schedule', 'student', 'date')
        ordering = ['-date', 'schedule']
    
    def __str__(self):
        return f"{self.student} - {self.schedule.subject} - {self.date} - {self.get_status_display()}"
