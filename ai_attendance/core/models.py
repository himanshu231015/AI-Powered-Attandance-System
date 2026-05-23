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

class TeacherProfile(models.Model):
    DESIGNATION_CHOICES = [
        ('hod', 'HOD'),
        ('asst_prof', 'Assistant Professor'),
    ]
    DEPARTMENT_CHOICES = [
        ('CSE',  'Computer Science & Engineering'),
        ('IT',   'Information Technology'),
        ('ECE',  'Electronics & Communication'),
        ('EE',   'Electrical Engineering'),
        ('ME',   'Mechanical Engineering'),
        ('CE',   'Civil Engineering'),
        ('AIDS', 'AI & Data Science'),
        ('AIML', 'AI & Machine Learning'),
        ('other','Other'),
    ]
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    designation = models.CharField(
        max_length=20,
        choices=DESIGNATION_CHOICES,
        default='asst_prof'
    )
    department = models.CharField(
        max_length=10,
        choices=DEPARTMENT_CHOICES,
        default='CSE'
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_designation_display()} ({self.department})"

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

# ─────────────────────────────────────────────
#  Store Management
# ─────────────────────────────────────────────

class StoreStaff(models.Model):
    ROLE_CHOICES = [
        ('head',  'Store Head'),
        ('staff', 'Store Staff'),
    ]
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='store_profile')
    role       = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')
    department = models.CharField(max_length=100, blank=True)
    phone      = models.CharField(max_length=15, blank=True)

    class Meta:
        verbose_name        = 'Store Staff'
        verbose_name_plural = 'Store Staff'

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"{name} ({self.get_role_display()})"


class StoreRequest(models.Model):
    STATUS_CHOICES = [
        ('pending_hod',   'Awaiting HOD Approval'),
        ('hod_rejected',  'Rejected by HOD'),
        ('pending_store', 'Awaiting Store Head'),
        ('assigned',      'Assigned to Staff'),
        ('delivered',     'Delivered by Staff (Awaiting Confirmation)'),
        ('partial',       'Partially Fulfilled'),
        ('fulfilled',     'Fully Fulfilled'),
        ('rejected',      'Rejected by Store'),
    ]

    # Basic info
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='store_requests')
    title        = models.CharField(max_length=200)
    notes        = models.TextField(blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_hod')

    # HOD approval step
    hod_approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='hod_approved_requests'
    )
    hod_approved_at = models.DateTimeField(null=True, blank=True)
    hod_remarks     = models.TextField(blank=True)

    # Store fulfilment step
    fulfilled_by = models.ForeignKey(
        StoreStaff, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='fulfilled_requests'
    )
    assigned_to  = models.ForeignKey(
        StoreStaff, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_requests'
    )
    assigned_at       = models.DateTimeField(null=True, blank=True)
    expected_delivery = models.DateField(null=True, blank=True)
    staff_response    = models.TextField(blank=True, help_text='Store staff response/notes')
    remarks           = models.TextField(blank=True, help_text='Store Head remarks')

    # Teacher Confirmation
    teacher_confirmed_at = models.DateTimeField(null=True, blank=True)
    teacher_remarks      = models.TextField(blank=True, help_text='Teacher remarks on receipt')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.requested_by.username} – {self.title} [{self.status}]"

    @property
    def total_items(self):
        return self.items.count()

    @property
    def fulfilled_items_count(self):
        return sum(1 for item in self.items.all() if item.is_fulfilled)

    @property
    def fulfillment_pct(self):
        total = self.total_items
        if total == 0:
            return 0
        return int((self.fulfilled_items_count / total) * 100)

    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


class StoreRequestItem(models.Model):
    request            = models.ForeignKey(StoreRequest, on_delete=models.CASCADE, related_name='items')
    item_name          = models.CharField(max_length=200)
    quantity_requested = models.PositiveIntegerField(default=1)
    quantity_provided  = models.PositiveIntegerField(default=0)
    quantity_received  = models.PositiveIntegerField(default=0)

    @property
    def is_fulfilled(self):
        return self.quantity_provided >= self.quantity_requested

    @property
    def fulfillment_pct(self):
        if self.quantity_requested == 0:
            return 100
        return min(100, int((self.quantity_provided / self.quantity_requested) * 100))

    def __str__(self):
        return f"{self.item_name}: {self.quantity_provided}/{self.quantity_requested}"


# ─────────────────────────────────────────────
#  Store Notifications (User-level)
# ─────────────────────────────────────────────

class StoreNotification(models.Model):
    NOTIF_TYPE_CHOICES = [
        ('status_update', 'Status Updated'),
        ('hod_action',    'HOD Action'),
        ('store_action',  'Store Action'),
        ('fulfillment',   'Fulfilment Update'),
        ('general',       'General'),
    ]

    recipient     = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='store_notifications'
    )
    store_request = models.ForeignKey(
        'StoreRequest', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='notifications'
    )
    message       = models.TextField()
    notif_type    = models.CharField(max_length=30, choices=NOTIF_TYPE_CHOICES, default='general')
    is_read       = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notif_type}] → {self.recipient.username}: {self.message[:60]}"


class CourseMaterial(models.Model):
    MATERIAL_TYPES = [
        ('assignment', 'Assignment'),
        ('notes', 'Notes'),
    ]
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_materials')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES, default='assignment')
    file = models.FileField(upload_to='course_materials/')
    subject = models.CharField(max_length=100, blank=True)
    year = models.CharField(max_length=10, blank=True)
    section = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(blank=True, null=True)

    @property
    def is_past_due(self):
        from django.utils import timezone
        if self.due_date:
            return timezone.now() > self.due_date
        return False

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.get_material_type_display()}"


class StudentSubmission(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='submissions')
    assignment = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='submissions/')
    remarks = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(max_length=10, blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ('student', 'assignment')

    def __str__(self):
        return f"{self.student.name} - {self.assignment.title}"

    @property
    def is_late(self):
        if self.assignment.due_date:
            return self.submitted_at > self.assignment.due_date
        return False


class LateSubmissionRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='late_requests')
    assignment = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE, related_name='late_requests')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('student', 'assignment')

    def __str__(self):
        return f"{self.student.name} - {self.assignment.title} ({self.status})"
