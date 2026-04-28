from django.db import models
from django.contrib.auth.models import User
import datetime

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    year = models.CharField(max_length=10, null=True, blank=True)
    section = models.CharField(max_length=10, null=True, blank=True)
    plain_password = models.CharField(max_length=128, null=True, blank=True)  # For display purposes only
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.roll_number} - {self.name}"

class TimeTable(models.Model):
    DAYS_OF_WEEK = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )
    day = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    subject = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.get_day_display()} {self.start_time}-{self.end_time}: {self.subject}"

class AttendanceRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(default=datetime.date.today)
    time = models.TimeField(default=datetime.datetime.now)
    status = models.CharField(max_length=20, default='Present')
    subject = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.student.name} - {self.date} {self.time} ({self.subject})"

class Teacher(User):
    class Meta:
        proxy = True
        verbose_name = 'Teacher'
        verbose_name_plural = 'Teachers'

class Admin(User):
    class Meta:
        proxy = True
        verbose_name = 'Admin'
        verbose_name_plural = 'Admins'

class TeacherSubject(models.Model):
    DAYS_OF_WEEK = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'is_staff': True, 'is_superuser': False})
    subject = models.CharField(max_length=100)
    year = models.CharField(max_length=10)
    section = models.CharField(max_length=10, null=True, blank=True)
    day = models.IntegerField(choices=DAYS_OF_WEEK, default=0)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.teacher.username} - {self.subject} ({self.year}) - {self.get_day_display()}"

class Notification(models.Model):
    recipient = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notification_type = models.CharField(max_length=50, default='Attendance')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.recipient.name}: {self.message}"

class AssessmentRequest(models.Model):
    ASSESSMENT_TYPES = [
        ('question_paper', 'Question Paper'),
        ('assignment', 'Assignment'),
        ('quiz', 'Quiz / MCQ Set'),
        ('lab_work', 'Lab Work / Practical'),
        ('project', 'Project Topic'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assessment_requests')
    subject = models.CharField(max_length=100)
    assessment_type = models.CharField(max_length=30, choices=ASSESSMENT_TYPES, default='question_paper')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    year = models.CharField(max_length=10, blank=True)
    section = models.CharField(max_length=10, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_remarks = models.TextField(blank=True, null=True, help_text='Admin response or remarks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.teacher.username} - {self.title} [{self.status}]"


class AccessoryRequest(models.Model):
    ACCESSORY_TYPES = [
        ('pen', 'Pen'),
        ('marker', 'Marker / Whiteboard Marker'),
        ('duster', 'Duster / Board Eraser'),
        ('chalk', 'Chalk'),
        ('board_cleaner', 'Board Cleaner / Spray'),
        ('eraser', 'Eraser'),
        ('stapler', 'Stapler'),
        ('tape', 'Tape / Adhesive'),
        ('scissors', 'Scissors'),
        ('ruler', 'Ruler / Scale'),
        ('notebook', 'Notebook / Register'),
        ('printer_paper', 'Printer Paper / A4 Sheets'),
        ('projector_remote', 'Projector Remote'),
        ('pointer', 'Laser Pointer'),
        ('other', 'Other'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High / Urgent'),
    ]
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]

    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accessory_requests')
    accessory_type = models.CharField(max_length=30, choices=ACCESSORY_TYPES, default='pen')
    quantity = models.PositiveIntegerField(default=1)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    notes = models.TextField(blank=True, help_text='Any extra details about the request')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    admin_remarks = models.TextField(blank=True, null=True, help_text='Admin response or remarks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.teacher.username} - {self.get_accessory_type_display()} x{self.quantity} [{self.status}]"
