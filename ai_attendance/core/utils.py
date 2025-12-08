import os
import pickle
import numpy as np
from django.conf import settings
from .models import Student

def train_model():
    import face_recognition
    from sklearn import neighbors
    dataset_dir = settings.DATASET_DIR
    model_path = settings.MODEL_PATH
    
    X = []
    y = []
    
    if not os.path.exists(dataset_dir):
        os.makedirs(dataset_dir)
        
    for person_name in os.listdir(dataset_dir):
        person_dir = os.path.join(dataset_dir, person_name)
        if not os.path.isdir(person_dir):
            continue
            
        # Extract roll number from folder name "Roll_Name"
        # Example: "1_Vivek" -> roll="1"
        try:
            roll_number = person_name.split('_')[0]
        except IndexError:
            continue 
            
        for image_name in os.listdir(person_dir):
            image_path = os.path.join(person_dir, image_name)
            # Skip non-image files
            if not image_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
                
            try:
                image = face_recognition.load_image_file(image_path)
                face_encodings = face_recognition.face_encodings(image)
                
                if len(face_encodings) > 0:
                    X.append(face_encodings[0])
                    y.append(roll_number)
            except Exception as e:
                print(f"Error processing {image_path}: {e}")
                
    if not X:
        return False, "No face data found in dataset."
        
    # Train KNN
    # n_neighbors depends on dataset size. 
    n_neighbors = int(round(np.sqrt(len(X))))
    if n_neighbors < 1:
        n_neighbors = 1
        
    knn_clf = neighbors.KNeighborsClassifier(n_neighbors=n_neighbors, algorithm='ball_tree', weights='distance')
    knn_clf.fit(X, y)
    
    # Save model
    with open(model_path, 'wb') as f:
        pickle.dump(knn_clf, f)
        
    return True, f"Model trained successfully with {len(X)} faces."

def identify_faces(image_path=None, image_content=None):
    import face_recognition
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
    
    print("Detecting face locations...")
    X_face_locations = face_recognition.face_locations(image)
    
    if len(X_face_locations) == 0:
        print("face_recognition found no faces, trying OpenCV Haarcascade...")
        import cv2
        # Load Haarcascade
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Convert to grayscale for Haarcascade
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
            
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        # Convert (x, y, w, h) to (top, right, bottom, left)
        X_face_locations = []
        for (x, y, w, h) in faces:
            X_face_locations.append((y, x + w, y + h, x))
            
    print(f"Found {len(X_face_locations)} faces")
    
    if len(X_face_locations) == 0:
        return []
        
    faces_encodings = face_recognition.face_encodings(image, known_face_locations=X_face_locations)
    
    print("Finding closest neighbors...")
    closest_distances = knn_clf.kneighbors(faces_encodings, n_neighbors=1)
    print(f"DEBUG: Closest distances: {closest_distances[0]}")
    # Relaxing threshold to 0.65 for better recall
    threshold = 0.65
    are_matches = [closest_distances[0][i][0] <= threshold for i in range(len(X_face_locations))]
    
    predictions = []
    # distances are in closest_distances[0]
    distances = closest_distances[0]
    
    for i, (pred, loc, rec, dist) in enumerate(zip(knn_clf.predict(faces_encodings), X_face_locations, are_matches, distances)):
        distance_val = round(dist[0], 2)
        if rec:
            roll_number = pred
            try:
                student = Student.objects.get(roll_number=roll_number)
                name = student.name
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
