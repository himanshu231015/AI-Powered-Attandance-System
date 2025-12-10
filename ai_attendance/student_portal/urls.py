from django.urls import path
from core import views as core_views

urlpatterns = [
    path('', core_views.student_dashboard, name='student_dashboard'),
]
