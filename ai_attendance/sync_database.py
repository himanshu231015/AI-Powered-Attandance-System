import os
import django
import sys
from pathlib import Path

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_attendance.settings')
django.setup()

from django.conf import settings
from django.contrib.auth.models import User
from core.models import Student
from core.utils import train_model

def sync_students():
    print("Syncing students from dataset...")
    dataset_dir = settings.DATASET_DIR
    
    if not os.path.exists(dataset_dir):
        print(f"Dataset directory not found: {dataset_dir}")
        return

    # Iterate over folders in dataset directory
    for folder_name in os.listdir(dataset_dir):
        folder_path = os.path.join(dataset_dir, folder_name)
        
        if os.path.isdir(folder_path):
            # Folder name format is expected to be "RollNumber_Name"
            parts = folder_name.split('_')
            if len(parts) >= 2:
                roll_number = parts[0]
                name = '_'.join(parts[1:]) # Join rest as name
                
                # Check if student exists
                student, created = Student.objects.get_or_create(
                    roll_number=roll_number,
                    defaults={'name': name}
                )
                
                if created:
                    print(f"Created Student: {name} ({roll_number})")
                else:
                    print(f"Student exists: {name} ({roll_number})")
                
                # Ensure User exists
                if not student.user:
                    if not User.objects.filter(username=roll_number).exists():
                        user = User.objects.create_user(username=roll_number, password=roll_number)
                        print(f"  Created User account for {roll_number}")
                    else:
                        user = User.objects.get(username=roll_number)
                        print(f"  Linked existing User account for {roll_number}")
                    
                    student.user = user
                    student.save()
            else:
                print(f"Skipping invalid folder name: {folder_name}")

    print("Sync complete.")
    
    # Retrain model
    print("Retraining model...")
    train_model()
    print("Model retrained successfully.")

if __name__ == '__main__':
    sync_students()
