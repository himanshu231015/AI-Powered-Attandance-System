from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Student, TimeTable, AttendanceRecord, Teacher

from django import forms
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.contrib import messages
import os
from .utils import detect_and_crop_face, train_model

class MultipleFileInput(forms.ClearableFileInput): 
    # Or inherit from FileInput if Clearable is problematic, 
    # but Clearable is standard for ModelForm.
    # To fix ValueError "ClearableFileInput doesn't support uploading multiple files",
    # we must set this flag.
    allow_multiple_selected = True

class StudentAdminForm(forms.ModelForm):
    photos = forms.FileField(
        widget=MultipleFileInput(attrs={'multiple': True}),
        label='Upload Photos',
        required=False,
        help_text='Select at least 5 photos for training.'
    )

    class Meta:
        model = Student
        fields = '__all__'
        exclude = ('user',) # Hide user field as it's auto-created

class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm
    list_display = ('name', 'roll_number', 'department', 'email', 'phone_number')
    search_fields = ('name', 'roll_number', 'email')
    list_filter = ('department',)

    def save_model(self, request, obj, form, change):
        # Create User if not exists (only for new students)
        if not change and not obj.user:
            try:
                if not User.objects.filter(username=obj.roll_number).exists():
                    user = User.objects.create_user(username=obj.roll_number, password=obj.roll_number)
                    obj.user = user
                else:
                    # Link to existing user if found but not linked?
                    # Or just warn? For now, try to get existing
                    obj.user = User.objects.get(username=obj.roll_number)
            except Exception as e:
                messages.error(request, f"Error creating linked User: {e}")

        super().save_model(request, obj, form, change)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['is_multipart'] = True
        return super().add_view(request, form_url, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['is_multipart'] = True
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        print(f"DEBUG: request.FILES keys: {request.FILES.keys()}")
        photos = request.FILES.getlist('photos')
        print(f"DEBUG: photos list: {photos}")
        
        if photos:
            try:
                folder_name = f"{obj.roll_number}_{obj.name}"
                save_dir = os.path.join(settings.DATASET_DIR, folder_name)
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                
                fs = FileSystemStorage()
                count = 0
                for img in photos:
                    # Save temp
                    filename = fs.save(img.name, img)
                    temp_path = fs.path(filename)
                    
                    if detect_and_crop_face(temp_path, save_dir, folder_name):
                        count += 1
                    
                    # Delete temp
                    fs.delete(filename)
                
                if count > 0:
                    messages.success(request, f"Successfully processed {count} face images for {obj.name}.")
                    
                    # Train model after adding new images
                    success, msg = train_model()
                    if success:
                        messages.success(request, msg)
                    else:
                        messages.warning(request, f"Model training warning: {msg}")
                        
                else:
                    messages.warning(request, "No faces detected in uploaded photos. Please try again with clear photos.")
                    
            except Exception as e:
                messages.error(request, f"Error processing photos: {e}")

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

from .models import Admin
class AdminAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_superuser')
    
    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_superuser=True)

    def save_model(self, request, obj, form, change):
        obj.is_staff = True
        obj.is_superuser = True
        super().save_model(request, obj, form, change)

admin.site.register(Admin, AdminAdmin)
