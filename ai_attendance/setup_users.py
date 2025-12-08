import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_attendance.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Student

def setup():
    # Create Teacher (Superuser)
    if not User.objects.filter(username='teacher').exists():
        User.objects.create_superuser('teacher', 'teacher@example.com', 'teacher123')
        print("Created Teacher account: username='teacher', password='teacher123'")
    else:
        print("Teacher account already exists.")

    # Link existing students to users
    students = Student.objects.filter(user__isnull=True)
    for student in students:
        if not User.objects.filter(username=student.roll_number).exists():
            user = User.objects.create_user(username=student.roll_number, password=student.roll_number)
            student.user = user
            student.save()
            print(f"Created User for Student {student.name}: username='{student.roll_number}', password='{student.roll_number}'")
        else:
            print(f"User for {student.roll_number} already exists, linking...")
            user = User.objects.get(username=student.roll_number)
            student.user = user
            student.save()

if __name__ == '__main__':
    setup()
