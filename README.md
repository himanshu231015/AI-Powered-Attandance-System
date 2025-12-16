# 🎓 AI-Powered Attendance System

[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Latest-red.svg)](https://opencv.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A cutting-edge web application that leverages **AI-powered facial recognition** to automate student attendance tracking in educational institutions. Built with Django and advanced computer vision technologies, this system provides a seamless, contactless attendance experience for students, teachers, and administrators.

---

## 📋 Table of Contents

- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [System Architecture](#-system-architecture)
- [Installation](#-installation)
- [Project Structure](#-project-structure)
- [Usage Guide](#-usage-guide)
- [Workflow](#-workflow)
- [API Endpoints](#-api-endpoints)
- [Configuration](#-configuration)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### 🔐 **Multi-Role Authentication System**
- **Three User Roles**: Admin, Teacher, and Student with role-based access control
- Secure login/logout functionality
- Password change with OTP verification (email-based)
- User registration and profile management
- Session management and CSRF protection

### 🤖 **AI-Powered Attendance Marking**

#### **Multiple Attendance Methods:**
1. **📸 Live Camera Attendance**
   - Real-time facial recognition via webcam
   - Instant student identification
   - Automatic attendance marking
   - Live preview with detected faces highlighted

2. **📤 Upload Photo Attendance**
   - Batch processing from uploaded class photos
   - Supports multiple students in single image
   - IoU-based duplicate detection
   - Comprehensive attendance reports

3. **✍️ Manual Attendance**
   - Teacher can manually mark/edit attendance
   - Useful for makeup classes or exceptions
   - Subject and date-specific marking

### 👨‍🎓 **Student Management**
- Complete student profiles (name, roll number, email, phone, address, DOB)
- Academic information (department, year, section)
- Photo upload for facial recognition training
- Bulk student import capabilities
- Edit/delete student records

### 👨‍🏫 **Teacher Management**
- Teacher account creation and management
- Subject assignment with schedule (day, time slot)
- Multiple subjects per teacher support
- Year and section-specific assignments

### 📅 **Timetable & Schedule Management**
- Weekly timetable configuration (Monday-Sunday)
- Subject-wise class scheduling
- Time slot management (start time, end time)
- Automatic lecture slot detection for attendance

### 📊 **Advanced Attendance Tracking**
- **Smart Duplicate Prevention**: No duplicate attendance for same lecture slot
- **Time-based Validation**: Only marks attendance during scheduled class times
- **Chronological Records**: Date and time-stamped attendance logs
- **Subject-wise Tracking**: Track attendance per subject
- **Attendance Statistics**: Calculate attendance percentage per student
- **Downloadable Reports**: Export attendance as Excel/CSV files

### 🔔 **Real-time Notifications**
- Instant notifications for students on attendance marking
- Attendance alerts and updates
- Read/unread status tracking
- API-based notification system

### 📱 **Comprehensive Dashboards**

#### **Admin Dashboard:**
- Overview of total students, teachers, and attendance
- Recent attendance statistics
- Quick access to all management functions
- System-wide analytics

#### **Teacher Dashboard:**
- View assigned subjects and sections
- Current day's schedule
- Quick attendance marking tools
- Student attendance history
- QR code generation for sessions

#### **Student Dashboard:**
- Personal attendance history
- Subject-wise attendance percentage
- Daily/weekly timetable view
- Recent notifications
- Profile management

### 🎨 **Modern User Interface**
- Responsive design (mobile, tablet, desktop)
- Dark/Light theme toggle
- Intuitive navigation
- Real-time updates
- Premium aesthetics with smooth animations

---

## 🛠 Technology Stack

### **Backend**
- **Framework**: Django 5.0
- **Language**: Python 3.8+
- **Database**: SQLite (development) - easily scalable to PostgreSQL/MySQL
- **Authentication**: Django built-in auth system

### **AI/ML Libraries**
- **OpenCV** (`opencv-python`) - Computer vision and image processing
- **face_recognition** - Facial recognition using deep learning (dlib-based)
- **NumPy** - Numerical computations and array operations
- **scikit-learn** - Machine learning utilities and model serialization
- **Pillow** - Image manipulation and processing

### **Frontend**
- **HTML5** - Structure
- **CSS3** - Styling with modern features (grid, flexbox, animations)
- **JavaScript** - Interactivity and AJAX requests
- **Responsive Design** - Mobile-first approach

### **Additional Libraries**
- **Pickle** - Model serialization
- **Base64** - Image encoding for live attendance
- **JSON** - API data exchange

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Layer (Browser)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Admin     │  │   Teacher    │  │   Student    │      │
│  │  Dashboard   │  │  Dashboard   │  │  Dashboard   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/HTTPS
┌──────────────────────────▼──────────────────────────────────┐
│                    Django Application Layer                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              URL Routing & Views                    │    │
│  │  (Authentication, CRUD, Attendance Processing)      │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           Business Logic & Utilities                │    │
│  │  (Face Recognition, Model Training, Validation)     │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                      Data Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   SQLite DB  │  │  ML Model    │  │  Face        │      │
│  │  (Students,  │  │  (model.pkl) │  │  Encodings   │      │
│  │  Attendance) │  │              │  │  Cache       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### **Prerequisites**
- Python 3.8 or higher
- pip (Python package manager)
- Git
- Webcam (for live attendance feature)

### **Step 1: Clone the Repository**
```bash
git clone https://github.com/himanshu231015/AI-Powered-Attandance-System.git
cd AI-Powered-Attandance-System
```

### **Step 2: Create Virtual Environment (Recommended)**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### **Step 3: Install Dependencies**
```bash
pip install -r requirements.txt
```

**Note**: Installing `face_recognition` on Windows may require:
- Visual Studio C++ Build Tools
- CMake
- dlib

For easier installation, you can use pre-built wheels from [this repository](https://github.com/z-mahmud22/Dlib_Windows_Python3.x).

### **Step 4: Apply Database Migrations**
```bash
cd ai_attendance
python manage.py makemigrations
python manage.py migrate
```

### **Step 5: Create Superuser (Admin)**
```bash
python manage.py createsuperuser
```
Follow the prompts to create an admin account.

### **Step 6: Create Required Directories**
```bash
# The following directories should already exist, but verify:
# - database/dataset/  (for student photos)
# - media/             (for uploaded files)
```

### **Step 7: Run Development Server**
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your browser.

---

## 📁 Project Structure

```
AI-Powered-Attendance-System/
│
├── ai_attendance/                    # Main Django project directory
│   ├── ai_attendance/                # Project configuration
│   │   ├── __init__.py
│   │   ├── settings.py               # Django settings
│   │   ├── urls.py                   # Main URL configuration
│   │   └── wsgi.py                   # WSGI configuration
│   │
│   ├── core/                         # Core application (main logic)
│   │   ├── migrations/               # Database migrations
│   │   ├── templatetags/             # Custom template tags
│   │   ├── __init__.py
│   │   ├── admin.py                  # Admin panel configuration
│   │   ├── models.py                 # Database models
│   │   ├── views.py                  # View functions (1186 lines)
│   │   ├── utils.py                  # AI utilities & face recognition
│   │   └── urls.py                   # URL routing
│   │
│   ├── student_portal/               # Student-specific features
│   │   ├── migrations/
│   │   ├── models.py
│   │   └── views.py
│   │
│   ├── teacher_portal/               # Teacher-specific features
│   │   ├── migrations/
│   │   ├── models.py
│   │   └── views.py
│   │
│   ├── templates/                    # HTML templates
│   │   ├── admin/                    # Admin templates
│   │   ├── student_portal/           # Student templates
│   │   ├── teacher_portal/           # Teacher templates
│   │   ├── includes/                 # Reusable components
│   │   ├── base.html                 # Base template
│   │   ├── login.html
│   │   ├── student_dashboard.html
│   │   ├── teacher_dashboard.html
│   │   ├── admin_dashboard.html
│   │   ├── live_attendance.html
│   │   ├── manual_attendance.html
│   │   └── ... (28 template files)
│   │
│   ├── static/                       # Static files (CSS, JS, images)
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   │
│   ├── db.sqlite3                    # SQLite database
│   ├── encodings_cache.pkl           # Cached face encodings
│   └── manage.py                     # Django management script
│
├── database/
│   ├── dataset/                      # Student photos for training
│   │   └── [student_name_roll]/      # One folder per student
│   │       └── *.jpg/png             # Student photos
│   └── model.pkl                     # Trained ML model (59KB)
│
├── media/                            # User-uploaded files
│   └── student_photos/               # Profile pictures
│
├── Time table/                       # Timetable reference files
│
├── requirements.txt                  # Python dependencies
└── README.md                         # This file
```

---

## 📖 Usage Guide

### **For Administrators**

#### **1. Add Students**
1. Login as admin
2. Navigate to **Admin Dashboard** → **Add Student**
3. Fill in student details (name, roll number, email, etc.)
4. Upload student photo for facial recognition
5. Click **Save**

**Bulk Upload:**
- Use Django admin panel (`/admin`) for bulk student import

#### **2. Add Teachers**
1. Navigate to **Admin Dashboard** → **Add Teacher**
2. Create teacher account with credentials
3. Assign subjects via **Manage Teacher Subjects**

#### **3. Train Face Recognition Model**
1. After adding students with photos, navigate to **Train Model**
2. Click **Train** button
3. Wait for the model to train (progress shown)
4. Model saved as `database/model.pkl`

**Note**: Retrain the model whenever new students are added.

#### **4. Manage Timetable**
1. Go to **Manage Teacher Subjects**
2. Click **Assign Teacher Subject**
3. Select teacher, subject, day, start/end time, year, section
4. Save the assignment

### **For Teachers**

#### **1. Mark Attendance - Live Camera**
1. Login to teacher account
2. Navigate to **Live Attendance**
3. Select subject, year, and section
4. Click **Start Camera**
5. Students look at the camera
6. System automatically detects and marks attendance
7. Click **Stop** when done

#### **2. Mark Attendance - Upload Photo**
1. Navigate to **Upload Attendance**
2. Select subject, year, section
3. Upload class photo
4. System processes image and marks attendance
5. Review and confirm attendance

#### **3. Mark Attendance - Manual**
1. Navigate to **Manual Attendance**
2. Select subject, date, year, section
3. Mark each student as Present/Absent
4. Click **Submit**

#### **4. Download Attendance Reports**
1. Navigate to **Download Attendance**
2. Select date range, subject (optional)
3. Click **Download** (Excel/CSV format)

### **For Students**

#### **1. View Dashboard**
- Login to student account
- Dashboard shows:
  - Today's timetable
  - Attendance percentage
  - Recent attendance records
  - Notifications

#### **2. Check Attendance History**
- Navigate to **My Attendance**
- Filter by date range or subject
- View detailed attendance logs

#### **3. Change Password**
1. Go to **Profile** → **Change Password**
2. Request OTP (sent to registered email)
3. Enter OTP and new password
4. Confirm changes

---

## 🔄 Workflow

### **Attendance Marking Workflow (Live Camera)**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Teacher starts live attendance session                   │
│    - Selects subject, year, section                         │
│    - Opens webcam interface                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 2. Students appear in front of camera                       │
│    - Webcam captures frames continuously                    │
│    - Sends frames to server via AJAX                        │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 3. Server processes each frame                              │
│    - Detects faces using OpenCV Haar Cascades               │
│    - Extracts face encodings using face_recognition         │
│    - Compares with trained model (model.pkl)                │
│    - Calculates similarity scores                           │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 4. Student identification                                   │
│    - If match confidence > threshold: Student identified    │
│    - Checks for existing attendance record (duplicate)      │
│    - Validates against current timetable slot               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 5. Attendance marking                                       │
│    - Creates AttendanceRecord in database                   │
│    - Sends notification to student                          │
│    - Returns confirmation to teacher interface              │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│ 6. Real-time feedback                                       │
│    - Displays recognized students on screen                 │
│    - Shows attendance count                                 │
│    - Highlights bounding boxes around faces                 │
└─────────────────────────────────────────────────────────────┘
```

### **Face Recognition Training Workflow**

```
1. Admin uploads student photos
   └─> Stored in database/dataset/[student_name_roll]/

2. Click "Train Model" button
   └─> Triggered: utils.train_model()

3. System loads all student photos
   └─> For each student folder:
       ├─> Reads all images
       ├─> Detects faces using OpenCV
       └─> Extracts 128-dimensional face encodings

4. Creates mapping: encodings → student_id
   └─> Uses pickle to serialize

5. Saves trained model
   └─> Saved as database/model.pkl
   └─> Cache created: encodings_cache.pkl

6. Model ready for attendance marking
```

---

## 🔌 API Endpoints

### **Authentication**
```
POST   /login/                      - User login
POST   /logout/                     - User logout
POST   /register/                   - User registration
```

### **Attendance**
```
GET    /live_attendance/            - Live attendance page
POST   /process_live_frame/         - Process webcam frame
POST   /upload_attendance/          - Upload photo attendance
GET    /manual_attendance/          - Manual attendance page
POST   /manual_attendance/          - Submit manual attendance
GET    /attendance_list/            - View all attendance records
GET    /download_attendance/        - Download attendance reports
```

### **Student Management**
```
GET    /add_student/                - Add student page
POST   /add_student/                - Create student
GET    /manage_students/            - List all students
GET    /edit_student/<id>/          - Edit student page
POST   /edit_student/<id>/          - Update student
POST   /delete_student/<id>/        - Delete student
```

### **Teacher Management**
```
GET    /add_teacher/                - Add teacher page
POST   /add_teacher/                - Create teacher
GET    /manage_teachers/            - List all teachers
GET    /manage_teacher_subjects/    - List teacher-subject assignments
POST   /assign_teacher_subject/     - Assign teacher to subject
POST   /edit_teacher_subject/<id>/  - Update assignment
POST   /delete_teacher_subject/<id>/ - Delete assignment
```

### **Dashboards**
```
GET    /admin_dashboard/            - Admin dashboard
GET    /teacher_dashboard/          - Teacher dashboard
GET    /student_dashboard/          - Student dashboard
```

### **Notifications**
```
GET    /notifications/get/          - Get unread notifications (JSON)
POST   /notifications/read/<id>/    - Mark notification as read
```

### **Utilities**
```
POST   /train/                      - Train face recognition model
GET    /profile/                    - User profile page
POST   /change_password/            - Change password
```

---

## ⚙️ Configuration

### **Key Settings (ai_attendance/settings.py)**

```python
# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Media Files (Student photos)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR.parent / 'media'

# Dataset & Model Paths
DATASET_DIR = BASE_DIR.parent / 'database' / 'dataset'
MODEL_PATH = BASE_DIR.parent / 'database' / 'model.pkl'

# Authentication
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'
```

### **Environment Variables (Optional)**

For production deployment, set these environment variables:

```bash
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://user:pass@host:port/dbname
```

---

## 🧪 Testing

### **Manual Testing Checklist**

#### **Face Recognition Accuracy**
- [ ] Upload 5+ photos per student for better accuracy
- [ ] Ensure good lighting conditions
- [ ] Test with different angles and expressions
- [ ] Verify no false positives

#### **Attendance Marking**
- [ ] Test duplicate prevention
- [ ] Verify time slot validation
- [ ] Check notification delivery
- [ ] Validate attendance reports

#### **User Roles**
- [ ] Admin can access all features
- [ ] Teacher cannot access admin features
- [ ] Student can only view their data

---

## 🚀 Deployment

### **Production Deployment Steps**

1. **Update Settings**
   ```python
   DEBUG = False
   ALLOWED_HOSTS = ['yourdomain.com']
   ```

2. **Use Production Database**
   - Switch from SQLite to PostgreSQL/MySQL
   - Update `DATABASES` configuration

3. **Collect Static Files**
   ```bash
   python manage.py collectstatic
   ```

4. **Use WSGI Server**
   - Gunicorn (Linux)
   - uWSGI
   - mod_wsgi (Apache)

5. **Set Up Reverse Proxy**
   - Nginx or Apache

6. **Enable HTTPS**
   - Use Let's Encrypt for SSL certificates

7. **Configure Email Backend**
   - For OTP functionality
   ```python
   EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
   EMAIL_HOST = 'smtp.gmail.com'
   EMAIL_PORT = 587
   EMAIL_USE_TLS = True
   EMAIL_HOST_USER = 'your-email@gmail.com'
   EMAIL_HOST_PASSWORD = 'your-app-password'
   ```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### **Coding Standards**
- Follow PEP 8 for Python code
- Write descriptive commit messages
- Add comments for complex logic
- Update documentation as needed

---

## 🐛 Known Issues & Limitations

1. **Face Recognition Accuracy**
   - Requires good lighting conditions
   - May struggle with masks or obscured faces
   - Needs multiple training photos per student

2. **Browser Compatibility**
   - Live camera feature requires modern browsers with WebRTC support
   - Best performance in Chrome/Edge

3. **Performance**
   - Large images may take time to process
   - Model training with 1000+ students can be slow

4. **Security**
   - Plain password storage (should be removed in production)
   - Implement rate limiting for login attempts

---

## 📝 Future Enhancements

- [ ] Mobile app (Android/iOS)
- [ ] Advanced analytics and dashboards
- [ ] Parent portal for viewing student attendance
- [ ] SMS notifications
- [ ] Geolocation-based attendance (outdoor classes)
- [ ] Leave management system
- [ ] Integration with LMS platforms
- [ ] Multi-camera support for large classrooms
- [ ] Attendance prediction using ML
- [ ] Export to other formats (PDF, Google Sheets)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Himanshu**
- GitHub: [@himanshu231015](https://github.com/himanshu231015)
- Repository: [AI-Powered-Attandance-System](https://github.com/himanshu231015/AI-Powered-Attandance-System)

---

## 🙏 Acknowledgments

- **face_recognition library** by Adam Geitgey
- **OpenCV** community
- **Django** framework developers
- All contributors and testers

---

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on [GitHub Issues](https://github.com/himanshu231015/AI-Powered-Attandance-System/issues)
- Email: [your-email@example.com]

---

## 🌟 Star This Repository

If you find this project useful, please consider giving it a ⭐ on GitHub!

---

**Made with ❤️ for the education community**
