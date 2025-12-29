from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# --- 1. Staff & Instructors ---
class Trainer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100, help_text="e.g. Senior Python Instructor")
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to='trainers/', blank=True, null=True)
    expertise = models.CharField(max_length=200, help_text="e.g. Data Science, Web Development")
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name

# --- 2. Academics (Course & Batch) ---
class Course(models.Model):
    name = models.CharField(max_length=200)
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, related_name='courses')
    image = models.ImageField(upload_to='courses/images/') 
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()

    def __str__(self):
        return self.name

class Batch(models.Model):
    name = models.CharField(max_length=50) # e.g., "Py-2025-Jan"
    
    # Links
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='batches')
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, related_name='batches')
    
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    timetable_link = models.URLField(help_text="Link to LMS or Calendar", blank=True)

    def __str__(self):
        return f"{self.name} - {self.course.name}"

# --- 3. Students ---
class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    
    # Links
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, related_name='students')
    # Optional direct course link (can be kept or removed)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True)
    
    profile_image = models.ImageField(upload_to='students/', blank=True, null=True)
    phone = models.CharField(max_length=15)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M','Male'), ('F','Female')], default='M')
    
    is_fee_paid = models.BooleanField(default=False)
    documents_verified = models.BooleanField(default=False)
    placement_willingness = models.BooleanField(default=True, verbose_name="Willing for Placement")

    def __str__(self):
        name = self.user.first_name if self.user.first_name else self.user.username
        return f"{name} ({self.student_id})"

class Enrollment(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    )
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    progress = models.IntegerField(default=0) 

    class Meta:
        unique_together = ('student', 'course') 

    def __str__(self):
        return f"{self.student} enrolled in {self.course.name}"

# --- 4. Supporting Models ---
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

class FeePayment(models.Model):
    MODES = [('FULL', 'Full Payment'), ('EMI', 'EMI'), ('LOAN', 'Loan')]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mode = models.CharField(max_length=10, choices=MODES)
    date_paid = models.DateField(auto_now_add=True)
    receipt_file = models.FileField(upload_to='receipts/', blank=True)

class LeaveApplication(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    STATUS_CHOICES = [('Pending', 'Pending'),('Approved', 'Approved'),('Rejected', 'Rejected')]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Pending')
    applied_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.first_name} - {self.status}"

class Placement(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    willing_to_be_placed = models.BooleanField(default=True)
    interview_status = models.CharField(max_length=50, default='Ready')

class Attendance(models.Model):
    STATUS_CHOICES = [('Present', 'Present'),('Absent', 'Absent'),('Late', 'Late')]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)

    class Meta:
        unique_together = ['student', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.student_id} - {self.date} - {self.status}"

class PendingAdmission(models.Model):
    PAYMENT_CHOICES = [('FULL', 'Full Payment'),('EMI', 'EMI (PDC Required)'),('LOAN', 'Student Loan')]
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='FULL')
    payment_receipt = models.FileField(upload_to='guest_payments/')
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.payment_mode}"

class StudentFeedback(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(1, 'Poor'), (2, 'Fair'), (3, 'Good'), (4, 'Very Good'), (5, 'Excellent')])
    comments = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

class ExamResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    exam_name = models.CharField(max_length=100) 
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    total_marks = models.DecimalField(max_digits=5, decimal_places=2)
    is_passed = models.BooleanField(default=False)
    certificate_file = models.FileField(upload_to='certificates/', null=True, blank=True)

    def __str__(self):
        return f"{self.student.student_id} - {self.exam_name}"