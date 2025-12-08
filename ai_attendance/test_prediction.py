import os
import django
import sys
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_attendance.settings')
django.setup()

from core.utils import identify_faces

# Path to a test image
test_image_path = r"c:\Users\housh\Desktop\AI Powered Attandance System\database\dataset\231027_Vivek Kumar Choudhary\face_01.jpg"

print(f"Testing prediction on {test_image_path}")

if os.path.exists(test_image_path):
    try:
        predictions = identify_faces(image_path=test_image_path)
        print("Predictions:", predictions)
    except Exception as e:
        print(f"Error during prediction: {e}")
else:
    print("Test image not found.")
