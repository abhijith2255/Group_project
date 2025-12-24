from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# --- 1. Onboarding & Profile ---
from django.db import models
from django.contrib.auth.models import User

class Course(models.Model):
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='courses/images/') 
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()

    def __str__(self):
        return self.name

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    
    # --- CHANGED: Link to the Course model ---
    # on_delete=models.SET_NULL means if you delete a Course, 
    # the student remains but their course field becomes empty.
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    
    profile_image = models.ImageField(upload_to='students/', blank=True, null=True)
    phone = models.CharField(max_length=15)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M','Male'), ('F','Female')], default='M')
    
    batch_no = models.CharField(max_length=50, default='Batch-001')
    is_fee_paid = models.BooleanField(default=False)
    documents_verified = models.BooleanField(default=False)
    placement_willingness = models.BooleanField(default=True, verbose_name="Willing for Placement")

    # --- IMPROVED: Safer display name ---
    def __str__(self):
        name = self.user.first_name if self.user.first_name else self.user.username
        return f"{name} ({self.student_id})"

class Document(models.Model):
    DOC_TYPES = [
        ('AADHAAR', 'Aadhaar Card'),
        ('DEGREE', 'Degree Certificate'),
        ('PHOTO', 'Passport Photo'),
        ('RESIDENCE', 'Residence Proof'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

# --- 2. Financials ---
class FeePayment(models.Model):
    MODES = [('FULL', 'Full Payment'), ('EMI', 'EMI'), ('LOAN', 'Loan')]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mode = models.CharField(max_length=10, choices=MODES)
    date_paid = models.DateField(auto_now_add=True)
    receipt_file = models.FileField(upload_to='receipts/', blank=True)

# --- 3. Academics ---
class Batch(models.Model):
    name = models.CharField(max_length=50)
    timetable_link = models.URLField(help_text="Link to LMS or Calendar")
    
class LeaveApplication(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    
    # Status field for Admin to approve/reject
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    
    applied_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.first_name} - {self.status}"


class Placement(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    willing_to_be_placed = models.BooleanField(default=True)
    interview_status = models.CharField(max_length=50, default='Ready')

class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
    ]

    # Link to your existing Student model
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        # Prevents duplicate attendance for the same student on the same day
        unique_together = ['student', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.student_id} - {self.date} - {self.status}"

class PendingAdmission(models.Model):
    PAYMENT_CHOICES = [
        ('FULL', 'Full Payment'),
        ('EMI', 'EMI (PDC Required)'),
        ('LOAN', 'Student Loan'),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    
    # --- NEW FIELDS ---
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='FULL')
    payment_receipt = models.FileField(upload_to='guest_payments/')
    
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.payment_mode}"
    
# StudentApp/models.py

class StudentFeedback(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(1, 'Poor'), (2, 'Fair'), (3, 'Good'), (4, 'Very Good'), (5, 'Excellent')])
    comments = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

class ExamResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam_name = models.CharField(max_length=100)  # e.g., "Mid-Term Python"
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2)
    is_passed = models.BooleanField(default=False)
    
    # Certificate file (only uploaded by Admin if passed)
    certificate_file = models.FileField(upload_to='certificates/', null=True, blank=True)

    def __str__(self):
        return f"{self.student.student_id} - {self.exam_name}"
    
