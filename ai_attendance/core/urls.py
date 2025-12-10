from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add_student/', views.add_student, name='add_student'),
    path('add_teacher/', views.add_teacher, name='add_teacher'),
    path('train/', views.train, name='train'),
    path('upload_attendance/', views.upload_attendance, name='upload_attendance'),
    path('attendance_list/', views.attendance_list, name='attendance_list'),
    path('student/<int:student_id>/', views.student_attendance, name='student_attendance'),
    path('live_attendance/', views.live_attendance, name='live_attendance'),
    path('process_live_frame/', views.process_live_frame, name='process_live_frame'),
    path('manage_students/', views.manage_students, name='manage_students'),
    path('edit_student/<int:student_id>/', views.edit_student, name='edit_student'),
    path('delete_student/<int:student_id>/', views.delete_student, name='delete_student'),
    path('manage_teachers/', views.manage_teachers, name='manage_teachers'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('change_password/', views.change_password, name='change_password'),
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),
]
