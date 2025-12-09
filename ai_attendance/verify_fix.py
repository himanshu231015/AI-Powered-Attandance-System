import os
import sys
import django
import cv2
import numpy as np
from django.conf import settings

# Setup Django environment
sys.path.append(r'c:\Users\himan\Documents\05-College\AI Powered Attandance System\AI Powered Attandance System\ai_attendance')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_attendance.settings')
django.setup()

from core.utils import identify_faces

def test_identify_faces():
    print("Testing identify_faces...")
    
    # Create a dummy image (black image) just to check for runtime errors
    # A black image will have 0 faces, so it should return [] but trigger the logic chains
    img = np.zeros((500, 500, 3), dtype=np.uint8)
    
    # We can't easily mock return values of face_recognition without mocking libraries,
    # but we can ensure the function runs through the merging logic if we simulate it or just let it run.
    # For now, let's just ensure it DOES NOT CRASH.
    
    try:
        predictions = identify_faces(image_content=img)
        print(f"Success! Result: {predictions}")
        print("Function executed without crashing.")
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_identify_faces()
