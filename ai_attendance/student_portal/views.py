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
    current_attendance_count = records.count()
    weekly_classes_count = TimeTable.objects.count()
    projected_attendance = current_attendance_count + weekly_classes_count
    
    context = {
        'student': student, 
        'records': records,
        'current_attendance_count': current_attendance_count,
        'weekly_classes_count': weekly_classes_count,
        'projected_attendance': projected_attendance
    }
    
    return render(request, 'student_portal/dashboard.html', context)
