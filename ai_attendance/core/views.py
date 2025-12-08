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
import base64

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
        
        for pred in predictions:
            if pred['roll_number']:
                try:
                    student = Student.objects.get(roll_number=pred['roll_number'])
                    # Mark attendance
                    today = datetime.date.today()
                    if not AttendanceRecord.objects.filter(student=student, date=today).exists():
                        AttendanceRecord.objects.create(student=student)
                        marked_count += 1
                except Student.DoesNotExist:
                    pass
            else:
                unknown_count += 1
                
        messages.success(request, f"Attendance marked for {marked_count} students. {unknown_count} unknown faces.")
        return render(request, 'attendance_result.html', {'predictions': predictions, 'image_url': fs.url(filename)})
        
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
            
            for pred in predictions:
                status_msg = ""
                if pred['roll_number']:
                    try:
                        student = Student.objects.get(roll_number=pred['roll_number'])
                        today = datetime.date.today()
                        
                        # Check if already marked for this subject today
                        # If subject is None/Extra Class, we might want to allow multiple? 
                        # For now, let's enforce unique per subject per day
                        
                        if not AttendanceRecord.objects.filter(student=student, date=today, subject=current_subject).exists():
                            AttendanceRecord.objects.create(student=student, subject=current_subject)
                            status_msg = f"Marked Present ({current_subject})"
                        else:
                            status_msg = f"Already Marked ({current_subject})"
                    except Student.DoesNotExist:
                        status_msg = "Student Not Found"
                else:
                    status_msg = "Unknown"
                
                results.append({
                    'name': pred['name'],
                    'roll_number': pred['roll_number'],
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
            return redirect('home')
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
            student = Student.objects.create(name=name, roll_number=roll_number, user=user)
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
        return redirect('home')
        
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
