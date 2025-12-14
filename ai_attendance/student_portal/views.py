from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.models import AttendanceRecord, Student, TimeTable

@login_required
def student_dashboard(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return render(request, 'error.html', {'message': 'You are not registered as a student.'})
        
    from django.contrib import messages

    if request.method == 'POST':
        student.email = request.POST.get('email')
        student.phone_number = request.POST.get('phone_number')
        student.address = request.POST.get('address')
        student.department = request.POST.get('department')
        dob = request.POST.get('date_of_birth')
        if dob:
            student.date_of_birth = dob
        student.save()
        messages.success(request, "Profile updated successfully.")
        
    records = AttendanceRecord.objects.filter(student=student).order_by('-date', '-time')
    
    # Calculate Statistics
    total_classes = records.count()
    present_count = records.filter(status='Present').count()
    
    overall_percentage = 0
    if total_classes > 0:
        overall_percentage = round((present_count / total_classes) * 100, 1)

    # Weekly classes (Estimate based on TimeTable)
    weekly_classes_count = TimeTable.objects.count()
    
    # Projections (Optimistic: "If I attend all future classes")
    # Next Week
    total_next_week = total_classes + weekly_classes_count
    present_next_week = present_count + weekly_classes_count
    prediction_week = round((present_next_week / total_next_week * 100) if total_next_week > 0 else 0, 1)
    
    # Next Month (4 Weeks)
    total_next_month = total_classes + (weekly_classes_count * 4)
    present_next_month = present_count + (weekly_classes_count * 4)
    prediction_month = round((present_next_month / total_next_month * 100) if total_next_month > 0 else 0, 1)
    
    # Subject Attendance
    subject_attendance = []
    subjects = records.values_list('subject', flat=True).distinct()
    for sub_name in subjects:
        if not sub_name: continue
        sub_records = records.filter(subject=sub_name)
        sub_total = sub_records.count()
        sub_present = sub_records.filter(status='Present').count()
        sub_pct = round((sub_present / sub_total * 100) if sub_total > 0 else 0, 1)
        subject_attendance.append({
            'subject': sub_name,
            'total': sub_total,
            'present': sub_present,
            'percentage': sub_pct
        })
    
    context = {
        'student': student, 
        'records': records,
        'current_attendance_count': present_count,
        'total_classes': total_classes,
        'overall_percentage': overall_percentage,
        'prediction_week': prediction_week,
        'prediction_month': prediction_month,
        'subject_attendance': subject_attendance,
        'weekly_classes_count': weekly_classes_count,
    }
    
    return render(request, 'student_portal/dashboard.html', context)
