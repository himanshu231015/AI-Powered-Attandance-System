from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate
from .models import Student, AttendanceRecord, TimeTable
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

def upload_attendance(request):
    if request.method == 'POST' and request.FILES.get('class_image'):
        image = request.FILES['class_image']
        fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads'), base_url='/media/uploads/')
        filename = fs.save(image.name, image)
        file_path = fs.path(filename)
        
        predictions = identify_faces(file_path)
        
        marked_count = 0
        unknown_count = 0
        
        checked_rolls = set()
        final_predictions = []
        
        for pred in predictions:
            roll_number = pred['roll_number']
            if roll_number:
                # Deduplication: Check if we already processed this student in this frame
                if roll_number in checked_rolls:
                    # Skip duplicate entirely
                    continue
                
                checked_rolls.add(roll_number)
                
                try:
                    student = Student.objects.get(roll_number=roll_number)
                    # Mark attendance with 1-hour Cooldown Logic
                    
                    # Check last attendance
                    last_attendance = AttendanceRecord.objects.filter(student=student).order_by('-date', '-time').first()
                    can_mark = True
                    status_text = "Marked Present"
                    
                    if last_attendance:
                        # Combine date and time to get full datetime (Assuming stored in UTC if USE_TZ=True)
                        # We need to make it aware. Since DB stores in UTC with USE_TZ=True, we interpret as UTC.
                        from django.utils import timezone
                        import datetime
                        
                        last_datetime_naive = datetime.datetime.combine(last_attendance.date, last_attendance.time)
                        # Make it aware (UTC)
                        last_datetime = timezone.make_aware(last_datetime_naive, datetime.timezone.utc)
                        
                        time_diff = timezone.now() - last_datetime
                        if time_diff.total_seconds() < 3600:
                            can_mark = False
                            status_text = f"Already Marked ({int(time_diff.total_seconds() // 60)}m ago)"
                    
                    if can_mark:
                         AttendanceRecord.objects.create(student=student)
                         marked_count += 1
                         
                    # Inject status into prediction object for template display
                    pred['status'] = status_text
                    
                except Student.DoesNotExist:
                    print(f"DEBUG: Student with roll number {roll_number} not found in DB.")
                    pred['status'] = 'Student Not Found'
                    pass
            else:
                unknown_count += 1
                pred['status'] = 'Unknown'
            
            final_predictions.append(pred)
                
        messages.success(request, f"Attendance marked for {marked_count} students. {unknown_count} unknown faces.")
        return render(request, 'attendance_result.html', {'predictions': final_predictions, 'image_url': fs.url(filename)})
        
    return render(request, 'upload_attendance.html')

def attendance_list(request):
    records = AttendanceRecord.objects.all().order_by('-date', '-time')
    return render(request, 'attendance_list.html', {'records': records})

def student_attendance(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    records = AttendanceRecord.objects.filter(student=student).order_by('-date')
    return render(request, 'student_attendance.html', {'student': student, 'records': records})

def live_attendance(request):
    return render(request, 'live_attendance.html')

@csrf_exempt
def process_live_frame(request):
    import cv2
    import numpy as np
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            image_data = data.get('image')
            
            print("Received live frame request")
            
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
                            # Cooldown Logic: Check last attendance for this student
                            last_attendance = AttendanceRecord.objects.filter(student=student).order_by('-date', '-time').first()
                            
                            can_mark = True
                            if last_attendance:
                                from django.utils import timezone
                                import datetime
                                # Combine date and time to get full datetime
                                last_datetime_naive = datetime.datetime.combine(last_attendance.date, last_attendance.time)
                                # Make it aware (UTC)
                                last_datetime = timezone.make_aware(last_datetime_naive, datetime.timezone.utc)
                                
                                time_diff = timezone.now() - last_datetime
                                
                                # Check if less than 1 hour (3600 seconds)
                                if time_diff.total_seconds() < 3600:
                                    can_mark = False
                                    status_msg = f"Already Marked ({int(time_diff.total_seconds() // 60)}m ago)"
                            
                            if can_mark:
                                try:
                                    AttendanceRecord.objects.create(student=student, subject=current_subject)
                                    status_msg = f"Marked Present ({current_subject})"
                                except Exception as e:
                                     # Likely IntegrityError
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
        images = request.FILES.getlist('images')
        
        if Student.objects.filter(roll_number=roll_number).exists():
            messages.error(request, "Student with this Roll Number already exists.")
            return redirect('add_student')
            
        # Create User for student
        try:
            user = User.objects.create_user(username=roll_number, password=roll_number)
            student = Student.objects.create(name=name, roll_number=roll_number, user=user, plain_password=roll_number)
        except Exception as e:
            messages.error(request, f"Error creating user: {e}")
            return redirect('add_student')
        
        # Create folder
        folder_name = f"{roll_number}_{name}"
        save_dir = os.path.join(settings.DATASET_DIR, folder_name)
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

@user_passes_test(lambda u: u.is_superuser)
def manage_students(request):
    students = Student.objects.all().order_by('-created_at')
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
    
    # Simple projection logic (placeholder)
    weekly_classes_count = TimeTable.objects.count() # This is total slots, maybe filter by student's dept/year if applicable
    projected_attendance = current_attendance_count # Just a placeholder
    
    records = AttendanceRecord.objects.filter(student=student).order_by('-date', '-time')[:10]
    
    context = {
        'student': student,
        'current_attendance_count': current_attendance_count,
        'weekly_classes_count': weekly_classes_count,
        'projected_attendance': projected_attendance,
        'records': records,
    }
    return render(request, 'student_portal/dashboard.html', context)
