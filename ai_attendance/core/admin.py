from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Student, TimeTable, AttendanceRecord, Teacher

class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'roll_number', 'department', 'email', 'phone_number')
    search_fields = ('name', 'roll_number', 'email')
    list_filter = ('department',)

class TimeTableAdmin(admin.ModelAdmin):
    list_display = ('day', 'start_time', 'end_time', 'subject')
    list_filter = ('day',)

class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'time', 'status', 'subject')
    list_filter = ('date', 'status', 'subject')
    search_fields = ('student__name', 'student__roll_number')

class TeacherAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # We can filter if we strongly enforce teachers are staff/superusers or 
        # just rely on the proxy model usage. The proxy model itself doesn't automatically filter 
        # unless we override the manager, but for admin registration purposes 
        # it creates a separate section.
        # Ideally, we might want to filter only users that are teachers, but for now
        # since we don't have a specific "is_teacher" flag other than maybe is_superuser/is_staff
        # or group membership, we will display all users but under the label "Teachers"
        # to allow creating new ones easily.
        return qs

admin.site.register(Student, StudentAdmin)
admin.site.register(TimeTable, TimeTableAdmin)
admin.site.register(AttendanceRecord, AttendanceRecordAdmin)
admin.site.register(Teacher, TeacherAdmin)
