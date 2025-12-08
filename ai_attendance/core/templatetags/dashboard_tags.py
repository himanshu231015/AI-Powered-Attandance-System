from django import template
from django.contrib.auth.models import User
from core.models import Student, AttendanceRecord

register = template.Library()

@register.inclusion_tag('includes/dashboard_stats.html')
def get_dashboard_stats():
    total_students = Student.objects.count()
    total_teachers = User.objects.filter(is_staff=True, is_superuser=False).count()
    total_attendance = AttendanceRecord.objects.count()
    
    return {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_attendance': total_attendance,
    }
