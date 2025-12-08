import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_attendance.settings')
django.setup()

from core.models import Student
from django.contrib.auth.models import User

def verify_sync():
    print("Starting verification...")
    # Get or create a test student
    user, created = User.objects.get_or_create(username='test_sync_user', defaults={'password': 'old_password'})
    if not hasattr(user, 'student'):
        student = Student.objects.create(user=user, name="Test Sync", roll_number="TEST001", plain_password="old_password")
    else:
        student = user.student

    print(f"Initial State - Roll: {student.roll_number}, PlainPassword: {student.plain_password}")

    # Simulate the logic in change_password view
    new_password = "new_secure_password_999"
    print(f"Simulating password change to: {new_password}")
    
    student.plain_password = new_password
    student.save()
    
    # Reload from DB to confirm persistence
    student.refresh_from_db()
    print(f"Final State - PlainPassword in DB: {student.plain_password}")
    
    if student.plain_password == new_password:
        print("SUCCESS: Password synced correctly to DB.")
    else:
        print("FAILURE: Password mismatch.")

if __name__ == '__main__':
    verify_sync()
