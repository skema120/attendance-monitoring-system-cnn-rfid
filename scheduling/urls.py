from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .authentication import StudentIDAuthBackend
from .forms import CustomAuthenticationForm

urlpatterns = [
    # Authentication URLs
    
    # path('login/', auth_views.LoginView.as_view(
    #     template_name='registration/login.html',
    #     authentication_form=CustomAuthenticationForm
    # ), name='login'),

    path('login/', views.CustomLoginView.as_view(), name='login'),
    
    path('logout/', views.logout_view, name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='registration/password_change_form.html',
        success_url='/password_change/done/'
    ), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='registration/password_change_done.html'
    ), name='password_change_done'),
    
    # Home and Profile
    path('', views.home, name='home'),
    path('profile/', views.profile, name='profile'),
    
    # Dashboards
    path('teacher/dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('student/dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('system/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    
    # Student-specific views
    path('student/schedule/', views.ScheduleListView.as_view(), name='student_schedule'),
    path('student/profile/', views.StudentDetailView.as_view(), name='student_profile'),
    
    # Teacher/Admin Management Views
    path('classrooms/', views.ClassroomListView.as_view(), name='classroom_list'),
    path('classrooms/new/', views.ClassroomCreateView.as_view(), name='classroom_create'),
    path('classrooms/<int:pk>/', views.ClassroomDetailView.as_view(), name='classroom_detail'),
    path('classrooms/<int:pk>/edit/', views.ClassroomUpdateView.as_view(), name='classroom_update'),
    path('classrooms/<int:pk>/delete/', views.ClassroomDeleteView.as_view(), name='classroom_delete'),
    path('classrooms/<int:pk>/toggle-status/', views.ClassroomToggleStatusView.as_view(), name='classroom_toggle_status'),
    
    # Teacher Management
    path('teachers/', views.TeacherListView.as_view(), name='teacher_list'),
    path('teachers/new/', views.TeacherCreateView.as_view(), name='teacher_create'),
    path('teachers/<int:pk>/', views.TeacherDetailView.as_view(), name='teacher_detail'),
    path('teachers/<int:pk>/edit/', views.TeacherUpdateView.as_view(), name='teacher_update'),
    path('teachers/<int:pk>/delete/', views.TeacherDeleteView.as_view(), name='teacher_delete'),
    path('teachers/<int:pk>/reset-password/', views.ResetTeacherPasswordView.as_view(), name='teacher_reset_password'),
    
    # Subject Management
    path('subjects/', views.SubjectListView.as_view(), name='subject_list'),
    path('subjects/new/', views.SubjectCreateView.as_view(), name='subject_create'),
    path('subjects/<int:pk>/', views.SubjectDetailView.as_view(), name='subject_detail'),
    path('subjects/<int:pk>/edit/', views.SubjectUpdateView.as_view(), name='subject_update'),
    path('subjects/<int:pk>/delete/', views.SubjectDeleteView.as_view(), name='subject_delete'),
    path('subjects/<int:pk>/toggle-status/', views.SubjectToggleStatusView.as_view(), name='subject_toggle_status'),
    
    # Schedule Management
    path('schedules/', views.ScheduleListView.as_view(), name='schedule_list'),
    path('schedules/new/', views.ScheduleCreateView.as_view(), name='schedule_create'),
    path('schedules/<int:pk>/', views.ScheduleDetailView.as_view(), name='schedule_detail'),
    path('schedules/<int:pk>/edit/', views.ScheduleUpdateView.as_view(), name='schedule_update'),
    path('schedules/<int:pk>/delete/', views.ScheduleDeleteView.as_view(), name='schedule_delete'),
    
    # Student Management (Teacher/Admin only)
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/<int:pk>/face_registration/', views.FaceRegistrationView.as_view(), name='face-registration'),
    path('students/new/', views.StudentCreateView.as_view(), name='student_create'),
    path('students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('students/<int:pk>/edit/', views.StudentUpdateView.as_view(), name='student_update'),
    path('students/<int:pk>/delete/', views.StudentDeleteView.as_view(), name='student_delete'),
    path('students/<int:pk>/subjects/', views.StudentSubjectsView.as_view(), name='student_subjects'),
    path('students/<int:pk>/reset-password/', views.ResetStudentPasswordView.as_view(), name='reset_student_password'),
    
    # Student-Subject Enrollment (Teacher/Admin only)
    path('subjects/<int:subject_id>/enroll/', views.EnrollStudentInSubjectView.as_view(), name='enroll_student_in_subject'),
    path('subjects/<int:subject_id>/unenroll/', views.UnenrollStudentView.as_view(), name='unenroll_student'),
    
    # User Management (Admin only)
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('users/assign-rfid/', views.assign_rfid, name='assign_rfid'),

    path('users/data_preprocess/', views.data_preprocess, name='data-preprocess'),
    path('users/train_cnn/', views.train_cnn, name='train-cnn'),

    
    # Attendance Management
    #cnn
    # path('schedules/<int:schedule_id>/attendance/cnn/', views.cnn_attendance, name='cnn-attendance'),
    path('video_feed/<int:schedule_id>/', views.video_feed, name='video_feed'),
    path('stop-stream/<int:schedule_id>/', views.stop_stream, name='stop_stream'),

    path('schedules/<int:schedule_id>/attendance/', views.take_attendance, name='take_attendance'),
    path('schedules/<int:schedule_id>/attendance/rfid/', views.take_attendance_rfid, name='take_attendance_rfid'),
    path('attendance/history/', views.attendance_history, name='attendance_history'),
    path('attendance/history/teacher/<int:teacher_id>/', views.attendance_history_teacher, name='attendance_history_teacher'),
]
