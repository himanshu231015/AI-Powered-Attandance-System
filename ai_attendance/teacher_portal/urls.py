from django.urls import path
from . import views

urlpatterns = [
    path('', views.teacher_dashboard, name='teacher_dashboard'),
    path('add_timetable/', views.add_timetable, name='add_timetable'),
    path('upload_timetable/', views.upload_timetable, name='upload_timetable'),
]
