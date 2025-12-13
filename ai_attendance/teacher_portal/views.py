from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from core.models import Student, AttendanceRecord, TimeTable, TeacherSubject
from django.contrib import messages
import datetime
import csv
import io

def is_teacher(user):
    return user.is_staff

@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    # Get assigned classes for the logged-in teacher
    assigned_classes = TeacherSubject.objects.filter(teacher=request.user)
    
    # Calculate counts
    total_classes_count = assigned_classes.count()
    total_students_count = Student.objects.count()
    
    # Filter handling
    selected_year = request.GET.get('year')
    selected_section = request.GET.get('section')
    
    if selected_year:
        assigned_classes = assigned_classes.filter(year=selected_year)
    if selected_section:
        assigned_classes = assigned_classes.filter(section=selected_section)

    return render(request, 'teacher_portal/dashboard.html', {
        'total_students_count': total_students_count,  # Fixed: changed from total_students
        'total_classes_count': total_classes_count,    # Fixed: added this
        'assigned_classes': assigned_classes,          # Fixed: passing filtered queryset
        'selected_year': selected_year,
        'selected_section': selected_section,
    })

@login_required
@user_passes_test(is_teacher)
def add_timetable(request):
    if request.method == 'POST':
        day = request.POST.get('day')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        subject = request.POST.get('subject')
        
        TimeTable.objects.create(
            day=day,
            start_time=start_time,
            end_time=end_time,
            subject=subject
        )
        messages.success(request, "Class added to timetable.")
        return redirect('teacher_dashboard')
        
    return render(request, 'teacher_portal/add_timetable.html')

@login_required
@user_passes_test(is_teacher)
def upload_timetable(request):
    if request.method == 'POST' and request.FILES.get('timetable_file'):
        csv_file = request.FILES['timetable_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a CSV file.")
            return redirect('upload_timetable')
            
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            count = 0
            for row in reader:
                # Expected columns: Day, Start Time, End Time, Subject
                # Day mapping: Monday=0, Sunday=6
                day_str = row.get('Day', '').strip().lower()
                day_map = {
                    'monday': 0, 'mon': 0, '0': 0,
                    'tuesday': 1, 'tue': 1, '1': 1,
                    'wednesday': 2, 'wed': 2, '2': 2,
                    'thursday': 3, 'thu': 3, '3': 3,
                    'friday': 4, 'fri': 4, '4': 4,
                    'saturday': 5, 'sat': 5, '5': 5,
                    'sunday': 6, 'sun': 6, '6': 6
                }
                
                day = day_map.get(day_str)
                if day is not None:
                    TimeTable.objects.create(
                        day=day,
                        start_time=row['Start Time'],
                        end_time=row['End Time'],
                        subject=row['Subject']
                    )
                    count += 1
                    
            messages.success(request, f"Successfully added {count} classes.")
            return redirect('teacher_dashboard')
            
        except Exception as e:
            messages.error(request, f"Error processing file: {e}")
            return redirect('upload_timetable')
    
    return render(request, 'teacher_portal/upload_timetable.html')
