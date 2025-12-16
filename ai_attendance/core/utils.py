import os
import pickle
import numpy as np
from django.conf import settings
import datetime
from django.utils import timezone
from .models import Student, AttendanceRecord, TeacherSubject, TimeTable

def get_existing_attendance_record(student, subject, date, ref_time=None):
    """
    Finds an existing attendance record for the student/subject/date 
    that matches the lecture slot covering ref_time, or a fall-back window.
    Params:
    - student: Student object
    - subject: Subject name (string)
    - date: datetime.date object
    - ref_time: datetime.time object (marking time). Defaults to now.
    """
    if ref_time is None:
        ref_time = datetime.datetime.now().time()

    # 1. Try to find the Class Slot (TeacherSubject or TimeTable)
    # Convert date to weekday (0=Mon, 6=Sun)
    weekday = date.weekday()
    
    # Check TeacherSubject first (Assigned Classes)
    # Find a class for this subject on this day where ref_time is close to start/end
    # We'll consider a "Slot" relevant if marking happens between Start-45min and End+45min
    
    # We need to filter by subject matching.
    # Note: Subject names might be loose, but we'll try exact first.
    
    matched_slot = None
    
    # Logic: Look for any slot for this subject on this day
    # Then see if ref_time is "within range" of that slot.
    
    slots = TeacherSubject.objects.filter(subject__iexact=subject, day=weekday)
    if not slots.exists():
        # Fallback to TimeTable
        slots = TimeTable.objects.filter(subject__iexact=subject, day=weekday)
        
    for slot in slots:
        if slot.start_time and slot.end_time:
            # Create full datetimes for comparison
            # Handle crossing midnight? Unlikely for classes, but safe to assume same day.
            
            start_dt = datetime.datetime.combine(date, slot.start_time)
            end_dt = datetime.datetime.combine(date, slot.end_time)
            
            # Add buffers
            window_start = start_dt - datetime.timedelta(minutes=45)
            window_end = end_dt + datetime.timedelta(minutes=45)
            
            check_dt = datetime.datetime.combine(date, ref_time)
            
            if window_start <= check_dt <= window_end:
                matched_slot = slot
                break
    
    # Query for existing records for this student, subject, date
    existing_records = AttendanceRecord.objects.filter(student=student, subject__iexact=subject, date=date)
    
    if matched_slot:
        # If we found a slot, we want ANY record that corresponds to this slot.
        # i.e., any record whose 'time' is also within this slot's window.
        
        start_dt = datetime.datetime.combine(date, matched_slot.start_time)
        end_dt = datetime.datetime.combine(date, matched_slot.end_time)
        window_start = start_dt - datetime.timedelta(minutes=45)
        window_end = end_dt + datetime.timedelta(minutes=45)
        
        for record in existing_records:
            # Check if record time is in window
            record_dt = datetime.datetime.combine(record.date, record.time)
            if window_start <= record_dt <= window_end:
                return record
                
    else:
        # No slot found (e.g. extra class, different time, or no schedule).
        # Fallback to pure time window (e.g. +/- 60 mins from ref_time)
        # Check against ref_time
        
        check_dt = datetime.datetime.combine(date, ref_time)
        window_start = check_dt - datetime.timedelta(minutes=60)
        window_end = check_dt + datetime.timedelta(minutes=60)
        
        for record in existing_records:
            record_dt = datetime.datetime.combine(record.date, record.time)
            if window_start <= record_dt <= window_end:
                return record
                
    return None

def train_model():
    import face_recognition
    from sklearn import neighbors
    dataset_dir = settings.DATASET_DIR
    model_path = settings.MODEL_PATH
    cache_path = os.path.join(settings.BASE_DIR, 'encodings_cache.pkl')
    
    X = []
    y = []
    
    # Load cache
    # Format: {'relative_path': encoding}
    encodings_cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                encodings_cache = pickle.load(f)
            print(f"Loaded {len(encodings_cache)} cached encodings.")
        except Exception as e:
            print(f"Error loading cache: {e}")
            encodings_cache = {}

    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
        
    active_files = set()
    new_encodings_count = 0
        
    for root, dirs, files in os.walk(dataset_dir):
        for person_name in dirs:
            # Check if this directory name looks like a student folder (Roll_Name)
            if '_' not in person_name:
                continue
                
            try:
                roll_number = person_name.split('_')[0]
                # Basic validation that roll_number is likely valid (alphanumeric)
                if not roll_number.isalnum():
                     continue
            except IndexError:
                continue
            
            person_dir = os.path.join(root, person_name)
            
            # Check if this folder contains images (to ensure it's a leaf/student folder)
            has_images = False
            for f in os.listdir(person_dir):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    has_images = True
                    break
            
            if not has_images:
                continue
            
            # It's a valid student folder
            print(f"Processing student folder: {person_name}") 
            
            for image_name in os.listdir(person_dir):
                image_path = os.path.join(person_dir, image_name)
                # Use relative path as key to be safe against directory moves if root changes, 
                # though absolute is easier. Let's use relative to dataset_dir.
                rel_path = os.path.relpath(image_path, dataset_dir)
                
                # Skip non-image files
                if not image_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                
                active_files.add(rel_path)
                    
                if rel_path in encodings_cache:
                    X.append(encodings_cache[rel_path])
                    y.append(roll_number)
                else:
                    try:
                        image = face_recognition.load_image_file(image_path)
                        face_encodings = face_recognition.face_encodings(image)
                        
                        if len(face_encodings) > 0:
                            encoding = face_encodings[0]
                            X.append(encoding)
                            y.append(roll_number)
                            encodings_cache[rel_path] = encoding
                            new_encodings_count += 1
                    except Exception as e:
                        print(f"Error processing {image_path}: {e}")
    
    # Check if we have data
    if not X:
        return False, "No face data found in dataset."

    # Cache Cleanup: Remove files that no longer exist
    # We create a new dict to avoid modifying while iterating or just use dict comprehension
    # But we want to keep the valid ones we just used. A simple way is to trust 'active_files'.
    # Note: If a file existed but failed processing, it won't be in X/y but also not in cache, so safe.
    # If a file was in cache but now deleted from disk, it won't be in 'active_files'.
    clean_cache = {k: v for k, v in encodings_cache.items() if k in active_files}
    
    # Save cache
    try:
        with open(cache_path, 'wb') as f:
            pickle.dump(clean_cache, f)
        print(f"Cache updated. New: {new_encodings_count}, Total Cached: {len(clean_cache)}")
    except Exception as e:
        print(f"Error saving cache: {e}")
        
    # Train KNN
    n_neighbors = int(round(np.sqrt(len(X))))
    if n_neighbors < 1:
        n_neighbors = 1
        
    knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm='ball_tree', weights='distance')
    knn_clf.fit(X, y)
    
    # Save model
    with open(model_path, 'wb') as f:
        pickle.dump(knn_clf, f)
        
    return True, f"Model updated! Processed {new_encodings_count} new images. Total faces: {len(X)}."

def identify_faces(image_path=None, image_content=None):
    import face_recognition
    import cv2
    
    model_path = settings.MODEL_PATH
    if not os.path.exists(model_path):
        return []
        
    print(f"Loading model from {model_path}")
    with open(model_path, 'rb') as f:
        knn_clf = pickle.load(f)
        
    if image_content is not None:
        image = image_content
    else:
        image = face_recognition.load_image_file(image_path)
    
    print("Detecting face locations with HOG...")
    # 1. HOG Detection (face_recognition defaults)
    hog_face_locations = face_recognition.face_locations(image)
    print(f"HOG found {len(hog_face_locations)} faces")

    # 2. Haar Cascade Detection
    print("Detecting face locations with Haar Cascade...")
    try:
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
        
        # Lower scaleFactor for more detail, lowered minNeighbors for more sensitivity
        # RELAXED minNeighbors to 5 (balanced) - 4 was too loose (ghosts), 12 too strict (misses)
        haar_faces_rects = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        
        haar_face_locations = []
        for (x, y, w, h) in haar_faces_rects:
            # Convert (x, y, w, h) to (top, right, bottom, left)
            # top = y, right = x+w, bottom = y+h, left = x
            haar_face_locations.append((y, x + w, y + h, x))
            
        print(f"Haar found {len(haar_face_locations)} faces")
    except Exception as e:
        print(f"Haar Cascade error: {e}")
        haar_face_locations = []

    # 3. Merge Detections (Avoid duplicates)
    final_face_locations = list(hog_face_locations)
    
    def calculate_iou(boxA, boxB):
        # determine the (x, y)-coordinates of the intersection rectangle
        # box: (top, right, bottom, left)
        # Convert to (x1, y1, x2, y2) where x1=left, y1=top, x2=right, y2=bottom
        
        # boxA
        tA, rA, bA, lA = boxA
        # boxB
        tB, rB, bB, lB = boxB
        
        xA = max(lA, lB)
        yA = max(tA, tB)
        xB = min(rA, rB)
        yB = min(bA, bB)
        
        # compute the area of intersection rectangle
        interArea = max(0, xB - xA) * max(0, yB - yA)
        
        # compute the area of both the prediction and ground-truth rectangles
        boxAArea = (rA - lA) * (bA - tA)
        boxBArea = (rB - lB) * (bB - tB)
        
        # compute the intersection over union
        iou = interArea / float(boxAArea + boxBArea - interArea)
        return iou

    for h_loc in haar_face_locations:
        is_duplicate = False
        for existing_loc in final_face_locations:
            iou = calculate_iou(h_loc, existing_loc)
            if iou > 0.3: # Threshold for overlap
                is_duplicate = True
                break
        
        if not is_duplicate:
            final_face_locations.append(h_loc)
            
    print(f"DEBUG: Total unique faces found: {len(final_face_locations)}")
    
    if len(final_face_locations) == 0:
        print("DEBUG: No faces found.")
        return []
        
    faces_encodings = face_recognition.face_encodings(image, known_face_locations=final_face_locations)
    print(f"DEBUG: Encodings generated: {len(faces_encodings)}")
    
    # If using Haar, sometimes faces are not clear enough for encodings to return valid data corresponding to locs?
    # face_encodings returns a list of len(known_face_locations). If it can't encode, does it skip?
    # Documentation says: "If known_face_locations is None, ... If known_face_locations is not None, returns a list of encodings for each face location."
    # So lists should match length.
    
    print("Finding closest neighbors...")
    # Handle case where we have locations but maybe encoding failed for some reason (rare but possible if image is tiny)
    if len(faces_encodings) == 0:
         return []

    closest_distances = knn_clf.kneighbors(faces_encodings, n_neighbors=1)
    
    # Tightened to 0.60 to avoid false positives (0.65 was too loose)
    threshold = 0.60
    are_matches = [closest_distances[0][i][0] <= threshold for i in range(len(faces_encodings))]
    
    predictions = []
    distances = closest_distances[0]
    
    for i, (pred, loc, rec, dist) in enumerate(zip(knn_clf.predict(faces_encodings), final_face_locations, are_matches, distances)):
        distance_val = round(dist[0], 2)
        if rec:
            roll_number = pred
            try:
                student = Student.objects.get(roll_number=roll_number)
                # Show score in UI for user feedback
                name = f"{student.name} ({distance_val})"
            except Student.DoesNotExist:
                name = "Unknown"
                roll_number = None
        else:
            name = f"Unknown (Dist: {distance_val})"
            roll_number = None
            
        predictions.append({'name': name, 'roll_number': roll_number, 'location': loc, 'distance': distance_val})
        
    return predictions

def detect_and_crop_face(image_path, save_dir, student_name_roll):
    import cv2
    import face_recognition
    """
    Detects faces in the image, crops the largest face, and saves it to save_dir.
    Returns True if a face was found and saved.
    """
    image = cv2.imread(image_path)
    if image is None:
        return False
        
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_image)
    
    if not face_locations:
        return False
        
    # Find largest face
    # location is (top, right, bottom, left)
    # Area = (bottom - top) * (right - left)
    largest_face = max(face_locations, key=lambda f: (f[2] - f[0]) * (f[1] - f[3]))
    top, right, bottom, left = largest_face
    
    # Add some padding
    height, width, _ = image.shape
    padding = 20
    top = max(0, top - padding)
    bottom = min(height, bottom + padding)
    left = max(0, left - padding)
    right = min(width, right + padding)
    
    face_image = image[top:bottom, left:right]
    
    # Generate filename
    # Count existing files
    existing_files = len(os.listdir(save_dir))
    filename = f"face_{existing_files + 1:02d}.jpg"
    save_path = os.path.join(save_dir, filename)
    
    cv2.imwrite(save_path, face_image)
    return True
