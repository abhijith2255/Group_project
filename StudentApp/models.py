from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# --- 1. Academics & Courses ---

class Course(models.Model):
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='courses/images/') 
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()

    def __str__(self):
        return self.name

# --- NEW: Enrollment Model (Tracks the signup & payment mode) ---
class Enrollment(models.Model):
    PAYMENT_CHOICES = [
        ('full', 'Full Payment'),
        ('emi', 'Booking Fee + EMI'),
        ('loan', 'Education Loan / PDC'),
    ]

    # Link to the User (because they might not be fully approved Students yet)
    student_user = models.ForeignKey(User, on_delete=models.CASCADE) 
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='full')
    
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_approved = models.BooleanField(default=False) 
    date_enrolled = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_user.username} - {self.course.name} ({self.payment_mode})"


# --- 2. Student Profile ---

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    
    # Links to the Course model
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


# --- 3. Financials ---

class FeePayment(models.Model):
    MODES = [('FULL', 'Full Payment'), ('EMI', 'EMI'), ('LOAN', 'Loan')]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mode = models.CharField(max_length=10, choices=MODES)
    date_paid = models.DateField(auto_now_add=True)
    receipt_file = models.FileField(upload_to='receipts/', blank=True)


# --- 4. Academics & Operations ---

class Batch(models.Model):
    name = models.CharField(max_length=50)
    timetable_link = models.URLField(help_text="Link to LMS or Calendar")
    
class LeaveApplication(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    
    applied_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.first_name} - {self.status}"


# --- 5. Assessment & Placement ---

class ExamResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.CharField(max_length=100)
    marks = models.IntegerField()
    passed = models.BooleanField(default=False)
    certificate_file = models.FileField(upload_to='certificates/', blank=True)

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

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ['student', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.student_id} - {self.date} - {self.status}"
    

# StudentApp/models.py

class AdmissionRequest(models.Model):
    # ... existing fields (name, phone, etc) ...
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    address = models.TextField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    
    # --- ADD THIS NEW FIELD ---
    PAYMENT_CHOICES = [
        ('full', 'Full Payment'),
        ('emi', 'Booking Fee + EMI'),
        ('loan', 'Education Loan / PDC'),
    ]
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='full')
    
    request_date = models.DateTimeField(auto_now_add=True)
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.course.name}"