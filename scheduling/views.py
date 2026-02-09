from django.shortcuts import render, redirect, get_object_or_404
from .forms import (UserRegistrationForm, TeacherForm, StudentForm, ClassroomForm, SubjectForm, ScheduleForm, UserEditForm, AttendanceForm, AttendanceFormSet, RFIDAssignmentForm, RFIDAttendanceForm, CustomAuthenticationForm)
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView, View, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.decorators.http import require_http_methods
from .models import User, Teacher, Student, Classroom, Subject, Schedule, StudentSubject, Attendance
from django.db.models import Q

from django.utils import timezone
from datetime import datetime, timedelta
import pytz
# Get the current time
current_date = datetime.now()

from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
import calendar
import random
import string
from django.forms import modelformset_factory
import os

from django.http import StreamingHttpResponse
import cv2


import sys
import numpy as np

from. import facenet as facenet
from. import detect_face as detect_face
import time
import pickle
from PIL import Image
import tensorflow.compat.v1 as tf

from.classifier import training
from.preprocess import preprocesses
import threading

from django.contrib.auth.views import LoginView

from django.core.mail import send_mail
from django.conf import settings


def is_superuser(user):
    return user.is_superuser

class SuperUserRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser

class StudentAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return hasattr(self.request.user, 'student')

class TeacherAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return hasattr(self.request.user, 'teacher') or self.request.user.is_superuser

class AdminAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = CustomAuthenticationForm  # your custom form

    def dispatch(self, request, *args, **kwargs):
        # If user is already logged in, redirect them accordingly
        if request.user.is_authenticated:
            if request.user.is_superuser or request.user.is_staff:
                return redirect('admin_dashboard')
            elif hasattr(request.user, 'student'):
                return redirect('student_dashboard')
            elif hasattr(request.user, 'teacher'):
                return redirect('teacher_dashboard')
            else:
                # fallback redirect
                return redirect('home')
        # else proceed normally to show login form
        return super().dispatch(request, *args, **kwargs)


@login_required
def home(request):
    # Redirect users based on their role
    if request.user.is_superuser or request.user.is_staff:
        return redirect('admin_dashboard')
    elif hasattr(request.user, 'student'):
        return redirect('student_dashboard')
    elif hasattr(request.user, 'teacher'):
        return redirect('teacher_dashboard')
    
    return redirect('login')

@login_required
def profile(request):
    # For students, only allow them to view their own profile
    if hasattr(request.user, 'student'):
        student = request.user.student
        return redirect('student_detail', pk=student.id)
    # For teachers, only allow them to view their own profile
    elif hasattr(request.user, 'teacher'):
        teacher = request.user.teacher
        return redirect('teacher_detail', pk=teacher.id)
    # For admins, show the user list
    else:
        return redirect('user_list')

class ClassroomListView(LoginRequiredMixin, TeacherAccessMixin, ListView):
    model = Classroom
    template_name = 'scheduling/classroom_list.html'
    context_object_name = 'classrooms'

    def get_queryset(self):
        queryset = Classroom.objects.all()
        search_query = self.request.GET.get('search')
        status_filter = self.request.GET.get('status')

        if search_query:
            queryset = queryset.filter(
                Q(room_number__icontains=search_query) |
                Q(building__icontains=search_query) |
                Q(capacity__icontains=search_query)
            )

        if status_filter:
            if status_filter == 'available':
                queryset = queryset.filter(is_active=True)
            elif status_filter == 'unavailable':
                queryset = queryset.filter(is_active=False)

        return queryset.order_by('room_number')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context

class ClassroomCreateView(LoginRequiredMixin, SuperUserRequiredMixin, CreateView):
    model = Classroom
    form_class = ClassroomForm
    template_name = 'scheduling/classroom_form.html'
    success_url = reverse_lazy('classroom_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Classroom created successfully!')
        return response

class ClassroomUpdateView(LoginRequiredMixin, SuperUserRequiredMixin, UpdateView):
    model = Classroom
    form_class = ClassroomForm
    template_name = 'scheduling/classroom_form.html'
    success_url = reverse_lazy('classroom_list')

    def form_valid(self, form):
        messages.success(self.request, 'Classroom updated successfully!')
        return super().form_valid(form)

class ClassroomDeleteView(LoginRequiredMixin, SuperUserRequiredMixin, DeleteView):
    model = Classroom
    template_name = 'scheduling/classroom_confirm_delete.html'
    success_url = reverse_lazy('classroom_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Classroom deleted successfully!')
        return super().delete(request, *args, **kwargs)

class ClassroomDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Classroom
    template_name = 'scheduling/classroom_detail.html'
    context_object_name = 'classroom'
    
    def test_func(self):
        classroom = self.get_object()
        
        # For students, only allow viewing classrooms associated with their enrolled subjects
        if hasattr(self.request.user, 'student'):
            student = self.request.user.student
            return Schedule.objects.filter(
                classroom=classroom,
                subject__studentsubject__student=student
            ).exists()
        # For teachers, only allow viewing classrooms they teach in
        elif hasattr(self.request.user, 'teacher') and not self.request.user.is_superuser:
            teacher = self.request.user.teacher
            return Schedule.objects.filter(
                classroom=classroom,
                subject__teacher=teacher
            ).exists()
        # For superusers, allow access to all classrooms
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        classroom = self.get_object()
        
        # For students, only show schedules for their enrolled subjects in this classroom
        if hasattr(self.request.user, 'student'):
            student = self.request.user.student
            context['schedules'] = Schedule.objects.filter(
                classroom=classroom,
                subject__studentsubject__student=student
            ).order_by('day', 'start_time')
        # For teachers, only show schedules for their subjects in this classroom
        elif hasattr(self.request.user, 'teacher') and not self.request.user.is_superuser:
            teacher = self.request.user.teacher
            context['schedules'] = Schedule.objects.filter(
                classroom=classroom,
                subject__teacher=teacher
            ).order_by('day', 'start_time')
        # For superusers, show all schedules for this classroom
        else:
            context['schedules'] = Schedule.objects.filter(classroom=classroom).order_by('day', 'start_time')
        
        return context

class ClassroomToggleStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def post(self, request, pk):
        classroom = get_object_or_404(Classroom, pk=pk)
        classroom.is_active = not classroom.is_active
        classroom.save()
        messages.success(request, f'Classroom {classroom.room_number} has been marked as {"available" if classroom.is_active else "unavailable"}.')
        return redirect('classroom_list')

class SubjectListView(LoginRequiredMixin, TeacherAccessMixin, ListView):
    model = Subject
    template_name = 'scheduling/subject_list.html'
    context_object_name = 'subjects'

    def get_queryset(self):
        query = self.request.GET.get('q')
        # Base queryset with teacher information
        base_queryset = Subject.objects.select_related('teacher')
        
        # Apply search filter if query exists
        if query:
            filtered = base_queryset.filter(
                Q(code__icontains=query) |
                Q(name__icontains=query) |
                Q(teacher__last_name__icontains=query) |
                Q(teacher__first_name__icontains=query)
            )
        else:
            filtered = base_queryset
            
        # For superusers, show all subjects
        if self.request.user.is_superuser:
            return filtered.order_by('code')
        # For teachers, show only their subjects
        elif hasattr(self.request.user, 'teacher'):
            return filtered.filter(teacher=self.request.user.teacher).order_by('code')
        # For students, show subjects they're enrolled in
        else:
            return filtered.filter(studentsubject__student__user=self.request.user).order_by('code')

class SubjectCreateView(LoginRequiredMixin, SuperUserRequiredMixin, CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'scheduling/subject_form.html'
    success_url = reverse_lazy('subject_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Subject created successfully!')
        return response

class SubjectUpdateView(LoginRequiredMixin, SuperUserRequiredMixin, UpdateView):
    model = Subject
    form_class = SubjectForm
    template_name = 'scheduling/subject_form.html'
    success_url = reverse_lazy('subject_list')

    def form_valid(self, form):
        messages.success(self.request, 'Subject updated successfully!')
        return super().form_valid(form)

class SubjectDeleteView(LoginRequiredMixin, SuperUserRequiredMixin, DeleteView):
    model = Subject
    template_name = 'scheduling/subject_confirm_delete.html'
    success_url = reverse_lazy('subject_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Subject deleted successfully!')
        return super().delete(request, *args, **kwargs)

class SubjectDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Subject
    template_name = 'scheduling/subject_detail.html'
    context_object_name = 'subject'
    
    def test_func(self):
        subject = self.get_object()
        
        # For students, only allow viewing subjects they're enrolled in
        if hasattr(self.request.user, 'student'):
            student = self.request.user.student
            return StudentSubject.objects.filter(
                student=student,
                subject=subject
            ).exists()
        # For teachers, only allow viewing their own subjects
        elif hasattr(self.request.user, 'teacher') and not self.request.user.is_superuser:
            teacher = self.request.user.teacher
            return subject.teacher == teacher
        # For superusers, allow access to all subjects
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subject = self.get_object()
        context['schedules'] = Schedule.objects.filter(subject=subject).order_by('day', 'start_time')
        
        # For students, show only enrolled students (themselves)
        if hasattr(self.request.user, 'student'):
            context['enrolled_students'] = Student.objects.filter(
                id=self.request.user.student.id
            )
        # For others, show all enrolled students
        else:
            # Use a more direct query to get students enrolled in this subject
            context['enrolled_students'] = Student.objects.filter(
                subjects=subject
            ).order_by('last_name', 'first_name')
        
        # Get students not enrolled in this subject - only for admins
        if self.request.user.is_superuser:
            context['available_students'] = Student.objects.exclude(
                studentsubject__subject=subject
            ).order_by('last_name', 'first_name')
            
        return context

class ScheduleListView(LoginRequiredMixin, ListView):
    model = Schedule
    template_name = 'scheduling/schedule_list.html'
    context_object_name = 'schedules'

    def get_queryset(self):
        query = self.request.GET.get('q')
        queryset = Schedule.objects.select_related('subject', 'subject__teacher', 'classroom')
        
        # Apply search filter if query exists
        if query:
            filtered = queryset.filter(
                Q(subject__name__icontains=query) |
                Q(subject__code__icontains=query) |
                Q(subject__teacher__first_name__icontains=query) |
                Q(subject__teacher__last_name__icontains=query) |
                Q(classroom__room_number__icontains=query)
            )
        else:
            filtered = queryset
            
        # Filter by user role
        if self.request.user.is_superuser:
            return filtered.order_by('day', 'start_time')
        elif hasattr(self.request.user, 'teacher'):
            return filtered.filter(subject__teacher=self.request.user.teacher).order_by('day', 'start_time')
        elif hasattr(self.request.user, 'student'):
            return filtered.filter(subject__studentsubject__student=self.request.user.student).order_by('day', 'start_time')
        return Schedule.objects.none()

    def dispatch(self, request, *args, **kwargs):
        # Check if user is a student and trying to access the main schedule list
        if hasattr(request.user, 'student') and not request.path.startswith('/student/schedule/'):
            return redirect('student_schedule')
        return super().dispatch(request, *args, **kwargs)

@user_passes_test(is_superuser)
def teacher_list(request):
    teachers = Teacher.objects.all()
    return render(request, 'scheduling/teacher_list.html', {'teachers': teachers})

@user_passes_test(is_superuser)
def student_list(request):
    students = Student.objects.all()
    return render(request, 'scheduling/student_list.html', {'students': students})

def check_schedule_conflict(schedule, exclude_id=None):
    conflicts = Schedule.objects.filter(
        classroom=schedule.classroom,
        day=schedule.day,
    ).exclude(id=exclude_id)
    
    for existing in conflicts:
        if (schedule.start_time <= existing.end_time and 
            schedule.end_time >= existing.start_time):
            return True
    return False

# Teacher Views
class TeacherListView(LoginRequiredMixin, TeacherAccessMixin, ListView):
    model = Teacher
    template_name = 'scheduling/teacher_list.html'
    context_object_name = 'teachers'
    ordering = ['last_name', 'first_name']

    def get_queryset(self):
        query = self.request.GET.get('q')
        base_queryset = Teacher.objects.all()
        
        # Apply search filter if query exists
        if query:
            filtered = base_queryset.filter(
                Q(last_name__icontains=query) |
                Q(first_name__icontains=query) |
                Q(email__icontains=query)
            )
        else:
            filtered = base_queryset
            
        # For students, only show teachers of enrolled subjects
        if hasattr(self.request.user, 'student'):
            student = self.request.user.student
            return filtered.filter(
                subject__studentsubject__student=student
            ).distinct().order_by('last_name', 'first_name')
        # For superusers, show all teachers
        elif self.request.user.is_superuser:
            return filtered.order_by('last_name', 'first_name')
        # For teachers, don't show any teachers (they shouldn't access this view)
        else:
            return Teacher.objects.none()

def generate_random_string(length, include_symbols=False):
    """Generate a random string of specified length."""
    characters = string.ascii_letters + string.digits
    if include_symbols:
        characters += '!@#$%&'
    return ''.join(random.choice(characters) for _ in range(length))

def generate_username(last_name):
    """Generate a username based on the last name and random characters."""
    # Take up to 4 characters from the last name
    base = last_name.lower()[:10]
    # Add 4 random characters
    random_part = generate_random_string(4)
    username = f"{base}_{random_part}"
    
    # Make sure username is unique
    counter = 1
    original_username = username
    while User.objects.filter(username=username).exists():
        username = f"{original_username}{counter}"
        counter += 1
        
    return username

def generate_password():
    """Generate a random password with 8 characters including numbers and symbols."""
    return generate_random_string(8, include_symbols=True)

class TeacherCreateView(LoginRequiredMixin, SuperUserRequiredMixin, CreateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'scheduling/teacher_form.html'
    success_url = reverse_lazy('teacher_list')

    def form_valid(self, form):
        # Create a new user for the teacher instead of using the admin's user
        username = generate_username(form.cleaned_data['last_name'])
        password = generate_password()
        
        # Create a new user for this teacher
        user = User.objects.create_user(
            username=username,
            email=form.cleaned_data['email'],
            password=password
        )
        
        # Associate the new user with the teacher
        form.instance.user = user
        form.instance.default_password = password
        
        response = super().form_valid(form)
        messages.success(self.request, 'Teacher created successfully!')
        return response

class TeacherUpdateView(LoginRequiredMixin, SuperUserRequiredMixin, UpdateView):
    model = Teacher
    form_class = TeacherForm
    template_name = 'scheduling/teacher_form.html'
    success_url = reverse_lazy('teacher_list')

    def form_valid(self, form):
        teacher = form.save(commit=False)
        user = teacher.user
        
        # Update user information
        user.email = form.cleaned_data['email']
        user.save()
        
        teacher.save()
        messages.success(self.request, 'Teacher account updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Error updating teacher account. Please check the form.')
        return super().form_invalid(form)

class TeacherDeleteView(LoginRequiredMixin, SuperUserRequiredMixin, DeleteView):
    model = Teacher
    template_name = 'scheduling/teacher_confirm_delete.html'
    success_url = reverse_lazy('teacher_list')

    def delete(self, request, *args, **kwargs):
        teacher = self.get_object()
        user = teacher.user
        
        # Delete the teacher and associated user account
        response = super().delete(request, *args, **kwargs)
        user.delete()
        
        messages.success(request, 'Teacher account deleted successfully!')
        return response

class TeacherDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Teacher
    template_name = 'scheduling/teacher_detail.html'
    context_object_name = 'teacher'
    
    def test_func(self):
        # For students, only allow viewing details of teachers they're enrolled with
        if hasattr(self.request.user, 'student'):
            teacher = self.get_object()
            student = self.request.user.student
            return student.subjects.filter(teacher=teacher).exists()
        # For superusers, allow access
        elif self.request.user.is_superuser:
            return True
        # Block teachers from accessing this view
        else:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.get_object()
        
        # For students, only show subjects they're enrolled in with this teacher
        if hasattr(self.request.user, 'student'):
            student = self.request.user.student
            context['subjects'] = Subject.objects.filter(
                teacher=teacher,
                studentsubject__student=student
            )
            context['schedules'] = Schedule.objects.filter(
                subject__teacher=teacher,
                subject__studentsubject__student=student
            ).order_by('day', 'start_time')
        # For superusers, show all subjects and schedules
        else:
            context['subjects'] = Subject.objects.filter(teacher=teacher)
            context['schedules'] = Schedule.objects.filter(subject__teacher=teacher).order_by('day', 'start_time')
        
        return context

# Student Views
class StudentListView(LoginRequiredMixin, TeacherAccessMixin, ListView):
    model = Student
    template_name = 'scheduling/student_list.html'
    context_object_name = 'student_list'
    ordering = ['last_name', 'first_name']

    def get_queryset(self):
        # For superusers, show all students
        if self.request.user.is_superuser:
            return Student.objects.select_related('user').all().order_by('last_name', 'first_name')
        # For teachers, show only students enrolled in their subjects
        elif hasattr(self.request.user, 'teacher'):
            teacher = self.request.user.teacher
            return Student.objects.filter(
                studentsubject__subject__teacher=teacher
            ).distinct().select_related('user').order_by('last_name', 'first_name')
        # For students, don't show any data (handled in template)
        return Student.objects.none()


class FaceRegistrationView(LoginRequiredMixin, SuperUserRequiredMixin, CreateView):
    def get(self, request, pk):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save_path = os.path.join(base_dir, 'train_img', str(pk))
        os.makedirs(save_path, exist_ok=True)

        cap = cv2.VideoCapture(0)
        num_pictures = 100

        try:
            for i in range(num_pictures):
                ret, frame = cap.read()
                if ret:
                    filename = os.path.join(save_path, f"student_{pk}_{i}.jpg")
                    cv2.imwrite(filename, frame)
                    print(f"Image captured: {filename}")
                    cv2.imshow('Face Registration', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                else:
                    print("Error capturing frame")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            cap.release()
            cv2.destroyAllWindows()

        student = get_object_or_404(Student, pk=pk)
        student.is_face_registered = True
        student.save()

        return redirect('student_list')


class StudentCreateView(LoginRequiredMixin, SuperUserRequiredMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'scheduling/student_form.html'
    success_url = reverse_lazy('student_list')

    def form_valid(self, form):
        # Don't save the student yet, just get the instance
        student = form.save(commit=False)
        
        # Create a user account for the student
        username = generate_username(student.last_name)
        password = generate_password()
        
        # Create and save the user
        user = User.objects.create_user(
            username=username,
            email=student.email,
            password=password
        )
        user.save()
        
        # Associate the user with the student
        student.user = user
        student.default_password = password  # Save the default password for reference
        student.save()
        
        messages.success(self.request, f'Student created successfully! Username: {username}, Password: {password}')
        return redirect(self.success_url)

class StudentUpdateView(LoginRequiredMixin, SuperUserRequiredMixin, UpdateView):
    model = Student
    form_class = StudentForm
    template_name = 'scheduling/student_form.html'
    success_url = reverse_lazy('student_list')

    def get_initial(self):
        initial = super().get_initial()
        return initial

    def form_valid(self, form):
        student = form.save(commit=False)
        user = student.user
        
        # Update user information
        user.email = form.cleaned_data['email']
        user.save()
        
        student.save()
        messages.success(self.request, 'Student account updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Error updating student account. Please check the form.')
        return super().form_invalid(form)

class StudentDeleteView(LoginRequiredMixin, SuperUserRequiredMixin, DeleteView):
    model = Student
    template_name = 'scheduling/student_confirm_delete.html'
    success_url = reverse_lazy('student_list')

    def delete(self, request, *args, **kwargs):
        student = self.get_object()
        user = student.user
        
        # Delete the student and associated user account
        response = super().delete(request, *args, **kwargs)
        user.delete()
        
        messages.success(request, 'Student account deleted successfully!')
        return response

class StudentDetailView(LoginRequiredMixin, DetailView):
    model = Student
    template_name = 'scheduling/student_detail.html'
    context_object_name = 'student'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.get_object()
        
        # Get all enrolled subjects for the student
        context['enrolled_subjects'] = student.subjects.all().select_related('teacher')
        
        # Get all schedules for the student's subjects
        schedules = []
        for subject in context['enrolled_subjects']:
            subject_schedules = Schedule.objects.filter(subject=subject).select_related('classroom')
            for schedule in subject_schedules:
                schedules.append(schedule)
        
        # If teacher is viewing, filter to only show their subjects
        if hasattr(self.request.user, 'teacher') and not self.request.user.is_superuser:
            teacher = self.request.user.teacher
            context['enrolled_subjects'] = context['enrolled_subjects'].filter(teacher=teacher)
            schedules = [s for s in schedules if s.subject.teacher == teacher]
            
        # Sort schedules by day and time
        schedules.sort(key=lambda x: (x.day, x.start_time))
        context['schedules'] = schedules
        
        return context

# Schedule Views
class ScheduleCreateView(LoginRequiredMixin, SuperUserRequiredMixin, CreateView):
    model = Schedule
    form_class = ScheduleForm
    template_name = 'scheduling/schedule_form.html'
    success_url = reverse_lazy('schedule_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Schedule created successfully!')
        return response

class ScheduleUpdateView(LoginRequiredMixin, SuperUserRequiredMixin, UpdateView):
    model = Schedule
    form_class = ScheduleForm
    template_name = 'scheduling/schedule_form.html'
    success_url = reverse_lazy('schedule_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Schedule updated successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle form errors, specifically highlighting conflicts"""
        if form.non_field_errors():
            for error in form.non_field_errors():
                messages.error(self.request, error)
        return super().form_invalid(form)

class ScheduleDeleteView(LoginRequiredMixin, SuperUserRequiredMixin, DeleteView):
    model = Schedule
    template_name = 'scheduling/schedule_confirm_delete.html'
    success_url = reverse_lazy('schedule_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Schedule deleted successfully!')
        return super().delete(request, *args, **kwargs)

class ScheduleDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Schedule
    template_name = 'scheduling/schedule_detail.html'
    context_object_name = 'schedule'
    
    def test_func(self):
        schedule = self.get_object()
        
        # For students, only allow viewing schedules for subjects they're enrolled in
        if hasattr(self.request.user, 'student'):
            student = self.request.user.student
            return StudentSubject.objects.filter(
                student=student,
                subject=schedule.subject
            ).exists()
        # For teachers, only allow viewing schedules for their subjects
        elif hasattr(self.request.user, 'teacher') and not self.request.user.is_superuser:
            teacher = self.request.user.teacher
            return schedule.subject.teacher == teacher
        # For superusers, allow access to all schedules
        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        schedule = self.get_object()
        
        # Get enrolled students for this subject
        context['enrolled_students'] = Student.objects.filter(
            studentsubject__subject=schedule.subject
        ).order_by('last_name', 'first_name')
        
        return context

# Student-Subject Enrollment Views
class EnrollStudentView(LoginRequiredMixin, SuperUserRequiredMixin, TemplateView):
    template_name = 'scheduling/enrollment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all students
        context['students'] = Student.objects.all().order_by('last_name', 'first_name')
        
        # Get statistics
        context['total_students'] = Student.objects.count()
        context['total_subjects'] = Subject.objects.count()
        
        # Calculate average subjects per student
        total_enrollments = StudentSubject.objects.count()
        if context['total_students'] > 0:
            context['avg_subjects_per_student'] = total_enrollments / context['total_students']
        else:
            context['avg_subjects_per_student'] = 0
            
        return context

    def post(self, request, *args, **kwargs):
        student_id = request.POST.get('student_id')
        subject_id = request.POST.get('subject_id')
        
        if not subject_id:
            messages.error(request, 'Please select a subject to enroll in.')
            return redirect('enroll_student') + f'?student_id={student_id}'
            
        student = get_object_or_404(Student, pk=student_id)
        subject = get_object_or_404(Subject, pk=subject_id)
        
        # Check if student is already enrolled
        if StudentSubject.objects.filter(student=student, subject=subject).exists():
            messages.warning(request, f'{student.full_name} is already enrolled in this subject.')
            return redirect('enroll_student') + f'?student_id={student_id}'
        
        # Check for schedule conflicts
        conflicts = self.get_enrollment_conflicts(student, subject)
        if conflicts:
            for conflict in conflicts:
                messages.error(request, conflict)
            return redirect('enroll_student') + f'?student_id={student_id}'
            
        # Enroll the student
        StudentSubject.objects.create(student=student, subject=subject)
        messages.success(request, f'{student.full_name} has been enrolled in {subject.name}.')
        return redirect('student_subjects', pk=student_id)

    def get_enrollment_conflicts(self, student, new_subject):
        """Get detailed list of schedule conflicts"""
        conflicts = []
        
        # Get all schedules for the new subject
        new_schedules = Schedule.objects.filter(subject=new_subject)
        
        # Get all subjects the student is enrolled in
        enrolled_subjects = Subject.objects.filter(studentsubject__student=student)
        
        # Get all schedules for enrolled subjects
        enrolled_schedules = Schedule.objects.filter(subject__in=enrolled_subjects)

        # Check for time conflicts
        for new_schedule in new_schedules:
            new_days = new_schedule.day.split(',')
            
            for enrolled_schedule in enrolled_schedules:
                enrolled_days = enrolled_schedule.day.split(',')
                
                # Check if any days overlap between the schedules
                for day in new_days:
                    if day in enrolled_days and self.times_overlap(new_schedule, enrolled_schedule):
                        day_name = dict(Schedule.DAYS_OF_WEEK)[day]
                        conflicts.append(
                            f"Schedule conflict: {student.full_name} is already enrolled in {enrolled_schedule.subject.name} "
                            f"on {day_name} from {enrolled_schedule.start_time.strftime('%H:%M')} to {enrolled_schedule.end_time.strftime('%H:%M')}, "
                            f"which conflicts with {new_subject.name} scheduled on {day_name} from {new_schedule.start_time.strftime('%H:%M')} to {new_schedule.end_time.strftime('%H:%M')}."
                        )
                        
        return conflicts

    def times_overlap(self, schedule1, schedule2):
        return (schedule1.start_time <= schedule2.end_time and 
                schedule1.end_time >= schedule2.start_time)

class UnenrollStudentView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        # Allow access to superusers only
        return self.request.user.is_superuser

    def post(self, request, subject_id):
        subject = get_object_or_404(Subject, pk=subject_id)
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, pk=student_id)

        # Remove the enrollment
        StudentSubject.objects.filter(student=student, subject=subject).delete()
        messages.success(request, f'{student.full_name} has been successfully unenrolled from {subject.name}.')
        return redirect('subject_detail', pk=subject_id)

class StudentSubjectsView(LoginRequiredMixin, TemplateView):
    template_name = 'scheduling/student_subjects.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        context['student'] = student
        
        # Get enrolled subjects
        context['enrolled_subjects'] = student.subjects.all()
        
        # Get available subjects (only for superusers)
        if self.request.user.is_superuser:
            context['available_subjects'] = Subject.objects.exclude(
                    id__in=context['enrolled_subjects'].values_list('id', flat=True)
                )
        
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            messages.error(request, "You don't have permission to enroll students.")
            return redirect('student_subjects', pk=self.kwargs['pk'])
            
        student = get_object_or_404(Student, pk=self.kwargs['pk'])
        subject_id = request.POST.get('subject_id')
        
        if not subject_id:
            messages.error(request, "Please select a subject to enroll in.")
            return redirect('student_subjects', pk=self.kwargs['pk'])
            
        subject = get_object_or_404(Subject, pk=subject_id)
        
        # Check if student is already enrolled
        if subject in student.subjects.all():
            messages.error(request, f"{student.full_name} is already enrolled in {subject.name}.")
            return redirect('student_subjects', pk=self.kwargs['pk'])
            
        # Check for schedule conflicts
        conflicts = self.get_enrollment_conflicts(student, subject)
        if conflicts:
            for conflict in conflicts:
                messages.error(request, conflict)
            return redirect('student_subjects', pk=self.kwargs['pk'])
            
        # Enroll the student
        student.subjects.add(subject)
        messages.success(request, f"Successfully enrolled {student.full_name} in {subject.name}.")
        return redirect('student_subjects', pk=self.kwargs['pk'])

    def get_enrollment_conflicts(self, student, new_subject):
        """Get detailed list of schedule conflicts"""
        conflicts = []
        
        # Get all schedules for the new subject
        new_schedules = Schedule.objects.filter(subject=new_subject)
        
        if not new_schedules.exists():
            return conflicts
            
        # Get all subjects the student is enrolled in
        enrolled_subjects = Subject.objects.filter(studentsubject__student=student)
        
        # Get all schedules for enrolled subjects
        enrolled_schedules = Schedule.objects.filter(subject__in=enrolled_subjects)
        
        # Check for time conflicts
        for new_schedule in new_schedules:
            new_days = new_schedule.day.split(',')
            
            for enrolled_schedule in enrolled_schedules:
                enrolled_days = enrolled_schedule.day.split(',')
                
                # Check if any days overlap between the schedules
                for day in new_days:
                    if day in enrolled_days and self.times_overlap(new_schedule, enrolled_schedule):
                        day_name = dict(Schedule.DAYS_OF_WEEK)[day]
                        conflicts.append(
                            f"Schedule conflict: {student.full_name} is already enrolled in {enrolled_schedule.subject.name} "
                            f"on {day_name} from {enrolled_schedule.start_time.strftime('%H:%M')} to {enrolled_schedule.end_time.strftime('%H:%M')}, "
                            f"which conflicts with {new_subject.name} scheduled on {day_name} from {new_schedule.start_time.strftime('%H:%M')} to {new_schedule.end_time.strftime('%H:%M')}."
                        )
        
        return conflicts

    def times_overlap(self, schedule1, schedule2):
        """Check if two schedules overlap in time."""
        return (schedule1.start_time <= schedule2.end_time and 
                schedule1.end_time >= schedule2.start_time)

@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')

class EnrollStudentInSubjectView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser

    def post(self, request, subject_id):
        subject = get_object_or_404(Subject, pk=subject_id)
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, pk=student_id)

        # Check if student is already enrolled
        if StudentSubject.objects.filter(student=student, subject=subject).exists():
            messages.warning(request, f'{student.full_name} is already enrolled in this subject.')
            return redirect('subject_detail', pk=subject_id)

        # Check for schedule conflicts
        conflicts = self.get_enrollment_conflicts(student, subject)
        if conflicts:
            for conflict in conflicts:
                messages.error(request, conflict)
            return redirect('subject_detail', pk=subject_id)

        # Enroll the student
        StudentSubject.objects.create(student=student, subject=subject)
        
        # Store enrollment info in session for success page
        request.session['enrolled_student_name'] = student.full_name
        request.session['enrolled_subject_name'] = subject.name
        request.session['enrolled_subject_id'] = subject_id
        request.session['enrolled_student_id'] = student_id
        
        messages.success(request, f"Successfully enrolled {student.full_name} in {subject.name}.")
        return redirect('subject_detail', pk=subject.id)

    def get_enrollment_conflicts(self, student, new_subject):
        """Get detailed list of schedule conflicts"""
        conflicts = []
        
        # Get all schedules for the new subject
        new_schedules = Schedule.objects.filter(subject=new_subject)
        
        # Get all subjects the student is enrolled in
        enrolled_subjects = Subject.objects.filter(studentsubject__student=student)
        
        # Get all schedules for enrolled subjects
        enrolled_schedules = Schedule.objects.filter(subject__in=enrolled_subjects)
        
        # Check for time conflicts
        for new_schedule in new_schedules:
            new_days = new_schedule.day.split(',')
            
            for enrolled_schedule in enrolled_schedules:
                enrolled_days = enrolled_schedule.day.split(',')
                
                # Check if any days overlap between the schedules
                for day in new_days:
                    if day in enrolled_days and self.times_overlap(new_schedule, enrolled_schedule):
                        day_name = dict(Schedule.DAYS_OF_WEEK)[day]
                        conflicts.append(
                            f"Schedule conflict: {student.full_name} is already enrolled in {enrolled_schedule.subject.name} "
                            f"on {day_name} from {enrolled_schedule.start_time.strftime('%H:%M')} to {enrolled_schedule.end_time.strftime('%H:%M')}, "
                            f"which conflicts with {new_subject.name} scheduled on {day_name} from {new_schedule.start_time.strftime('%H:%M')} to {new_schedule.end_time.strftime('%H:%M')}."
                        )
                        
        return conflicts

    def times_overlap(self, schedule1, schedule2):
        return (schedule1.start_time <= schedule2.end_time and 
                schedule1.end_time >= schedule2.start_time)

class TeacherDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'scheduling/teacher_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Redirect if user is not a teacher
        if not hasattr(request.user, 'teacher'):
            messages.error(request, "You don't have access to the teacher dashboard.")
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher
        
        # Get current date and day of week
        # current_date = timezone.now()
        # philippines_tz = pytz.timezone('Asia/Manila')
        # current_date = timezone.now().astimezone(philippines_tz)

        current_date1 = datetime.now()

        # Map full day name to our model's day code
        day_mapping = {
            'monday': 'M',
            'tuesday': 'T',
            'wednesday': 'W',
            'thursday': 'Th',
            'friday': 'F',
            'saturday': 'S',
            'sunday': 'Su'  
        }
        
        # Get the current day's code
        current_day_name = current_date1.strftime('%A').lower()
        current_day = day_mapping.get(current_day_name, '')
        
        # Get today's schedules (filtered for teacher)
        # Need to filter schedules where day contains current_day (since day can now be a comma-separated list)
        today_schedules = []
        if current_day:
            # Get all schedules for this teacher
            teacher_schedules = Schedule.objects.filter(
                subject__teacher=teacher
            ).select_related(
                'subject',
                'classroom'
            ).order_by('start_time')
            
            # Filter to only include schedules that contain the current day
            for schedule in teacher_schedules:
                days = schedule.day.split(',')
                if current_day in days:
                    today_schedules.append(schedule)
        
        # Get all subjects taught by this teacher
        all_subjects = Subject.objects.filter(teacher=teacher)
        
        # Get students enrolled in teacher's subjects - count unique students
        enrolled_students = Student.objects.filter(
            studentsubject__subject__teacher=teacher
        ).distinct()
        
        # Get count of classrooms used by this teacher
        teacher_classrooms = Classroom.objects.filter(
            schedule__subject__teacher=teacher
        ).distinct()
        
        context.update({
            'teacher': teacher,
            'current_date': current_date1,
            'current_day_name': current_day_name.capitalize(),
            'today_schedules': today_schedules,
            'total_subjects': all_subjects.count(),
            'total_students': enrolled_students.count(),
            'total_classrooms': teacher_classrooms.count(),
            'subjects': all_subjects,
            'is_sunday': current_day_name == 'sunday',
        })
        
        return context

class StudentDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'scheduling/student_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if the user is a student
        if not hasattr(self.request.user, 'student'):
            messages.error(self.request, "You don't have access to the student dashboard.")
            return context
            
        student = self.request.user.student
        
        # Get current date and day of week
        # current_date = timezone.now()
        # philippines_tz = pytz.timezone('Asia/Manila')
        # current_date = timezone.now().astimezone(philippines_tz)

        
        # Map full day name to our model's day code
        day_mapping = {
            'monday': 'M',
            'tuesday': 'T',
            'wednesday': 'W',
            'thursday': 'Th',
            'friday': 'F',
            'saturday': 'S',
            'sunday': 'Su'  
        }
        
        # Get the current day's code
        current_day_name = current_date.strftime('%A').lower()
        current_day = day_mapping.get(current_day_name, '')
        
        # Get enrolled subjects
        enrolled_subjects = student.subjects.all().select_related('teacher')
        
        # Get schedules for today
        today_schedules = []
        if current_day:
            # Get all schedules for subjects the student is enrolled in
            student_schedules = Schedule.objects.filter(
                subject__in=enrolled_subjects
            ).select_related(
                'subject',
                'classroom'
            ).order_by('start_time')
            
            # Filter to only include schedules that contain the current day
            for schedule in student_schedules:
                days = schedule.day.split(',')
                if current_day in days:
                    today_schedules.append(schedule)
        
        # Get total enrollments
        total_enrollments = enrolled_subjects.count()
        
        # Get unique subjects with schedules in the week
        weekly_subjects = set()
        for subject in enrolled_subjects:
            if subject.schedule_set.exists():
                weekly_subjects.add(subject)
        
        # Determine if it's Sunday
        is_sunday = current_day_name == 'sunday'
        
        context.update({
            'student': student,
            'current_date': current_date,
            'current_day_name': current_day_name.capitalize(),
            'enrolled_subjects': enrolled_subjects,
            'today_schedules': today_schedules,
            'total_enrollments': total_enrollments,
            'total_weekly_schedules': len(weekly_subjects),
            'is_sunday': is_sunday,
        })
        
        return context

class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'scheduling/admin_dashboard.html'
    
    def test_func(self):
        # Allow access for staff users (administrators)
        return self.request.user.is_staff
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get current date and day of week
        # current_date = timezone.now()
        # philippines_tz = pytz.timezone('Asia/Manila')
        # current_date = timezone.now().astimezone(philippines_tz)


        day_mapping = {
            'monday': 'M',
            'tuesday': 'T',
            'wednesday': 'W',
            'thursday': 'Th',
            'friday': 'F',
            'saturday': 'S',
            'sunday': 'Su'  
        }
        
        # Get the current day's code, default to empty string if it's Sunday
        current_day_name = current_date.strftime('%A').lower()
        current_day = day_mapping.get(current_day_name, '')

        # Get today's schedules (empty queryset if it's Sunday)
        today_schedules = Schedule.objects.filter(
            day=current_day
        ).select_related(
            'subject',
            'subject__teacher',
            'classroom'
        ).order_by('start_time') if current_day else Schedule.objects.none()
        
        # Get statistics for admin dashboard
        total_students = Student.objects.count()
        total_teachers = Teacher.objects.count()
        total_subjects = Subject.objects.filter(is_active=True).count()
        total_classrooms = Classroom.objects.filter(is_active=True).count()
        
        context.update({
            'current_date': current_date,
            'today_schedules': today_schedules,
            'is_sunday': current_day_name == 'sunday',
            'total_students': total_students,
            'total_teachers': total_teachers,
            'total_subjects': total_subjects,
            'total_classrooms': total_classrooms
        })
        
        return context

class ResetTeacherPasswordView(LoginRequiredMixin, SuperUserRequiredMixin, View):
    def post(self, request, pk):
        teacher = get_object_or_404(Teacher, pk=pk)
        user = teacher.user
        
        # Use the existing default password instead of generating a new one
        default_password = teacher.default_password
        
        # Update user password
        user.set_password(default_password)
        user.save()
        
        messages.success(request, f"Password has been reset to the default password.")
        return redirect('teacher_detail', pk=pk)

class ResetStudentPasswordView(LoginRequiredMixin, SuperUserRequiredMixin, View):
    def post(self, request, pk):
        student = get_object_or_404(Student, pk=pk)
        user = student.user
        
        # Use the existing default password instead of generating a new one
        default_password = student.default_password
        
        # Update user password
        user.set_password(default_password)
        user.save()
        
        messages.success(request, f"Password has been reset to the default password.")
        return redirect('student_detail', pk=pk)

class SubjectToggleStatusView(LoginRequiredMixin, SuperUserRequiredMixin, View):
    def post(self, request, pk):
        subject = get_object_or_404(Subject, pk=pk)
        subject.is_active = not subject.is_active
        subject.save()
        
        status = "activated" if subject.is_active else "deactivated"
        messages.success(request, f"Subject {subject.name} has been {status}.")
        return redirect('subject_list')

class SuccessPageMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get credentials from session if they exist
        context['username'] = self.request.session.pop('new_username', None)
        context['password'] = self.request.session.pop('new_password', None)
        # Get enrollment info from session if it exists
        context['student_name'] = self.request.session.pop('enrolled_student_name', None)
        context['subject_name'] = self.request.session.pop('enrolled_subject_name', None)
        context['subject_id'] = self.request.session.pop('enrolled_subject_id', None)
        context['student_id'] = self.request.session.pop('enrolled_student_id', None)
        return context

def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(request, 'Student created successfully!')
            return redirect('student_list')
    else:
        form = StudentForm()
    return render(request, 'scheduling/student_form.html', {'form': form})

def subject_create(request):
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save()
            messages.success(request, 'Subject created successfully!')
            return redirect('subject_list')
    else:
        form = SubjectForm()
    return render(request, 'scheduling/subject_form.html', {'form': form})

def teacher_create(request):
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            # Create a new user for the teacher
            username = generate_username(form.cleaned_data['last_name'])
            password = generate_password()
            
            # Create a new user for this teacher
            user = User.objects.create_user(
                username=username,
                email=form.cleaned_data['email'],
                password=password
            )
            
            # Save the teacher but don't commit to DB yet
            teacher = form.save(commit=False)
            teacher.user = user
            teacher.default_password = password
            teacher.save()
            
            messages.success(request, 'Teacher created successfully!')
            return redirect('teacher_list')
    else:
        form = TeacherForm()
    return render(request, 'scheduling/teacher_form.html', {'form': form})

def schedule_create(request):
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, 'Schedule created successfully!')
            return redirect('schedule_list')
    else:
        form = ScheduleForm()
    return render(request, 'scheduling/schedule_form.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def user_list(request):
    # Get all users
    users = User.objects.all()
    
    # Prepare user data with type information
    user_data = []
    for user in users:
        user_type = []
        if user.is_superuser:
            user_type.append('superuser')
        
        # Check if user is a teacher
        try:
            if hasattr(user, 'teacher'):
                user_type.append('teacher')
        except:
            pass
            
        # Check if user is a student
        try:
            if hasattr(user, 'student'):
                user_type.append('student')
        except:
            pass
            
        if not user_type:
            user_type.append('regular')
            
        # Get full name based on user type
        full_name = user.get_full_name() or user.username
        
        # If user is a teacher or student, use their profile name
        try:
            if hasattr(user, 'teacher'):
                teacher = user.teacher
                if teacher.first_name and teacher.last_name:
                    full_name = f"{teacher.first_name} {teacher.middle_name or ''} {teacher.last_name}".strip()
        except:
            pass
            
        try:
            if hasattr(user, 'student'):
                student = user.student
                if student.first_name and student.last_name:
                    full_name = f"{student.first_name} {student.middle_name or ''} {student.last_name}".strip()
        except:
            pass
            
        user_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': full_name,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'user_type': user_type
        })
    
    return render(request, 'scheduling/user_list.html', {'users': user_data})

@login_required
def train_cnn(request):
    datadir = './aligned_img'
    modeldir = './model/20180402-114759.pb'
    #modeldir = './model/20170511-185253.pb'
    classifier_filename = './class/classifier.pkl'
    print ("Training Start")
    obj=training(datadir,modeldir,classifier_filename)
    try:
        get_file=obj.main_train()
        print('Saved classifier model to file "%s"' % get_file)
        messages.success(request, 'CNN Model Trained successfully')
    except ValueError as e:
        messages.error(request, "Error: {}".format(e))
        return redirect('user_list')
    # Redirect to the users page
    return redirect('user_list')

@login_required
def data_preprocess(request):
    # Set the base directory (assuming you have a 'static' folder within your project)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # input_datadir = os.path.join(base_dir, 'static', 'train_img')
    # output_datadir = os.path.join(base_dir, 'static', 'aligned_img')

    input_datadir = './train_img'
    output_datadir = './aligned_img'

    try:
        # Initialize the preprocess object
        obj = preprocesses(input_datadir, output_datadir)

        # Collect data
        nrof_images_total, nrof_successfully_aligned = obj.collect_data()

        # Check if there are 0 images
        if nrof_images_total == 0:
            messages.error(request, "No images found in the input directory.")
            return redirect('user_list')

        # Print the number of images and successfully aligned images
        print(f'Total number of images: {nrof_images_total}')
        print(f'Number of successfully aligned images: {nrof_successfully_aligned}')
        message = f"{nrof_images_total} images found in the input directory.<br>"
        message += f"{nrof_successfully_aligned} images successfully aligned."
        messages.success(request, message)

    except Exception as e:
        messages.error(request, f"An error occurred during data preprocessing: {e}")
        return redirect('user_list')

    # Redirect to the users page
    return redirect('user_list')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def assign_rfid(request):
    if request.method == 'POST':
        form = RFIDAssignmentForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'RFID card successfully assigned to {user.username}')
            return redirect('user_detail', user_id=user.id)
    else:
        # Check if a user ID was provided in the query parameters
        user_id = request.GET.get('user')
        initial_data = {}
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                initial_data['user'] = user
            except User.DoesNotExist:
                pass
                
        form = RFIDAssignmentForm(initial=initial_data)
        
    return render(request, 'scheduling/assign_rfid.html', {'form': form})

@user_passes_test(lambda u: u.is_superuser)
def user_detail(request, user_id):
    # Get the user object
    user = get_object_or_404(User, id=user_id)
    
    # Check if user has teacher profile and get teacher data
    teacher_data = None
    try:
        if hasattr(user, 'teacher'):
            teacher = user.teacher
            teacher_data = {
                'id': teacher.id,
                'first_name': teacher.first_name,
                'middle_name': teacher.middle_name,
                'last_name': teacher.last_name,
                'address': teacher.address,
                'email': teacher.email,
                'default_password': teacher.default_password
            }
    except:
        pass
        
    # Check if user has student profile and get student data
    student_data = None
    try:
        if hasattr(user, 'student'):
            student = user.student
            student_data = {
                'id': student.id,
                'student_id': student.student_id,
                'first_name': student.first_name,
                'middle_name': student.middle_name,
                'last_name': student.last_name,
                'address': student.address,
                'email': student.email,
                'course': student.course,
                'year_level': student.year_level,
                'default_password': student.default_password
            }
    except:
        pass
    
    # Create a user data dictionary with safe access to properties
    user_data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_superuser': user.is_superuser,
        'is_staff': user.is_staff,
        'date_joined': user.date_joined,
        'last_login': user.last_login,
        'is_active': user.is_active,
        # Add rfid_uid safely
        'rfid_uid': getattr(user, 'rfid_uid', None)
    }
    
    context = {
        'user_obj': user_data,
        'is_teacher': teacher_data is not None,
        'is_student': student_data is not None,
        'teacher': teacher_data,
        'student': student_data,
    }
    return render(request, 'scheduling/user_detail.html', context)

@user_passes_test(lambda u: u.is_superuser)
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            # Handle superuser status
            if 'is_superuser' in request.POST:
                user.is_superuser = True
            else:
                user.is_superuser = False
            # Handle staff status
            if 'is_staff' in request.POST:
                user.is_staff = True
            else:
                user.is_staff = False
            user.save()
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('user_list')
    else:
        form = UserEditForm(instance=user)
    
    return render(request, 'scheduling/user_form.html', {
        'form': form,
        'user_obj': user,
    })

@user_passes_test(lambda u: u.is_superuser)
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('user_list')
    return render(request, 'scheduling/user_confirm_delete.html', {'user': user})

@login_required
def take_attendance(request, schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)
    
    # Only allow the teacher assigned to this subject or superusers to take attendance
    if not (request.user.is_superuser or 
            (hasattr(request.user, 'teacher') and request.user.teacher == schedule.subject.teacher)):
        messages.error(request, 'You are not authorized to take attendance for this class.')
        return redirect('home')
    
    # Get all students enrolled in this subject
    students = Student.objects.filter(
        studentsubject__subject=schedule.subject,
        is_active=True
    ).order_by('last_name', 'first_name')
    
    # Get the current date
    # current_date = timezone.now().date()
    # philippines_tz = pytz.timezone('Asia/Manila')
    # current_date = timezone.now().astimezone(philippines_tz)

    
    # Check if attendance has already been recorded for this schedule and date
    existing_records = Attendance.objects.filter(
        schedule=schedule,
        date=current_date
    )
    
    # For admin users, get the teacher from the schedule
    recorded_by = None
    if hasattr(request.user, 'teacher'):
        recorded_by = request.user.teacher
    else:
        # If admin, use the subject's teacher
        recorded_by = schedule.subject.teacher
    
    # Create a formset for attendance records
    AttendanceFormSetFactory = modelformset_factory(
        Attendance,
        form=AttendanceForm,
        formset=AttendanceFormSet,
        extra=len(students) - existing_records.count()
    )
    
    if request.method == 'POST':
        formset = AttendanceFormSetFactory(
            request.POST,
            queryset=existing_records,
        )
        
        # Set the custom attributes after initialization
        formset.schedule = schedule
        formset.date = current_date
        formset.teacher = recorded_by
        
        if formset.is_valid():
            formset.save_all()
            messages.success(request, 'Attendance recorded successfully!')
            return redirect('take_attendance', schedule_id=schedule.id)
        else:
            messages.error(request, 'There was an error recording attendance. Please check the form.')
    else:
        # Initialize formset with existing records or empty forms
        initial_data = []
        
        # Create a dictionary to quickly look up existing records
        existing_records_dict = {record.student_id: record for record in existing_records}
        
        for student in students:
            # If we already have a record for this student, it will be part of the queryset
            if student.id not in existing_records_dict:
                initial_data.append({
                    'student': student.id,
                    'status': 'present',  # Default status
                })
        
        formset = AttendanceFormSetFactory(
            queryset=existing_records,
            initial=initial_data,
        )
        
        # Set the custom attributes after initialization
        formset.schedule = schedule
        formset.date = current_date
        formset.teacher = recorded_by
    
    # Pair each form with its corresponding student for display
    student_forms = []
    for i, form in enumerate(formset.forms):
        student_id = form.initial.get('student') or form.instance.student_id if form.instance else None
        student = next((s for s in students if s.id == student_id), None)
        if student:
            student_forms.append((student, form))
    
    context = {
        'schedule': schedule,
        'formset': formset,
        'student_forms': student_forms,
        'current_date': current_date,
        'management_form': formset.management_form,
    }
    
    return render(request, 'scheduling/take_attendance.html', context)

@login_required
def attendance_history(request):
    # This view is for admins to see attendance history across all teachers
    if not request.user.is_superuser and not request.user.is_staff:
        messages.error(request, "You don't have permission to access this page.")
        return redirect('home')
    
    # Get all teachers
    teachers = Teacher.objects.all().order_by('last_name', 'first_name')
    
    # Get selected date from request or use today's date
    selected_date = request.GET.get('date')
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    # Get all attendance records for the selected date
    attendance_records = Attendance.objects.filter(
        date=selected_date
    ).select_related(
        'student',
        'schedule',
        'schedule__subject',
        'schedule__subject__teacher',
        'schedule__classroom',
        'recorded_by'
    ).order_by('schedule__subject__name', 'student__last_name')
    
    # Group attendance records by teacher and subject
    attendance_by_teacher = {}
    for record in attendance_records:
        teacher = record.schedule.subject.teacher
        subject = record.schedule.subject
        
        if teacher not in attendance_by_teacher:
            attendance_by_teacher[teacher] = {}
        
        if subject not in attendance_by_teacher[teacher]:
            attendance_by_teacher[teacher][subject] = []
        
        attendance_by_teacher[teacher][subject].append(record)
    
    context = {
        'teachers': teachers,
        'selected_date': selected_date,
        'attendance_by_teacher': attendance_by_teacher,
        'today': timezone.now().date(),
    }
    
    return render(request, 'scheduling/attendance_history.html', context)

@login_required
def attendance_history_teacher(request, teacher_id):
    # This view is for a specific teacher's attendance history
    # Check if the user is the teacher or an admin
    teacher = get_object_or_404(Teacher, id=teacher_id)
    
    if not request.user.is_superuser and not request.user.is_staff:
        if not hasattr(request.user, 'teacher') or request.user.teacher.id != teacher_id:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('home')
    
    # Get selected date from request or use today's date
    selected_date = request.GET.get('date')
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    # Get all subjects taught by this teacher
    subjects = Subject.objects.filter(teacher=teacher)
    
    # Get all attendance records for this teacher on the selected date
    attendance_records = Attendance.objects.filter(
        schedule__subject__teacher=teacher,
        date=selected_date
    ).select_related(
        'student',
        'schedule',
        'schedule__subject',
        'schedule__classroom'
    ).order_by('schedule__subject__name', 'student__last_name')
    
    # Group attendance records by subject and schedule
    attendance_by_subject = {}
    for record in attendance_records:
        subject = record.schedule.subject
        schedule = record.schedule
        
        if subject not in attendance_by_subject:
            attendance_by_subject[subject] = {}
        
        if schedule not in attendance_by_subject[subject]:
            attendance_by_subject[subject][schedule] = []
        
        attendance_by_subject[subject][schedule].append(record)
    
    context = {
        'teacher': teacher,
        'subjects': subjects,
        'selected_date': selected_date,
        'attendance_by_subject': attendance_by_subject,
        'today': timezone.now().date(),
    }
    
    return render(request, 'scheduling/attendance_history_teacher.html', context)

@login_required
def take_attendance_rfid(request, schedule_id):
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    # Get the schedule
    schedule = get_object_or_404(Schedule, id=schedule_id)
    
    # Check if the user has permission to take attendance for this schedule
    # Either the user is the teacher of the subject or an admin
    if not (request.user.is_superuser or request.user.is_staff or 
            (hasattr(request.user, 'teacher') and request.user.teacher == schedule.subject.teacher)):
        messages.error(request, "You don't have permission to take attendance for this schedule.")
        return redirect('home')
    
    # Get the students enrolled in this subject
    students = Student.objects.filter(subjects=schedule.subject).order_by('last_name', 'first_name')
    
    if not students.exists():
        messages.warning(request, "No students are enrolled in this subject.")
        return redirect('schedule_detail', pk=schedule_id)
    
    # Get the current date
    # current_date = timezone.now().date()
    # philippines_tz = pytz.timezone('Asia/Manila')
    # current_date = timezone.now().astimezone(philippines_tz)

    
    # For admin users, get the teacher from the schedule
    recorded_by = None
    if hasattr(request.user, 'teacher'):
        recorded_by = request.user.teacher
    else:
        # If admin, use the subject's teacher
        recorded_by = schedule.subject.teacher
    
    # Get existing attendance records for this schedule and date
    existing_records = Attendance.objects.filter(
        schedule=schedule,
        date=current_date
    )
    
    # Create a dictionary to quickly look up existing records
    existing_records_dict = {record.student_id: record for record in existing_records}
    
    # Create a dictionary to map RFID UIDs to students
    rfid_to_student = {}
    for student in students:
        if student.user and student.user.rfid_uid:
            rfid_to_student[student.user.rfid_uid] = student
    
    # Count students with RFID cards
    students_with_rfid = len(rfid_to_student)
    
    # Process RFID scan
    if request.method == 'POST':
        form = RFIDAttendanceForm(request.POST, schedule=schedule, date=current_date, teacher=recorded_by)
        
        if form.is_valid():
            rfid_uid = form.cleaned_data['rfid_uid']
            
            # Check if the RFID belongs to a student in this class
            if rfid_uid in rfid_to_student:
                student = rfid_to_student[rfid_uid]
                
                # Check if attendance already recorded for this student
                if student.id in existing_records_dict:
                    # Student already has an attendance record
                    record = existing_records_dict[student.id]
                    if record.status == 'present':
                        # Student already marked present - this is a double tap
                        if is_ajax:
                            # For AJAX requests, return JSON response that will be handled by JavaScript
                            double_tap_response = {
                                'status': 'warning',
                                'message': f"{student.first_name} {student.last_name} is already marked present for this class.",
                                'student_name': f"{student.first_name} {student.last_name}",
                                'is_double_tap': True,
                                'timestamp': record.timestamp.strftime('%I:%M:%S %p')
                            }
                            return JsonResponse(double_tap_response)
                        else:
                            # For regular form submissions, use Django messages
                            messages.warning(request, f"{student.first_name} {student.last_name} is already marked present for this class.")
                            return redirect('take_attendance_rfid', schedule_id=schedule.id)
                    else:
                        # Update existing record
                        record.status = 'present'
                        record.save()
                        messages.success(request, f"Attendance updated for {student.first_name} {student.last_name}")
                else:
                    # Create new attendance record
                    Attendance.objects.create(
                        schedule=schedule,
                        student=student,
                        date=current_date,
                        status='present',
                        recorded_by=recorded_by
                    )
                    
                    if is_ajax:
                        return JsonResponse({
                            'status': 'success',
                            'message': f"Attendance recorded for {student.first_name} {student.last_name}",
                            'student_name': f"{student.first_name} {student.last_name}"
                        })
                    else:
                        messages.success(request, f"Attendance recorded for {student.first_name} {student.last_name}")
                
                # Refresh the attendance records
                existing_records = Attendance.objects.filter(
                    schedule=schedule,
                    date=current_date
                )
                existing_records_dict = {record.student_id: record for record in existing_records}
            else:
                if is_ajax:
                    return JsonResponse({
                        'status': 'error',
                        'message': "RFID card not recognized or not assigned to any student in this class.",
                        'is_double_tap': False
                    })
                else:
                    messages.error(request, "RFID card not recognized or not assigned to any student in this class.")
        
        # Clear the form for the next scan
        form = RFIDAttendanceForm(schedule=schedule, date=current_date, teacher=recorded_by)
    else:
        form = RFIDAttendanceForm(schedule=schedule, date=current_date, teacher=recorded_by)
    
    # Get all students and their attendance status
    student_attendance = []
    for student in students:
        status = 'Not Recorded'
        timestamp = None
        if student.id in existing_records_dict:
            record = existing_records_dict[student.id]
            status = record.status.capitalize()
            timestamp = record.timestamp
        
        has_rfid = bool(student.user and student.user.rfid_uid)
        
        student_attendance.append({
            'student': student,
            'status': status,
            'has_rfid': has_rfid,
            'timestamp': timestamp
        })
    
    context = {
        'schedule': schedule,
        'date': current_date,
        'form': form,
        'student_attendance': student_attendance,
        'students_with_rfid': students_with_rfid,
        'total_students': len(students),
        'recorded_count': len(existing_records)
    }
    
    return render(request, 'scheduling/take_attendance_rfid.html', context)

# @login_required
# def cnn_attendance(request, schedule_id):
#     schedule = get_object_or_404(Schedule, id=schedule_id)

#     video= 0 # 0 FOR OPENCV CAM OR PUT A VIDEO FILE PATH
#     modeldir = './model/20180402-114759.pb'
#     classifier_filename = './class/classifier.pkl'
#     npy='./npy'
#     train_img="./train_img"

#     # philippines_tz = pytz.timezone('Asia/Manila')
#     # current_date = timezone.now().astimezone(philippines_tz)

#     # For admin users, get the teacher from the schedule
#     recorded_by = None
#     if hasattr(request.user, 'teacher'):
#         recorded_by = request.user.teacher
#     else:
#         # If admin, use the subject's teacher
#         recorded_by = schedule.subject.teacher

#     with tf.Graph().as_default():
#         gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.6)
#         sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))
#         with sess.as_default():
#             pnet, rnet, onet = detect_face.create_mtcnn(sess, npy)
#             minsize = 30  # minimum size of face
#             threshold = [0.6,0.7,0.7]  #[0.7,0.8,0.8]  # three steps's threshold
#             factor = 0.709  # scale factor
#             margin = 44
#             batch_size =100 #1000
#             image_size = 182
#             input_image_size = 160
#             HumanNames = os.listdir(train_img)
#             HumanNames.sort()
#             print('Loading Model')
#             facenet.load_model(modeldir)
#             images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
#             embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
#             phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")
#             embedding_size = embeddings.get_shape()[1]
#             classifier_filename_exp = os.path.expanduser(classifier_filename)
#             with open(classifier_filename_exp, 'rb') as infile:
#                 (model, class_names) = pickle.load(infile,encoding='latin1')
            
#             video_capture = cv2.VideoCapture(video)
#             print('Start Recognition')
#             while True:
#                 ret, frame = video_capture.read()
#                 # frame = cv2.resize(frame, (800, 600))    #resize frame (optional)
#                 frame = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)    #resize frame (optional)
#                 timer =time.time()
#                 if frame.ndim == 2:
#                     frame = facenet.to_rgb(frame)
#                 bounding_boxes, _ = detect_face.detect_face(frame, minsize, pnet, rnet, onet, threshold, factor)
#                 faceNum = bounding_boxes.shape[0]
#                 if faceNum > 0:
#                     det = bounding_boxes[:, 0:4]
#                     img_size = np.asarray(frame.shape)[0:2]
#                     cropped = []
#                     scaled = []
#                     scaled_reshape = []
#                     for i in range(faceNum):
#                         emb_array = np.zeros((1, embedding_size))
#                         xmin = int(det[i][0])
#                         ymin = int(det[i][1])
#                         xmax = int(det[i][2])
#                         ymax = int(det[i][3])
#                         try:
#                             # inner exception
#                             if xmin <= 0 or ymin <= 0 or xmax >= len(frame[0]) or ymax >= len(frame):
#                                 print('Face is very close!')
#                                 continue
#                             cropped.append(frame[ymin:ymax, xmin:xmax,:])
#                             cropped[i] = facenet.flip(cropped[i], False)
#                             scaled.append(np.array(Image.fromarray(cropped[i]).resize((image_size, image_size))))
#                             scaled[i] = cv2.resize(scaled[i], (input_image_size,input_image_size),
#                                                     interpolation=cv2.INTER_CUBIC)
#                             scaled[i] = facenet.prewhiten(scaled[i])
#                             scaled_reshape.append(scaled[i].reshape(-1,input_image_size,input_image_size,3))
#                             feed_dict = {images_placeholder: scaled_reshape[i], phase_train_placeholder: False}
#                             emb_array[0, :] = sess.run(embeddings, feed_dict=feed_dict)
#                             predictions = model.predict_proba(emb_array)
#                             best_class_indices = np.argmax(predictions, axis=1)
#                             best_class_probabilities = predictions[np.arange(len(best_class_indices)), best_class_indices]
#                             print(best_class_probabilities)
#                             if best_class_probabilities>0.85: #ACCURACY RATING 
#                                 cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)    #boxing face
#                                 for H_i in HumanNames:
#                                     if HumanNames[best_class_indices[0]] == H_i:
#                                         result_names = HumanNames[best_class_indices[0]]
#                                         print("Predictions : [ name: {} , accuracy: {:.3f} ]".format(HumanNames[best_class_indices[0]],best_class_probabilities[0]))
#                                         cv2.rectangle(frame, (xmin, ymin-20), (xmax, ymin-2), (0, 255,255), -1)
#                                         cv2.putText(frame, result_names, (xmin,ymin-5), cv2.FONT_HERSHEY_COMPLEX_SMALL,
#                                                     1, (0, 0, 0), thickness=1, lineType=1)
#                                         # print(result_names)
#                                         try:
#                                             student_obj = Student.objects.get(pk=result_names)  # or match on name if that's what you're storing
#                                         except Student.DoesNotExist:
#                                             print(f"No student found with ID: {result_names}")
#                                             continue

#                                         current_datetime1 = datetime.now()

#                                         is_enrolled = StudentSubject.objects.filter(student=student_obj, subject=schedule.subject).exists()

#                                         if not is_enrolled:
#                                             print(f"Student {student_obj} is not enrolled in subject: {schedule.subject}")
#                                             continue  # Skip this student

#                                         existing_attendance = Attendance.objects.filter(schedule=schedule, student=student_obj, date=current_datetime1).first()

#                                         if not existing_attendance:
#                                             student_attend = Attendance.objects.create(
#                                                 schedule=schedule,
#                                                 student=student_obj,
#                                                 date=current_datetime1,
#                                                 status='present',
#                                                 recorded_by=recorded_by
#                                             )
#                                             student_attend.save()

#                                             print(f"Attendance Time-IN recorded for student: {student_obj}")
#                                         else:
#                                             print(f"Student {student_obj} already Time-IN to this event.")
                                  
#                             else :
#                                 cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
#                                 cv2.rectangle(frame, (xmin, ymin-20), (xmax, ymin-2), (0, 255,255), -1)
#                                 cv2.putText(frame, "Unknown", (xmin,ymin-5), cv2.FONT_HERSHEY_COMPLEX_SMALL,
#                                                     1, (0, 0, 0), thickness=1, lineType=1)
#                         except Exception as e: 
#                             print(f"Error saving attendance: {e}")
                           
#                 endtimer = time.time()
#                 fps = 1/(endtimer-timer)
#                 cv2.rectangle(frame,(15,30),(135,60),(0,255,255),-1)
#                 cv2.putText(frame, "fps: {:.2f}".format(fps), (20, 50),cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
#                 cv2.imshow('Face Recognition', frame)
#                 key= cv2.waitKey(1)
#                 if key== 113: # "q"
#                     break
#             video_capture.release()
#             cv2.destroyAllWindows()
       
#     return redirect('teacher_dashboard')

stop_stream_flags = {}
# Top-level variable (in-memory example)
attendance_messages = {}

def generate_frames(schedule_id):
    schedule = get_object_or_404(Schedule, id=schedule_id)

    video = 0
    modeldir = './model/20180402-114759.pb'
    classifier_filename = './class/classifier.pkl'
    npy = './npy'
    train_img = "./train_img"

    recorded_by = None
    if hasattr(schedule.subject.teacher.user, 'teacher'):
        recorded_by = schedule.subject.teacher
    else:
        return  # can't proceed

    global stop_stream_flags
    stop_event = stop_stream_flags.get(schedule_id, threading.Event())
    stop_stream_flags[schedule_id] = stop_event

    with tf.Graph().as_default():
        gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.6)
        sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options, log_device_placement=False))
        with sess.as_default():
            pnet, rnet, onet = detect_face.create_mtcnn(sess, npy)

            facenet.load_model(modeldir)
            images_placeholder = tf.get_default_graph().get_tensor_by_name("input:0")
            embeddings = tf.get_default_graph().get_tensor_by_name("embeddings:0")
            phase_train_placeholder = tf.get_default_graph().get_tensor_by_name("phase_train:0")
            embedding_size = embeddings.get_shape()[1]

            with open(classifier_filename, 'rb') as infile:
                model, class_names = pickle.load(infile, encoding='latin1')

            HumanNames = sorted(os.listdir(train_img))
            print('Loading Model')
            video_capture = cv2.VideoCapture(video)
            video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

            print('Start Recognition')
            while True:
                ret, frame = video_capture.read()
                if not ret:
                    break

                frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                timer = time.time()
                if frame.ndim == 2:
                    frame = facenet.to_rgb(frame)

                bounding_boxes, _ = detect_face.detect_face(frame, 30, pnet, rnet, onet, [0.6, 0.7, 0.7], 0.709)
                faceNum = bounding_boxes.shape[0]

                if faceNum > 0:
                    det = bounding_boxes[:, 0:4]
                    for i in range(faceNum):
                        xmin, ymin, xmax, ymax = map(int, det[i])
                        try:
                            if xmin <= 0 or ymin <= 0 or xmax >= len(frame[0]) or ymax >= len(frame):
                                print('Face is very close!')
                                continue
                            cropped = frame[ymin:ymax, xmin:xmax, :]
                            cropped = facenet.flip(cropped, False)
                            scaled = np.array(Image.fromarray(cropped).resize((182, 182)))
                            scaled = cv2.resize(scaled, (160, 160), interpolation=cv2.INTER_CUBIC)
                            scaled = facenet.prewhiten(scaled)
                            reshaped = scaled.reshape(-1, 160, 160, 3)

                            emb_array = np.zeros((1, embedding_size))
                            emb_array[0, :] = sess.run(embeddings, feed_dict={
                                images_placeholder: reshaped,
                                phase_train_placeholder: False
                            })

                            predictions = model.predict_proba(emb_array)
                            best_class_idx = np.argmax(predictions, axis=1)
                            best_class_prob = predictions[np.arange(len(best_class_idx)), best_class_idx]
                            print(best_class_prob)
                            if best_class_prob > 0.85:
                                result_name = HumanNames[best_class_idx[0]]
                                print("Predictions : [ name: {} , accuracy: {:.3f} ]".format(HumanNames[best_class_idx[0]],best_class_prob[0]))
                                cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 255, 0), 2)
                                cv2.rectangle(frame, (xmin, ymin-20), (xmax, ymin-2), (0, 255, 255), -1)
                                cv2.putText(frame, result_name, (xmin, ymin - 5), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (0, 0, 0), 1)

                                try:
                                    student_obj = Student.objects.get(pk=result_name)
                                except Student.DoesNotExist:
                                    print(f"No student found with ID: {result_names}")
                                    continue

                                current_datetime1 = datetime.now()

                                is_enrolled = StudentSubject.objects.filter(student=student_obj, subject=schedule.subject).exists()

                                if not is_enrolled:
                                    print(f"Student {student_obj} is not enrolled in subject: {schedule.subject}")
                                    continue  # Skip this student

                                existing_attendance = Attendance.objects.filter(schedule=schedule, student=student_obj, date=current_datetime1).first()

                                if not existing_attendance:
                                    # Compare current time with schedule start time
                                    schedule_start_datetime = datetime.combine(current_datetime1.date(), schedule.start_time)
                                    time_difference = (current_datetime1 - schedule_start_datetime).total_seconds() / 60  # in minutes

                                    # Default to "present"
                                    status = 'present'

                                    if time_difference >= 60:
                                        status = 'absent'
                                    elif time_difference >= 15:
                                        status = 'late'

                                    student_attend = Attendance.objects.create(
                                        schedule=schedule,
                                        student=student_obj,
                                        date=current_datetime1,
                                        status=status,
                                        recorded_by=recorded_by
                                    )
                                    student_attend.save()

                                    try:
                                        subject = f"Attendance Recorded for {schedule.subject.name}"
                                        message = (
                                            f"Dear {student_obj.first_name},\n\n"
                                            f"Your attendance for the subject \"{schedule.subject.name}\" "
                                            f"has been recorded as **{status.upper()}** on {current_datetime1.strftime('%Y-%m-%d %H:%M:%S')}.\n\n"
                                            f"Recorded by: {recorded_by.full_name if recorded_by else 'System'}\n\n"
                                            f"Thank you,\nAttendance Monitoring System"
                                        )
                                        recipient_email = student_obj.email

                                        send_mail(
                                            subject,
                                            message,
                                            settings.DEFAULT_FROM_EMAIL,  # Make sure it's configured in settings.py
                                            [recipient_email],
                                            fail_silently=False,
                                        )
                                        print(f"Email sent to {recipient_email}")
                                    except Exception as e:
                                        print(f"Failed to send email to {student_obj.email}: {e}")

                                    attendance_messages[schedule_id] = {
                                        'message': f"{status.capitalize()} marked for student: {student_obj}",
                                        'type': 'success'
                                    }
                                    print(f"{status.capitalize()} marked for student: {student_obj}")
                                else:
                                    print(f"Student {student_obj} already has attendance on this day for this subject.")
                            else:
                                cv2.rectangle(frame, (xmin, ymin), (xmax, ymax), (0, 0, 255), 2)
                                cv2.rectangle(frame, (xmin, ymin-20), (xmax, ymin-2), (0, 0, 255), -1)
                                cv2.putText(frame, "Unknown", (xmin, ymin - 5), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1, (255, 255, 255), 1)
                        
                        except Exception as e: 
                             print(f"Error saving attendance: {e}")

                fps = 1 / (time.time() - timer)
                cv2.rectangle(frame, (15, 30), (135, 60), (0, 255, 255), -1)
                cv2.putText(frame, "fps: {:.2f}".format(fps), (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

            video_capture.release()
            print(f"Stream for schedule {schedule_id} stopped.")

@login_required
def video_feed(request, schedule_id):
    global stop_stream_flags
    stop_stream_flags[schedule_id] = threading.Event()
    return StreamingHttpResponse(generate_frames(schedule_id),
                                 content_type='multipart/x-mixed-replace; boundary=frame')

def stop_stream(request, schedule_id):
    global stop_stream_flags
    stop_event = stop_stream_flags.get(schedule_id)
    if stop_event:
        stop_event.set()
        return JsonResponse({'status': 'stopped'})
    return JsonResponse({'status': 'not_running'})