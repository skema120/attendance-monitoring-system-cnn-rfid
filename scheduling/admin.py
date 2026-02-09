from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Teacher, Student, Classroom, Subject, Schedule, StudentSubject

# Register your models here.

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email')
    ordering = ('username',)

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'user')
    search_fields = ('full_name', 'email')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'full_name', 'email', 'course', 'year_level', 'is_active')
    search_fields = ('student_id', 'full_name', 'email', 'course')
    list_filter = ('year_level', 'is_active')

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'capacity', 'is_active')
    search_fields = ('room_number',)
    list_filter = ('is_active',)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'teacher')
    search_fields = ('code', 'name', 'teacher__full_name')
    autocomplete_fields = ('teacher',)

@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('subject', 'classroom', 'day', 'start_time', 'end_time')
    list_filter = ('day',)
    search_fields = ('subject__name', 'classroom__room_number')
    autocomplete_fields = ('subject', 'classroom')

@admin.register(StudentSubject)
class StudentSubjectAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'date_enrolled')
    search_fields = ('student__full_name', 'subject__name')
    autocomplete_fields = ('student', 'subject')
