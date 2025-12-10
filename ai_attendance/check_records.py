import os
import django
import sys

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_attendance.settings')
django.setup()

from core.models import AttendanceRecord, Student

def check_records():
    student = Student.objects.first()
    if not student:
        print("No students found.")
        return

    print(f"Checking records for student: {student.name} ({student.roll_number})")
    records = AttendanceRecord.objects.filter(student=student).order_by('-date', '-time')
    
    if not records.exists():
        print("No records found.")
    
    for r in records[:10]:
        print(f"Date: {r.date}, Subject: {r.subject}, Status: '{r.status}'")

if __name__ == "__main__":
    check_records()
