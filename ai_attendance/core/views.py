from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from .models import Student, AttendanceRecord, TimeTable, TeacherSubject, Notification
from .utils import train_model, identify_faces, detect_and_crop_face
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.decorators import user_passes_test
import os
import datetime
import json
import base64
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser:
                return redirect('admin_dashboard')
            elif user.is_staff:
                return redirect('teacher_dashboard')
            else:
                return redirect('student_dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

def register(request):
    if request.method == 'POST':
        # Basic registration logic or redirect to login
        # Assuming student registration or similar.
        # For now, if code was lost, I'll provide a basic implementation 
        # that redirects to login or handles student creation if that was the intent.
        # Given the context, I will just render register.html if GET, 
        # and on POST maybe create a student/user?
        # Safe bet: If register.html exists, render it.
        pass 
    return render(request, 'register.html')


def index(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('admin_dashboard')
        elif request.user.is_staff:
            return redirect('teacher_dashboard')
        else:
            return redirect('student_dashboard')
    return redirect('login')

def home(request):
    total_students = Student.objects.count()
    total_attendance = AttendanceRecord.objects.count()
    return render(request, 'home.html', {'total_students': total_students, 'total_attendance': total_attendance})



def train(request):
    if request.method == 'POST':
        success, msg = train_model()
        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    return redirect('home')

@login_required
def upload_attendance(request):
    # Get params
    subject = request.GET.get('subject') or request.POST.get('subject')
    year = request.GET.get('year') or request.POST.get('year')
    section = request.GET.get('section') or request.POST.get('section')
    
    # 1. Security Check: Ensure Teacher is assigned to this Subject/Year
    if not request.user.is_superuser:
        if not TeacherSubject.objects.filter(teacher=request.user, subject=subject, year=year).exists():
             messages.error(request, "You are not authorized to mark attendance for this class.")
             return redirect('teacher_dashboard')

    if request.method == 'POST' and request.FILES.get('class_image'):
        image = request.FILES['class_image']
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads'), base_url='/media/uploads/')
        filename = fs.save(image.name, image)
        file_path = fs.path(filename)
        
        predictions = identify_faces(file_path)
        
        marked_count = 0
        unknown_count = 0
        absent_count = 0
        
        checked_rolls = set()
        present_roll_numbers = set()
        final_predictions = []
        
        today = datetime.date.today()
        
        # 1. Process Detected Faces (Mark Present)
        for pred in predictions:
            roll_number = pred['roll_number']
            if roll_number:
                present_roll_numbers.add(roll_number)
                
                # Deduplication: Check if we already processed this student in this frame
                if roll_number in checked_rolls:
                    continue
                
                checked_rolls.add(roll_number)
                
                try:
                    student = Student.objects.get(roll_number=roll_number)
                    
                    # Verify student belongs to this year/section
                    if year and str(student.year) != str(year):
                        pred['status'] = f"Wrong Year ({student.year})"
                        final_predictions.append(pred)
                        continue
                    if section and str(student.section).lower() != str(section).lower():
                        pred['status'] = f"Wrong Section ({student.section})"
                        final_predictions.append(pred)
                        continue
                        
                    status_text = "Marked Present"
                    if subject:
                         status_text += f" ({subject})"
                    
                    can_mark = True
                    
                    if subject:
                         # Time-based lookup for existing record (60 mins window)
                         cutoff_time = timezone.now() - datetime.timedelta(minutes=60)
                         records = AttendanceRecord.objects.filter(student=student, date=today, subject=subject).order_by('-time')
                         existing_record = None
                         for record in records:
                             dt_naive = datetime.datetime.combine(record.date, record.time)
                             if timezone.is_naive(dt_naive):
                                 dt_aware = timezone.make_aware(dt_naive, timezone.get_current_timezone())
                             else:
                                 dt_aware = dt_naive
                             if dt_aware > cutoff_time:
                                 existing_record = record
                                 break
                         
                         if existing_record:
                             if existing_record.status == 'Absent':
                                 existing_record.status = 'Present'
                                 # existing_record.time = timezone.now().time() # Don't update time, keep original slot time
                                 existing_record.save()
                                 status_text = f"Marked Present (Was Absent) - ({subject})"
                                 marked_count += 1
                                 can_mark = False # Handled update
                             else:
                                 can_mark = False
                                 status_text = f"Already Marked Present ({subject})"
                    else:
                        # Fallback Global Cooldown
                        last_attendance = AttendanceRecord.objects.filter(student=student).order_by('-date', '-time').first()
                        if last_attendance:
                            last_datetime_naive = datetime.datetime.combine(last_attendance.date, last_attendance.time)
                            if timezone.is_naive(last_datetime_naive):
                                last_datetime = timezone.make_aware(last_datetime_naive, timezone.get_current_timezone())
                            else:
                                last_datetime = last_datetime_naive
                                
                            time_diff = timezone.now() - last_datetime
                            if time_diff.total_seconds() < 3600 and last_attendance.status == 'Present':
                                can_mark = False
                                status_text = f"Already Marked ({int(time_diff.total_seconds() // 60)}m ago)"

                    if can_mark:
                         AttendanceRecord.objects.create(student=student, subject=subject, status='Present')
                         marked_count += 1
                         
                    pred['status'] = status_text
                    
                except Student.DoesNotExist:
                    print(f"DEBUG: Student with roll number {roll_number} not found in DB.")
                    pred['status'] = 'Student Not Found'
                    pass
            else:
                unknown_count += 1
                pred['status'] = 'Unknown'
            
            final_predictions.append(pred)

        # 2. Process Missing Students (Auto-Absent) - ONLY if Subject is defined (Class Mode)
        # CRITICAL FIX: Only fetch students for this specific YEAR (and section)
        if subject and year:
            filter_kwargs = {'year': year}
            if section:
                filter_kwargs['section'] = section
                
            class_students = Student.objects.filter(**filter_kwargs)
            
            for student in class_students:
                if student.roll_number not in present_roll_numbers:
                    # Check if recent record exists
                    recent_exists = False
                    cutoff_time = timezone.now() - datetime.timedelta(minutes=60)
                    recs = AttendanceRecord.objects.filter(student=student, date=today, subject=subject)
                    for r in recs:
                        dt_n = datetime.datetime.combine(r.date, r.time)
                        if timezone.is_naive(dt_n):
                            dt_a = timezone.make_aware(dt_n, timezone.get_current_timezone())
                        else:
                            dt_a = dt_n
                        if dt_a > cutoff_time:
                            recent_exists = True
                            break
                            
                    if not recent_exists:
                         AttendanceRecord.objects.create(student=student, subject=subject, status='Absent')
                         absent_count += 1
                
        messages.success(request, f"Present: {marked_count}, Absent: {absent_count}, Unknown: {unknown_count}")
        return render(request, 'attendance_result.html', {'predictions': final_predictions, 'image_url': fs.url(filename)})
        
    return render(request, 'upload_attendance.html', {'subject': subject, 'year': year, 'section': section})

def attendance_list(request):
    records = AttendanceRecord.objects.all().order_by('-date', '-time')
    return render(request, 'attendance_list.html', {'records': records})

def student_attendance(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    records = AttendanceRecord.objects.filter(student=student).order_by('-date')
    return render(request, 'student_attendance.html', {'student': student, 'records': records})

@login_required
def manual_attendance(request):
    subject_raw = request.GET.get('subject')
    subject = subject_raw.strip() if subject_raw else ''
    year = request.GET.get('year')
    section = request.GET.get('section')

    # Fetch students for this class
    students = Student.objects.none()
    if year:
        students = Student.objects.filter(year__icontains=year)
        if section:
            students = students.filter(section__icontains=section)
        students = students.order_by('roll_number')

    if request.method == 'POST':
        date_str = request.POST.get('date')
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "Invalid date format.")
            return redirect(request.path)
            
        # Get list of student IDs marked as present
        present_student_ids = request.POST.getlist('student_ids')
        
        count_present = 0
        count_absent = 0
        
        time_str = request.POST.get('time')
        current_time = datetime.datetime.now().time()
        
        if time_str:
            try:
                current_time = datetime.datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                pass # Fallback to now
        
        for student in students:
            is_present = str(student.id) in present_student_ids
            status = 'Present' if is_present else 'Absent'
            
            # Use specific time for lookup if provided, effectively disabling "cooldown" merging for different times
            # But if updating same slot, we should find it.
            # Logic: If record exists for this student + date + subject, check if time matches closely OR if it was just created (auto-now behavior prev).
            # With explicit time, we can be more strict. Let's look for record with same date and approx same time (e.g. within 5 mins) to allowing editing.
            
            cutoff_start = datetime.datetime.combine(date_obj, current_time) - datetime.timedelta(minutes=10)
            cutoff_end = datetime.datetime.combine(date_obj, current_time) + datetime.timedelta(minutes=10)
            
            # Naive/Aware handling
            if timezone.is_aware(timezone.now()):
                 cutoff_start = timezone.make_aware(cutoff_start)
                 cutoff_end = timezone.make_aware(cutoff_end)
                 
            possible_records = AttendanceRecord.objects.filter(student=student, date=date_obj, subject=subject).order_by('-time')
            record = None
            
            for r in possible_records:
                dt_naive = datetime.datetime.combine(r.date, r.time)
                if timezone.is_aware(timezone.now()):
                    dt_check = timezone.make_aware(dt_naive, timezone.get_current_timezone())
                else:
                    dt_check = dt_naive
                    
                # Loose check around the target time to allow editing
                # If naive comparison:
                if cutoff_start <= dt_check <= cutoff_end:
                    record = r
                    break

            if record:
                # Update existing
                record.status = status
                # Update time if beneficial, or keep original?
                # If we are "correcting" a record, we might keep time. If we are explicitly setting time, we set it.
                if time_str:
                     record.time = current_time
                record.save()
                create_notification(student, f"Attendance updated: {status} for {subject} on {date_obj} at {current_time.strftime('%H:%M')}")
            else:
                # Create new
                AttendanceRecord.objects.create(
                    student=student,
                    date=date_obj,
                    subject=subject,
                    status=status,
                    time=current_time
                )
                create_notification(student, f"Attendance marked: {status} for {subject} on {date_obj} at {current_time.strftime('%H:%M')}")
            
            if is_present:
                count_present += 1
            else:
                count_absent += 1
            
        messages.success(request, f"Attendance marked for {subject}: {count_present} Present, {count_absent} Absent.")
        return redirect('teacher_dashboard')


    today = datetime.date.today().strftime('%Y-%m-%d')
    default_time = request.GET.get('start_time', datetime.datetime.now().strftime('%H:%M'))
    
    # Check if attendance exists for this slot
    present_student_ids = []
    attendance_marked = False
    
    if default_time:
         try:
            query_time = datetime.datetime.strptime(default_time, '%H:%M').time()
            cutoff_start = datetime.datetime.combine(datetime.date.today(), query_time) - datetime.timedelta(minutes=20)
            cutoff_end = datetime.datetime.combine(datetime.date.today(), query_time) + datetime.timedelta(minutes=20)
            
            if timezone.is_aware(timezone.now()):
                 cutoff_start = timezone.make_aware(cutoff_start)
                 cutoff_end = timezone.make_aware(cutoff_end)
            
            existing_records = AttendanceRecord.objects.filter(
                subject=subject, 
                date=datetime.date.today()
            )
            
            # Filter in python or complex query for time range
            # Since we removed auto_now_add, we trust the time field more.
            # Let's find records in the window.
            matched_records = []
            for r in existing_records:
                dt_naive = datetime.datetime.combine(r.date, r.time)
                if timezone.is_aware(timezone.now()):
                    dt_check = timezone.make_aware(dt_naive, timezone.get_current_timezone())
                else:
                    dt_check = dt_naive
                
                if cutoff_start <= dt_check <= cutoff_end:
                    matched_records.append(r)
            
            if matched_records:
                attendance_marked = True
                for r in matched_records:
                    if r.status == 'Present':
                        present_student_ids.append(r.student.id)

         except ValueError:
             pass

    return render(request, 'manual_attendance.html', {
        'students': students, 
        'subject': subject, 
        'year': year, 
        'section': section,
        'today': today,
        'default_time': default_time,
        'attendance_marked': attendance_marked,
        'present_student_ids': present_student_ids,
    })

def live_attendance(request):
    subject = request.GET.get('subject')
    year = request.GET.get('year')
    section = request.GET.get('section')
    return render(request, 'live_attendance.html', {
        'subject': subject,
        'year': year,
        'section': section
    })

@csrf_exempt
def process_live_frame(request):
    import cv2
    import numpy as np
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image')
            
            # Get explicit class params
            req_subject = data.get('subject')
            req_year = data.get('year')
            req_section = data.get('section')
            
            print(f"Received live frame request. params: {req_subject}, {req_year}, {req_section}")
            
            if not image_data:
                print("No image data received")
                return JsonResponse({'status': 'error', 'message': 'No image data'})

            # Decode base64
            if ';base64,' in image_data:
                format, imgstr = image_data.split(';base64,') 
            else:
                imgstr = image_data

            try:
                data = base64.b64decode(imgstr)
            except Exception as e:
                print(f"Base64 decode error: {e}")
                return JsonResponse({'status': 'error', 'message': 'Invalid base64 data'})
            
            # Convert to numpy array
            nparr = np.frombuffer(data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                 print("Failed to decode image from numpy array")
                 return JsonResponse({'status': 'error', 'message': 'Failed to decode image'})

            # Convert BGR to RGB (face_recognition uses RGB)
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            print("Calling identify_faces...")
            predictions = identify_faces(image_content=rgb_img)
            print(f"Predictions: {predictions}")
            
            if req_subject:
                # Explicit mode
                current_subject = req_subject
            else:
                # TimeTable mode
                # Get current subject from timetable
                now = datetime.datetime.now()
                current_time = now.time()
                current_weekday = now.weekday()
                
                # Find active class
                # We filter for classes that started before now and end after now
                active_class = TimeTable.objects.filter(
                    day=current_weekday,
                    start_time__lte=current_time,
                    end_time__gte=current_time
                ).first()
                
                current_subject = active_class.subject if active_class else "Extra Class"

            # Mark attendance
            results = []
            
            # Deduplication for this frame
            req_time_str = data.get('start_time')
            
            # Default to now if not provided
            current_time = datetime.datetime.now().time()
            if req_time_str:
                try:
                    current_time = datetime.datetime.strptime(req_time_str, '%H:%M').time()
                except ValueError:
                    pass

            # ... decode image ... (omitted in tool, matching context below)

            # Mark attendance logic
            
            # Deduplication for this frame
            processed_rolls_in_frame = set()
            
            for pred in predictions:
                status_msg = ""
                roll_number = pred['roll_number']
                
                if roll_number:
                     # Check if we already processed this student in this frame
                    if roll_number in processed_rolls_in_frame:
                        continue # Skip duplicate
                    else:
                        processed_rolls_in_frame.add(roll_number)
                        try:
                            student = Student.objects.get(roll_number=roll_number)
                            
                            # Validate logic if year/section provided
                            if req_year:
                                if str(student.year) != str(req_year):
                                    continue # Skip wrong year
                            if req_section:
                                if str(student.section).lower() != str(req_section).lower():
                                    continue # Skip wrong section
                                    
                            can_mark = True
                            
                            if req_subject:
                                 # Explicit Subject Mode (Dashboard)
                                 # Use Window Logic (+/- 20 mins around current_time)
                                 # This allows marking 11:10 and 12:00 separately.
                                 
                                 cutoff_start = datetime.datetime.combine(datetime.date.today(), current_time) - datetime.timedelta(minutes=20)
                                 cutoff_end = datetime.datetime.combine(datetime.date.today(), current_time) + datetime.timedelta(minutes=20)
                                 
                                 if timezone.is_aware(timezone.now()):
                                     cutoff_start = timezone.make_aware(cutoff_start)
                                     cutoff_end = timezone.make_aware(cutoff_end)
                                     
                                 existing_records = AttendanceRecord.objects.filter(student=student, date=datetime.date.today(), subject=current_subject)
                                 
                                 for r in existing_records:
                                     dt_naive = datetime.datetime.combine(r.date, r.time)
                                     if timezone.is_aware(timezone.now()):
                                         dt_check = timezone.make_aware(dt_naive, timezone.get_current_timezone())
                                     else:
                                         dt_check = dt_naive
                                         
                                     if cutoff_start <= dt_check <= cutoff_end:
                                         can_mark = False
                                         status_msg = f"Already Marked ({current_time.strftime('%H:%M')})"
                                         break
                            else:
                                # Fallback / Timetable Mode (Auto-detect)
                                # Use Global Cooldown (1 hour) to prev spam
                                last_attendance = AttendanceRecord.objects.filter(student=student).order_by('-date', '-time').first()
                                if last_attendance:
                                    last_datetime_naive = datetime.datetime.combine(last_attendance.date, last_attendance.time)
                                    if timezone.is_aware(timezone.now()):
                                         last_datetime = timezone.make_aware(last_datetime_naive, datetime.timezone.utc)
                                    else:
                                         last_datetime = last_datetime_naive
                                    
                                    time_diff = timezone.now() - last_datetime
                                    if time_diff.total_seconds() < 3600:
                                        can_mark = False
                                        status_msg = f"Already Marked ({int(time_diff.total_seconds() // 60)}m ago)"
                            
                            if can_mark:
                                try:
                                    AttendanceRecord.objects.create(student=student, subject=current_subject, time=current_time)
                                    create_notification(student, f"Marked Present for {current_subject} via Face ID")
                                    status_msg = f"Marked Present ({current_subject})"
                                except Exception as e:
                                     status_msg = f"Already Marked Today ({current_subject})"
                                    
                        except Student.DoesNotExist:
                            status_msg = "Student Not Found"
                else:
                    status_msg = "Unknown"
                
                results.append({
                    'name': pred['name'],
                    'roll_number': roll_number,
                    'location': pred['location'],
                    'status': status_msg
                })
            
            return JsonResponse({'status': 'success', 'results': results})
            
        except Exception as e:
            print(f"Error in process_live_frame: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@user_passes_test(lambda u: u.is_superuser)
def add_teacher(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('add_teacher')
            
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_staff = True
            user.save()
            messages.success(request, f"Teacher {username} added successfully!")
            return redirect('admin_dashboard')
        except Exception as e:
            messages.error(request, f"Error adding teacher: {e}")
            return redirect('add_teacher')
            
    return render(request, 'add_teacher.html')

@user_passes_test(lambda u: u.is_superuser)
def add_student(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        roll_number = request.POST.get('roll_number')
        department = request.POST.get('department')
        year = request.POST.get('year')
        section = request.POST.get('section')
        images = request.FILES.getlist('images')
        
        if Student.objects.filter(roll_number=roll_number).exists():
            messages.error(request, "Student with this Roll Number already exists.")
            return redirect('add_student')
            
        # Create User for student
        try:
            user = User.objects.create_user(username=roll_number, password=roll_number)
            student = Student.objects.create(
                name=name, 
                roll_number=roll_number, 
                user=user, 
                plain_password=roll_number,
                department=department,
                year=year,
                section=section
            )
        except Exception as e:
            messages.error(request, f"Error creating user: {e}")
            return redirect('add_student')
        
        # Create folder with hierarchy: Branch/Year/Section/Roll_Name
        folder_name = f"{roll_number}_{name}"
        # Sanitize inputs to prevent path traversal or bad characters
        safe_dept = "".join([c for c in department if c.isalnum() or c in (' ', '_', '-')]).strip()
        safe_year = "".join([c for c in str(year) if c.isalnum()]).strip()
        safe_section = "".join([c for c in str(section) if c.isalnum()]).strip()
        
        save_dir = os.path.join(settings.DATASET_DIR, safe_dept, safe_year, safe_section, folder_name)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # Process images
        fs = FileSystemStorage()
        count = 0
        for img in images:
            # Save temp
            filename = fs.save(img.name, img)
            temp_path = fs.path(filename)
            
            if detect_and_crop_face(temp_path, save_dir, folder_name):
                count += 1
            
            # Delete temp
            fs.delete(filename)
            
        messages.success(request, f"Student added with {count} face images.")
        return redirect('admin_dashboard')
        
    return render(request, 'add_student.html')

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def download_attendance(request):
    import openpyxl
    from openpyxl.styles import Font
    from django.http import HttpResponse

    # Get filter parameters
    branch = request.GET.get('branch')
    year = request.GET.get('year')
    section = request.GET.get('section')

    # Fetch Data (Reuse logic)
    if branch and year and section:
        students = Student.objects.filter(
            department__icontains=branch,
            year__icontains=year,
            section__icontains=section
        ).order_by('roll_number')
    else:
        students = Student.objects.none()

    # Create Workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Attendance Report"

    # Headers
    headers = ['Roll Number', 'Name', 'Department', 'Year', 'Section', 'Total Classes', 'Present', 'Attendance %']
    ws.append(headers)

    # Style Header
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Determine if user is a teacher and filter subjects
    assigned_subjects = None
    if not request.user.is_superuser and request.user.is_staff:
        assigned_subjects = TeacherSubject.objects.filter(teacher=request.user).values_list('subject', flat=True)

    # Add Data
    for student in students:
        records = AttendanceRecord.objects.filter(student=student)
        if assigned_subjects is not None:
            records = records.filter(subject__in=assigned_subjects)
            
        total_classes = records.count()
        present_count = records.filter(status='Present').count()
        if total_classes > 0:
            percentage = round((present_count / total_classes) * 100, 1)
        else:
            percentage = 0
        
        ws.append([
            student.roll_number,
            student.name,
            student.department,
            student.year,
            student.section,
            total_classes,
            present_count,
            f"{percentage}%"
        ])

    # Create Response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Attendance_Report_{branch}_{year}_{section}.xlsx"'

    wb.save(response)
    return response

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def manage_students(request):
    # Get filter parameters
    branch = request.GET.get('branch')
    year = request.GET.get('year')
    section = request.GET.get('section')
    
    # Base QuerySet
    if branch and year and section:
         students = Student.objects.filter(
            department__icontains=branch,
            year__icontains=year,
            section__icontains=section
        ).order_by('roll_number')
    else:
        # Default behavior if no filter found
        if request.user.is_superuser:
            students = Student.objects.all().order_by('-created_at') # Admin sees all
        else:
            students = Student.objects.none() # Teacher sees none
            
    # Determine if user is a teacher and filter subjects
    assigned_subjects = None
    if not request.user.is_superuser and request.user.is_staff:
        assigned_subjects = TeacherSubject.objects.filter(teacher=request.user).values_list('subject', flat=True)

    # Calculate attendance for each student (common logic)
    for student in students:
        records = AttendanceRecord.objects.filter(student=student)
        if assigned_subjects is not None:
            records = records.filter(subject__in=assigned_subjects)
            
        total_classes = records.count()
        present_count = records.filter(status='Present').count()
        
        if total_classes > 0:
            percentage = round((present_count / total_classes) * 100, 1)
        else:
            percentage = 0
            
        student.attendance_percentage = percentage
        student.total_classes = total_classes
        student.present_count = present_count
        
    return render(request, 'manage_students.html', {'students': students})

@user_passes_test(lambda u: u.is_superuser)
def delete_student(request, student_id):
    if request.method == 'POST':
        student = get_object_or_404(Student, id=student_id)
        user = student.user
        name = student.name
        
        # Delete student folder if exists
        try:
            folder_name = f"{student.roll_number}_{student.name}"
            save_dir = os.path.join(settings.DATASET_DIR, folder_name)
            if os.path.exists(save_dir):
                import shutil
                shutil.rmtree(save_dir)
        except Exception as e:
            print(f"Error deleting folder: {e}")

        # Delete student (this cascades to attendance records)
        student.delete()
        
        # Delete associated user
        if user:
            user.delete()
            
        messages.success(request, f"Student {name} has been deleted successfully.")
        return redirect('manage_students')
    
    return redirect('manage_students')

@user_passes_test(lambda u: u.is_superuser)
def edit_student(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        roll_number = request.POST.get('roll_number')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        department = request.POST.get('department')
        year = request.POST.get('year')
        section = request.POST.get('section')
        password = request.POST.get('password')
        
        # Update fields
        student.name = name
        student.roll_number = roll_number
        student.email = email
        student.phone_number = phone_number
        student.department = department
        student.year = year
        student.section = section
        
        # Update password if provided
        if password:
            student.plain_password = password
            # Also update the User object if it exists
            if student.user:
                student.user.set_password(password)
                student.user.save()
        
        # Sync other details to User object if it exists
        if student.user:
            student.user.email = email
            student.user.first_name = name
            student.user.save()
        
        student.save()
        messages.success(request, f"Student {student.name} updated successfully.")
        return redirect('manage_students')
        
    return render(request, 'edit_student.html', {'student': student})

@user_passes_test(lambda u: u.is_superuser)
def manage_teachers(request):
    teachers = User.objects.filter(is_staff=True, is_superuser=False).order_by('-date_joined')
    return render(request, 'manage_teachers.html', {'teachers': teachers})
@user_passes_test(lambda u: u.is_superuser)
def admin_dashboard(request):
    total_students = Student.objects.count()
    total_teachers = User.objects.filter(is_staff=True, is_superuser=False).count()
    total_attendance = AttendanceRecord.objects.count()
    
    # Get recent attendance
    recent_attendance = AttendanceRecord.objects.all().order_by('-date', '-time')[:5]
    
    context = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_attendance': total_attendance,
        'recent_attendance': recent_attendance,
    }
    return render(request, 'admin_dashboard.html', context)

@login_required
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        try:
            user.save()
            messages.success(request, "Profile updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating profile: {e}")
        return redirect('profile')
        
    return render(request, 'profile.html', {'user': request.user})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            
            # Update plain password for display in admin dashboard
            if hasattr(user, 'student'):
                try:
                    student = user.student
                    student.plain_password = form.cleaned_data['new_password1']
                    student.save()
                    print(f"DEBUG: Updated plain_password for {student.roll_number} to {student.plain_password}")
                except Exception as e:
                    print(f"DEBUG: Error updating plain_password: {e}")
            else:
                 print(f"DEBUG: User {user.username} has no student profile.")
                
            messages.success(request, 'Your password was successfully updated!')
            # Redirect to appropriate dashboard based on role
            if user.is_superuser:
                return redirect('admin_dashboard')
            elif user.is_staff:
                return redirect('teacher_dashboard')
            else:
                return redirect('student_dashboard')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})

@login_required
def student_dashboard(request):
    if not hasattr(request.user, 'student'):
         # Fallback if user is not linked to a student profile
         return render(request, 'student_portal/dashboard.html', {'error': 'No student profile found.'})
    
    student = request.user.student
    
    # Handle Profile Update
    if request.method == 'POST':
        try:
            student.email = request.POST.get('email')
            student.phone_number = request.POST.get('phone_number')
            student.department = request.POST.get('department')
            student.address = request.POST.get('address')
            
            dob = request.POST.get('date_of_birth')
            if dob:
                student.date_of_birth = dob
            
            student.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('student_dashboard')
        except Exception as e:
            messages.error(request, f"Error updating profile: {e}")
    
    today = datetime.date.today()
    start_week = today - datetime.timedelta(days=today.weekday())
    end_week = start_week + datetime.timedelta(days=6)
    
    # Calculate attendance stats
    current_attendance_count = AttendanceRecord.objects.filter(student=student, status='Present').count()
    
    # Subject-wise Attendance Logic
    all_records = AttendanceRecord.objects.filter(student=student)
    subject_stats = {}
    
    for record in all_records:
        # Use subject from record, default to "General" if None
        subj = record.subject if record.subject else "General"
        
        if subj not in subject_stats:
            subject_stats[subj] = {'present': 0, 'total': 0}
            
        subject_stats[subj]['total'] += 1
        if record.status == 'Present':
            subject_stats[subj]['present'] += 1
            
    subject_attendance = []
    for subj, stats in subject_stats.items():
        total = stats['total']
        present = stats['present']
        percentage = (present / total * 100) if total > 0 else 0
        subject_attendance.append({
            'subject': subj,
            'present': present,
            'total': total,
            'percentage': round(percentage, 1)
        })
    
    # Overall Statistics
    total_classes = all_records.count()
    overall_percentage = (current_attendance_count / total_classes * 100) if total_classes > 0 else 0
    
    # Prediction Logic
    # Estimate weekly classes from Timetable count or default
    weekly_classes_count = TimeTable.objects.count()
    if weekly_classes_count == 0:
        weekly_classes_count = 15 # Default assumption if no timetable
        
    # Predict Next Week (Assuming full attendance)
    pred_week_present = current_attendance_count + weekly_classes_count
    pred_week_total = total_classes + weekly_classes_count
    pred_week_pct = (pred_week_present / pred_week_total * 100) if pred_week_total > 0 else 0
    
    # Predict Next Month (Assuming full attendance ~4 weeks)
    pred_month_present = current_attendance_count + (weekly_classes_count * 4)
    pred_month_total = total_classes + (weekly_classes_count * 4)
    pred_month_pct = (pred_month_present / pred_month_total * 100) if pred_month_total > 0 else 0

    records = AttendanceRecord.objects.filter(student=student).order_by('-date', '-time')[:10]
    
    context = {
        'student': student,
        'current_attendance_count': current_attendance_count,
        'total_classes': total_classes,
        'overall_percentage': round(overall_percentage, 1),
        'records': records,
        'subject_attendance': subject_attendance,
        'prediction_week': round(pred_week_pct, 1),
        'prediction_month': round(pred_month_pct, 1),
    }
    return render(request, 'student_portal/dashboard.html', context)

@login_required
def teacher_dashboard(request):
    # Fetch subjects assigned to this teacher
    today_weekday = datetime.datetime.now().weekday()
    assigned_classes = TeacherSubject.objects.filter(teacher=request.user, day=today_weekday)
    
    # Filter by Year
    year_query = request.GET.get('year')
    if year_query:
        assigned_classes = assigned_classes.filter(year__icontains=year_query)
        
    # Filter by Section
    section_query = request.GET.get('section')
    if section_query:
        assigned_classes = assigned_classes.filter(section__icontains=section_query)
        
    # Calculate Stats for Dashboard
    # Total assigned classes
    total_classes_count = assigned_classes.count()
    
    # Total students in relevant years/sections (Approximate)
    # Get set of (year, section) tuples
    class_specs = assigned_classes.values_list('year', 'section').distinct()
    
    total_students_count = 0
    relevant_students_ids = set()
    
    for year, section in class_specs:
        q = Student.objects.filter(year__icontains=year)
        if section:
            q = q.filter(section__icontains=section)
        ids = q.values_list('id', flat=True)
        relevant_students_ids.update(ids)
        
    total_students_count = len(relevant_students_ids)
    
    # Recent Attendance for these classes/students
    recent_attendance = AttendanceRecord.objects.filter(student__id__in=relevant_students_ids).order_by('-date', '-time')[:5]

    return render(request, 'teacher_dashboard.html', {
        'assigned_classes': assigned_classes,
        'selected_year': year_query, 
        'selected_section': section_query,
        'total_classes_count': total_classes_count,
        'total_students_count': total_students_count,
        'recent_attendance': recent_attendance,
        'user': request.user
    })

@user_passes_test(lambda u: u.is_superuser)
def manage_teacher_subjects(request):
    subjects = TeacherSubject.objects.all().order_by('teacher__username', 'day')
    return render(request, 'manage_teacher_subjects.html', {'subjects': subjects})

@user_passes_test(lambda u: u.is_superuser)
def assign_teacher_subject(request):
    teachers = User.objects.filter(is_staff=True, is_superuser=False)
    
    if request.method == 'POST':
        teacher_id = request.POST.get('teacher')
        subject = request.POST.get('subject')
        year = request.POST.get('year')
        section = request.POST.get('section')
        day = request.POST.get('day')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        # Convert empty strings to None
        if not start_time: start_time = None
        if not end_time: end_time = None
        
        try:
            teacher = User.objects.get(id=teacher_id)
            TeacherSubject.objects.create(
                teacher=teacher,
                subject=subject,
                year=year,
                section=section,
                day=day,
                start_time=start_time,
                end_time=end_time
            )
            messages.success(request, f"Assigned {subject} to {teacher.username} successfully.")
            return redirect('manage_teacher_subjects')
        except Exception as e:
            messages.error(request, f"Error assigning subject: {e}")
            
    days = TeacherSubject.DAYS_OF_WEEK
    return render(request, 'assign_teacher_subject.html', {'teachers': teachers, 'days': days})

@user_passes_test(lambda u: u.is_superuser)
def edit_teacher_subject(request, subject_id):
    subject_obj = get_object_or_404(TeacherSubject, id=subject_id)
    teachers = User.objects.filter(is_staff=True, is_superuser=False)
    
    if request.method == 'POST':
        try:
            teacher_id = request.POST.get('teacher')
            subject = request.POST.get('subject')
            year = request.POST.get('year')
            section = request.POST.get('section')
            day = request.POST.get('day')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            
            # Convert empty strings to None
            if not start_time: start_time = None
            if not end_time: end_time = None
            
            teacher = User.objects.get(id=teacher_id)
            
            # Update fields
            subject_obj.teacher = teacher
            subject_obj.subject = subject
            subject_obj.year = year
            subject_obj.section = section
            subject_obj.day = day
            subject_obj.start_time = start_time
            subject_obj.end_time = end_time
            subject_obj.save()
            
            messages.success(request, f"Updated assignment for {subject} successfully.")
            return redirect('manage_teacher_subjects')
        except Exception as e:
            messages.error(request, f"Error updating assignment: {e}")
            
    days = TeacherSubject.DAYS_OF_WEEK
    return render(request, 'edit_teacher_subject.html', {
        'submission': subject_obj,
        'teachers': teachers, 
        'days': days
    })

@user_passes_test(lambda u: u.is_superuser)
def delete_teacher_subject(request, subject_id):
    if request.method == 'POST':
        try:
            subject = TeacherSubject.objects.get(id=subject_id)
            name = subject.subject
            teacher = subject.teacher.username
            subject.delete()
            messages.success(request, f"Removed assignment: {name} from {teacher}")
        except TeacherSubject.DoesNotExist:
            messages.error(request, "Subject assignment not found.")
        except Exception as e:
            messages.error(request, f"Error deleting assignment: {e}")
            
    return redirect('manage_teacher_subjects')

# --- Notification Logic ---

def create_notification(student, message, notif_type='Attendance'):
    """Helper to create a notification for a student."""
    try:
        Notification.objects.create(
            recipient=student,
            message=message,
            notification_type=notif_type
        )
    except Exception as e:
        print(f"Error creating notification: {e}")

@login_required
def get_notifications(request):
    """API to fetch unread notifications for the logged-in student."""
    if hasattr(request.user, 'student'):
        student = request.user.student
        # Get unread notifications
        notifications = Notification.objects.filter(recipient=student, is_read=False)[:10]
        data = [{
            'id': n.id,
            'message': n.message,
            'created_at': n.created_at.strftime('%H:%M %d-%m'),
            'type': n.notification_type
        } for n in notifications]
        return JsonResponse({'status': 'success', 'notifications': data, 'count': len(data)})
    return JsonResponse({'status': 'error', 'message': 'Not a student'}, status=403)

@login_required
@csrf_exempt
def mark_notification_read(request, notif_id):
    """API to mark a notification as read."""
    if request.method == 'POST':
        try:
            notification = Notification.objects.get(id=notif_id, recipient__user=request.user)
            notification.is_read = True
            notification.save()
            return JsonResponse({'status': 'success'})
        except Notification.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
