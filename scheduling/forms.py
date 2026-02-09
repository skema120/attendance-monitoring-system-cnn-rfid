from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User, Teacher, Student, Classroom, Subject, Schedule, Attendance
from django.db.models import Q

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['room_number', 'capacity', 'is_active']
        widgets = {
            'room_number': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

class TeacherForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ['last_name', 'first_name', 'middle_name', 'address', 'email']
        widgets = {
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'})
        }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')

        # Check if email is already in use (excluding the current instance when editing)
        if email:
            user_query = User.objects.filter(email=email)
            if self.instance and self.instance.pk and hasattr(self.instance, 'user'):
                user_query = user_query.exclude(pk=self.instance.user.pk)
            
            if user_query.exists():
                raise forms.ValidationError("This email is already in use")

        return cleaned_data

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['student_id', 'first_name', 'middle_name', 'last_name', 'email', 'course', 'year_level', 'is_active']
        widgets = {
            'student_id': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'middle_name': forms.TextInput(attrs={'class': 'form-control', 'required': False}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'course': forms.TextInput(attrs={'class': 'form-control'}),
            'year_level': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        student_id = cleaned_data.get('student_id')

        # Check if email is already in use
        if email:
            user_query = User.objects.filter(email=email)
            if self.instance and self.instance.pk and hasattr(self.instance, 'user'):
                user_query = user_query.exclude(pk=self.instance.user.pk)
            
            if user_query.exists():
                raise forms.ValidationError("This email is already in use")

        # Check if student_id is already in use
        if student_id:
            student_query = Student.objects.filter(student_id=student_id)
            if self.instance and self.instance.pk:
                student_query = student_query.exclude(pk=self.instance.pk)
            
            if student_query.exists():
                raise forms.ValidationError("This student ID is already in use")

        return cleaned_data

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['code', 'name', 'teacher']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'teacher': forms.Select(attrs={'class': 'form-control'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = Teacher.objects.all()

class ScheduleForm(forms.ModelForm):
    # Add a MultipleChoiceField for day selection
    days = forms.MultipleChoiceField(
        choices=Schedule.DAYS_OF_WEEK,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=True
    )
    
    class Meta:
        model = Schedule
        fields = ['subject', 'classroom', 'start_time', 'end_time']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'classroom': forms.Select(attrs={'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'})
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter subjects to only show active ones
        if user and not user.is_superuser and hasattr(user, 'teacher'):
            self.fields['subject'].queryset = Subject.objects.filter(
                teacher=user.teacher,
                is_active=True
            )
        else:
            self.fields['subject'].queryset = Subject.objects.filter(is_active=True)
            
        self.fields['classroom'].queryset = Classroom.objects.filter(is_active=True)
        
        # If we're editing an existing schedule, initialize the days field
        if self.instance and self.instance.pk and self.instance.day:
            self.initial['days'] = self.instance.day.split(',')

    def clean(self):
        cleaned_data = super().clean()
        subject = cleaned_data.get('subject')
        classroom = cleaned_data.get('classroom')
        days = cleaned_data.get('days')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Check if end time is after start time
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError("End time must be after start time.")
            
        # Skip conflict checks if any required field is missing
        if not (subject and classroom and days and start_time and end_time):
            return cleaned_data
            
        # Check for conflicts
        conflicts = self.check_conflicts(days, start_time, end_time, classroom, subject)
        if conflicts:
            raise forms.ValidationError(conflicts)
            
        return cleaned_data
        
    def check_conflicts(self, days, start_time, end_time, classroom, subject):
        """Check for various types of scheduling conflicts"""
        conflicts = []
        
        if not days:
            return conflicts
            
        # Exclude current schedule when editing
        exclude_id = self.instance.pk if self.instance and self.instance.pk else None
            
        for day in days:
            # 1. Check classroom availability for the same timeslot
            classroom_conflicts = Schedule.objects.filter(
                classroom=classroom
            ).exclude(pk=exclude_id)
            
            for schedule in classroom_conflicts:
                schedule_days = schedule.day.split(',')
                if day in schedule_days and self.times_overlap(start_time, end_time, schedule.start_time, schedule.end_time):
                    conflicts.append(f"Room {classroom.room_number} is already scheduled for {schedule.subject.name} on {dict(Schedule.DAYS_OF_WEEK)[day]} from {schedule.start_time.strftime('%H:%M')} to {schedule.end_time.strftime('%H:%M')}.")
            
            # 2. Check if the teacher is already teaching at the same time
            if subject and subject.teacher:
                teacher_conflicts = Schedule.objects.filter(
                    subject__teacher=subject.teacher
                ).exclude(pk=exclude_id).exclude(subject=subject)
                
                for schedule in teacher_conflicts:
                    schedule_days = schedule.day.split(',')
                    if day in schedule_days and self.times_overlap(start_time, end_time, schedule.start_time, schedule.end_time):
                        conflicts.append(f"Teacher {subject.teacher.full_name} is already teaching {schedule.subject.name} on {dict(Schedule.DAYS_OF_WEEK)[day]} from {schedule.start_time.strftime('%H:%M')} to {schedule.end_time.strftime('%H:%M')}.")
        
        return conflicts
        
    def times_overlap(self, start1, end1, start2, end2):
        """Check if two time periods overlap"""
        return (start1 < end2 and start2 < end1)
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Join selected days with commas and save to the day field
        if 'days' in self.cleaned_data:
            instance.day = ','.join(self.cleaned_data['days'])
        if commit:
            instance.save()
        return instance

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Student ID",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username or student ID'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'})
    )

class UserEditForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    is_superuser = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    is_staff = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    rfid_uid = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}), label='RFID UID')

    class Meta:
        model = User
        fields = ['username', 'email', 'rfid_uid', 'is_superuser', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.initial['is_superuser'] = self.instance.is_superuser
            self.initial['is_staff'] = self.instance.is_staff

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'status', 'remarks']
        widgets = {
            'student': forms.HiddenInput(),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

class RFIDAssignmentForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Select User'
    )
    rfid_uid = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Scan RFID card...'}),
        label='RFID UID'
    )

    def save(self):
        user = self.cleaned_data['user']
        rfid_uid = self.cleaned_data['rfid_uid']
        user.rfid_uid = rfid_uid
        user.save()
        return user
        
class RFIDAttendanceForm(forms.Form):
    rfid_uid = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Scan RFID card...', 'autofocus': 'autofocus'}),
        label='RFID UID'
    )
    
    def __init__(self, *args, **kwargs):
        self.schedule = kwargs.pop('schedule', None)
        self.date = kwargs.pop('date', None)
        self.teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)

class AttendanceFormSet(forms.BaseModelFormSet):
    def __init__(self, *args, schedule=None, date=None, teacher=None, **kwargs):
        self.schedule = schedule
        self.date = date
        self.teacher = teacher
        super().__init__(*args, **kwargs)

    def save_all(self):
        instances = []
        for form in self.forms:
            if form.is_valid() and form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                instance = form.save(commit=False)
                instance.schedule = self.schedule
                instance.date = self.date
                instance.recorded_by = self.teacher
                instance.save()
                instances.append(instance)
        return instances
