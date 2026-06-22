<!--
SUGGESTED REPOSITORY METADATA:
- Description: A sleek, automated classroom attendance system using Django and facial recognition (HOG + Haar Cascades & KNN) with real-time student alerts, dynamic dashboard statistics, and Excel reporting.
- Tagline: Frictionless AI-powered attendance tracking for modern classrooms.
- Topics/Tags: django, python, face-recognition, opencv, knn, computer-vision, machine-learning, attendance-system, student-portal, teacher-portal, openpyxl, bootstrap5, darkmode
-->

# 🎓 AI-Powered Attendance System

<div align="center">

[![Django](https://img.shields.io/badge/Django-5.0-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Latest-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-Latest-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**A modern, contactless student attendance management platform that replaces manual registers with automated face recognition.**

[Key Features](#-features) • [Tech Stack](#-tech-stack) • [Setup Guide](#-installation-guide) • [AI Workflow](#-aiml-workflow) • [Contributors](#-contributors)

</div>

---

## 📖 Problem & Solution

> [!IMPORTANT]
> **The Problem:** Calling out roll numbers or passing around sign-in sheets wastes up to **15% of class time**, invites proxy attendance (cheating), and creates massive administrative overhead when compiling reports.

**The Solution:** A fully automated web portal integrating browser-based camera processing and static photo batch analysis to instantly cross-reference face descriptors against student records.

```
                    ┌──────────────────────────────┐
                    │  Choose Attendance Method    │
                    └──────────────┬───────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  [📸 Live Webcam]         [📤 Photo Upload]         [✍️ Manual Bypass]
  Streams video and        Processes static group     Provides a backup
  marks faces instantly    snapshots of classrooms    roster checklist
```

---

## ✨ Features

* **🔐 Role-Based Portals**: Custom workspaces for **Administrators**, **Teachers**, **Students**, **HODs**, and **Store Staff**.
* **📦 Store & Inventory Management**: Fully integrated store request workflow for classroom accessories, requiring HOD approval and Store Head assignment.
* **📚 Academic Management**: End-to-end course material distribution, assignment tracking, late submission requests, and formal assessment requests.
* **🤖 Dual-Engine Face Detection**: Leverages **HOG (Histogram of Oriented Gradients)** for precision and **Haar Cascades** for speed, merging coordinates using Intersection over Union (IoU > 0.3) to avoid duplicates.
* **⚡ Incremental AI Training**: Encodes facial features into 128D vectors and caches them (`encodings_cache.pkl`) to bypass recalculations, training a **K-Nearest Neighbors (KNN)** model dynamically.
* **📅 Timetable Synchronization**: Auto-detects the current lecture block based on the timetable schedule, marking attendance only during valid slots.
* **🚫 Smart Duplicate Prevention & Auto-Absent**: Prevents repeat submissions via a time buffer. Automatically registers missing students as "Absent" and updates them to "Present" if they arrive late.
* **📊 Excel Reports & Alerts**: Instantly download calculated reports in `.xlsx` format. Students receive real-time dashboard notifications when their records change.
* **🎨 Modern Responsive UI**: Styled with clean shadows and standard transitions, featuring a persistent client-side **Dark Mode** toggle.

---

## 🛠 Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Backend** | Django 5.0, SQLite3 | Secure MVC structure & relational database |
| **AI / ML** | `face_recognition` (dlib) | Generates 128-dimensional face embedding vectors |
| **Computer Vision** | OpenCV (`opencv-python`) | Handles webcam streaming, color conversions, and image cropping |
| **Classifiers** | `scikit-learn` (KNN) | Predicts roll numbers using K-Nearest Neighbors |
| **Reports** | `openpyxl` | Generates formatted Excel spreadsheets dynamically |
| **Frontend** | HTML5, CSS3, JS, Bootstrap 5 | Responsive layout with persistent Dark/Light themes |

---

## 🏗 Architecture Overview

```mermaid
graph LR
    User[Webcam / Upload Portal] -->|Image/JSON Frame| Routing[URLs & Views]
    Routing -->|Read/Write Records| DB[(SQLite Database)]
    Routing -->|Process Frame| AI[AI Engine utils.py]
    AI -->|Incremental Cache| Cache[encodings_cache.pkl]
    AI -->|Predict Identity| Model[KNN Model.pkl]
    Model -->|Match Roll Number| Routing
```

---

## 🗄 Database Schema

The database structure consists of five key tables:

### 1. `Student`
Extends the standard Django `User` model to hold academic profiles.
* `roll_number` (Unique) • `name` • `department` • `year` • `section` • `date_of_birth` • `plain_password` (Admin display).

### 2. `TimeTable`
Defines general class timetables.
* `day` (0-6) • `start_time` • `end_time` • `subject`.

### 3. `TeacherSubject`
Maps teachers to their assigned classes.
* `teacher` (FK to User) • `subject` • `year` • `section` • `day` • `start_time` • `end_time`.

### 4. `AttendanceRecord`
Logs attendance checks.
* `student` (FK to Student) • `date` • `time` • `status` ('Present'/'Absent') • `subject`.

### 5. `Notification`
Pushes in-app alerts to student dashboards.
* `recipient` (FK to Student) • `message` • `is_read` • `created_at` • `notification_type`.

### 6. `Store & Inventory Management`
Handles the procurement and distribution workflow.
* `StoreStaff` • `StoreRequest` • `StoreRequestItem` • `StoreNotification`

### 7. `Academic & Assessments`
Handles coursework, assignments, and formal teacher requests.
* `CourseMaterial` • `StudentSubmission` • `AssessmentRequest` • `AccessoryRequest`

---

## 🧠 AI/ML Workflow

```
[Registration]  ──> Admin uploads student profile photos.
     │
[Crop & Save]   ──> OpenCV crops the largest face with 20px padding.
     │
[Extraction]    ──> Computes 128D face encodings (cached in encodings_cache.pkl).
     │
[Model Fit]     ──> Fits KNN model where Neighbors (k) = round(sqrt(N)), saved to model.pkl.
     ├────────────────────────────────────────────────────────────────────────┐
     ▼ (At Inference)                                                         ▼ (At Inference)
[HOG Detection] ──> Extracts precise face boxes.               [Haar Cascade] ──> Detects fast face boxes.
     │                                                                        │
     └─────────────────────────► [IoU Merging (Threshold > 0.3)] ◄────────────┘
                                              │
                                   [KNN Prediction & Match]
                                              │
                                   [Distance Check (<= 0.50)]
                                     ├─────────────────────┤
                                     ▼ (Yes)               ▼ (No)
                             [Mark Present]          [Mark Unknown]
```

---

## 📈 Model Evaluation

The recognition pipeline was benchmarked across **105 face encodings** from **12 registered students** using a 5-fold stratified cross-validation strategy. Evaluation covers three distinct axes: classification performance, biometric verification, and embedding-space quality.

> Run the evaluation yourself: `python evaluate_model.py` (from the project root). Results are saved to `evaluation_output/`.

---

### 1️⃣ Classification Task

| Metric | Value |
| :--- | :--- |
| **Accuracy** | **98.10%** |
| **Precision** (weighted avg) | **99.05%** |
| **Recall** (weighted avg) | **98.10%** |
| **F1 Score** (weighted avg) | **98.53%** |
| **Unknown Rejection Rate** | 1.90% |


---

### 2️⃣ Verification Task (Biometric)

The system was evaluated as a **1-vs-1 verification engine** by computing similarity scores across all **5,460 pairwise combinations** (534 genuine + 4,926 impostor pairs).

| Metric | Value | Description |
| :--- | :--- | :--- |
| **AUC (ROC)** | **0.9947** | Near-perfect discriminability; 1.0 is ideal |
| **EER** | **4.31%** | Equal Error Rate — where FAR equals FRR |
| **FAR** | **0.63%** | False Accept Rate — impostors wrongly accepted |
| **FRR** | **9.93%** | False Reject Rate — genuine users wrongly rejected |

---

### 3️⃣ Embedding Similarity (128-D Face Vectors)

Analysis of pairwise distances in the 128-dimensional `dlib` face embedding space:

| Metric | Genuine Pairs | Impostor Pairs | Ideal |
| :--- | :---: | :---: | :---: |
| **Mean Cosine Similarity** | 0.9599 | 0.8708 | 1.0 / 0.0 |
| **Mean Euclidean Distance** | 0.3801 | 0.7218 | 0.0 / >0.53 |
| **RMSE** | 0.4033 | 0.2907 | 0.0 / — |



### 🔬 Evaluation Script

A standalone evaluation script is included at the project root:

```bash
# From the project root directory
python evaluate_model.py
```

It generates three plots in the `evaluation_output/` folder:

| Output File | Contents |
| :--- | :--- |
| `confusion_matrix.png` | 12×12 confusion matrix with color intensity |
| `roc_far_frr.png` | ROC curve (AUC) + FAR/FRR vs threshold sweep |
| `embedding_similarity.png` | Euclidean & Cosine distance distributions (genuine vs impostor) |

---

## 📁 Folder Structure

```hl
AI-Powered-Attendance-System/
├── ai_attendance/                 # Django Project root directory
│   ├── ai_attendance/             # Project Settings & Routing
│   ├── core/                      # Main application view & model files
│   │   ├── utils.py               # AI Pipeline (HOG, Haar Cascades, KNN)
│   │   └── views.py               # Controller endpoints (1180+ lines)
│   ├── student_portal/            # Student dashboard views
│   ├── teacher_portal/            # CSV timetable imports & teacher views
│   ├── templates/                 # UI HTML templates (Admin, Student, Teacher)
│   ├── static/                    # Custom CSS overrides
│   ├── db.sqlite3                 # Local database file
│   └── encodings_cache.pkl        # Pickle cache mapping image to 128D encoding
├── database/                      # AI Assets folder
│   ├── dataset/                   # Folder tree containing cropped student faces
│   └── model.pkl                  # Serialized KNN classifier model file
├── media/                         # Upload directory for classroom photos
├── requirements.txt               # Dependencies list
└── README.md                      # This file
```

---

## ⚙️ Environment Setup

Create an `.env` file at the root of `ai_attendance/`:
```env
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=postgres://user:password@host:5432/dbname
```

---

## 🚀 Installation Guide

### Prerequisites
Ensure your machine has **Python (3.8 - 3.11)**, **CMake**, and a **C++ Compiler** (like Visual Studio Build Tools for Windows or Xcode for macOS).

### Step-by-Step Installation

```bash
# 1. Clone the project
git clone https://github.com/himanshu231015/AI-Powered-Attandance-System.git
cd AI-Powered-Attandance-System

# 2. Setup a virtual environment
python -m venv venv
# On Windows use: venv\Scripts\activate
# On Linux/macOS use: source venv/bin/activate

# 3. Install packages
pip install --upgrade pip
pip install -r requirements.txt
```

> [!TIP]
> If installing `face_recognition` fails on Windows due to `dlib` compilation issues, download a pre-built wheel (`.whl`) matching your Python version from [Dlib Windows Wheels Repository](https://github.com/z-mahmud22/Dlib_Windows_Python3.x) and run:
> `pip install dlib-19.22.99-cpXX-cpXX-win_amd64.whl`

---

## 💻 Running Locally

```bash
# Move to the project folder
cd ai_attendance

# 1. Run migrations
python manage.py makemigrations
python manage.py migrate

# 2. Create the Admin account
python manage.py createsuperuser

# 3. Start development server
python manage.py runserver
```
Visit `http://127.0.0.1:8000` in your browser. Log in to the admin panel at `/admin/`, upload student photographs, and click **Train Model** to generate the AI model.

---

## ☁️ Deployment Guide

1. **Static Files**: Run `python manage.py collectstatic` to consolidate frontend files.
2. **Database Configuration**: Update `settings.py` to point to a production-ready database (e.g. PostgreSQL).
3. **WSGI Server**: Run the project using **Gunicorn**:
   `gunicorn ai_attendance.wsgi:application --bind 0.0.0.0:8000`
4. **Nginx Reverse Proxy**: Route public traffic to Gunicorn and directly serve the static/media directories.
5. **Secure Connection (HTTPS)**: Webcam features require a secure HTTPS connection to access the user's camera in production. Use **Certbot (Let's Encrypt)**:
   `sudo certbot --nginx -d yourdomain.com`

---

## 🔌 API Endpoints

### 🔑 Authentication
* `POST /login/` - User authentication session start.
* `GET /logout/` - Session termination.

### 📊 Dashboards
* `GET /admin_dashboard/` - Central administrative controls.
* `GET /teacher_dashboard/` - Teacher dashboard showing assigned rosters.
* `GET /student_dashboard/` - Student performance metrics and records.

### 📂 Attendance & Management
* `POST /core/process_live_frame/` - Stream live frames to the AI engine (AJAX endpoint).
* `POST /core/upload_attendance/` - Batch recognition via uploaded group photos.
* `GET /core/download_attendance/` - Export attendance sheets in `.xlsx` format.
* `POST /core/train/` - Triggers AI model retraining.
* `GET /core/notifications/get/` - Fetches unread student messages.

---

## 🖼 Screenshots

```carousel
![Login screen](https://raw.githubusercontent.com/himanshu231015/AI-Powered-Attandance-System/main/media/login_mockup.png)
<!-- slide -->
![Admin Controls Dashboard](https://raw.githubusercontent.com/himanshu231015/AI-Powered-Attandance-System/main/media/admin_dashboard_mockup.png)
<!-- slide -->
![Webcam Streaming Panel](https://raw.githubusercontent.com/himanshu231015/AI-Powered-Attandance-System/main/media/live_camera_mockup.png)
```

---

## 🔧 Troubleshooting

* **Compilation Errors (`dlib`)**: Run `pip install cmake` and ensure C++ build tools are installed before running the installer.
* **Webcam Blocked**: Modern web browsers require an **HTTPS** connection (or localhost) to grant camera permissions.
* **"No face data found" on Train**: Check that folders under `database/dataset/` are named in the `{roll_number}_{name}` format and contain actual image files.
* **Database Locks**: SQLite can lock up during high concurrent workloads. Upgrade to PostgreSQL/MySQL for multi-user production environments.

---

## ❓ FAQ

**Q: Can it recognize faces in low lighting?**
**A:** HOG and Haar Cascade detectors require moderate ambient light. If it's too dark, use manual attendance mode.

**Q: What if a student grows a beard?**
**A:** Upload a few updated pictures to their folder and click the retrain button.

**Q: Can we track attendance for several subjects?**
**A:** Yes. The system automatically syncs records to subjects according to the calendar timetable and the current classroom time slot.

---

## 👥 Contributors

### Vivek Kumar Choudhary
* **Enrollment Number**: 0873AL231027
* **Course**: B.Tech in CSE (Artificial Intelligence & Machine Learning)
* **College Name**: Sri Aurobindo Institute of Technology (SAIT), Indore

### Himanshu Kumar
* **Enrollment Number**: 0873AL231015
* **Course**: B.Tech in CSE (Artificial Intelligence & Machine Learning)
* **College Name**: Sri Aurobindo Institute of Technology (SAIT), Indore

---

## 📄 License & Acknowledgements

* **License**: MIT License.
* **Acknowledgements**: We thank Adam Geitgey for the [`face_recognition`](https://github.com/ageitgey/face_recognition) project, Davis King for the [`dlib`](https://github.com/davisking/dlib) library, and the OpenCV contributors.
