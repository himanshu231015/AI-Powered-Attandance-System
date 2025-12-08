import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_attendance.settings')
django.setup()

from django.contrib import admin
from core.models import Student, TimeTable, AttendanceRecord, Teacher

def verify():
    registered_models = admin.site._registry.keys()
    
    expected_models = [Student, TimeTable, AttendanceRecord, Teacher]
    all_registered = True
    
    print("Checking Admin Registry...")
    for model in expected_models:
        if model in registered_models:
            print(f"[PASS] {model.__name__} is registered.")
        else:
            print(f"[FAIL] {model.__name__} is NOT registered.")
            all_registered = False
            
    if all_registered:
        print("\nSUCCESS: All expected models are registered in the Admin.")
    else:
        print("\nFAILURE: Some models are missing from the Admin.")

if __name__ == '__main__':
    verify()
