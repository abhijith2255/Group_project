from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# ==========================================
# 1. STAFF & ACADEMICS
# ==========================================

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

class Course(models.Model):
    name = models.CharField(max_length=200)
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, related_name='courses')
    image = models.ImageField(upload_to='courses/images/') 
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()

    def __str__(self):
        return self.name

class Batch(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    
    # ADD THIS LINE HERE:
    time_slot = models.CharField(max_length=50, null=True, blank=True) 

    def __str__(self):
        return self.name

# ==========================================
# 2. STUDENT CORE
# ==========================================

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, related_name='students')
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

# ==========================================
# 3. ADMINISTRATIVE (Admissions, Fees, Docs)
# ==========================================

class PendingAdmission(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    payment_receipt = models.FileField(upload_to='receipts/')
    payment_mode = models.CharField(max_length=50)
    is_processed = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.course.name}"

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

class StudentFeedback(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5) 
    feedback_type = models.CharField(max_length=50, choices=[
        ('Course', 'Course Content'),
        ('Trainer', 'Trainer/Teaching'),
        ('Facility', 'Infrastructure/Facility'),
        ('Other', 'Other')
    ], default='Course')
    comments = models.TextField()
    date_submitted = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.user.username} - {self.rating} Stars"

# ==========================================
# 4. LEARNING & CLASSROOM (LMS)
# ==========================================

class StudyMaterial(models.Model):
    MATERIAL_TYPES = [
        ('Note', 'PDF / Document'),
        ('Video', 'Video / Link'),
        ('Assignment', 'Assignment / Task'),
    ]
    title = models.CharField(max_length=200)
    topic = models.CharField(max_length=200, help_text="e.g., Python Basics, Django Views")
    type = models.CharField(max_length=20, choices=MATERIAL_TYPES, default='Note')
    file = models.FileField(upload_to='classroom/materials/', blank=True, null=True)
    link = models.URLField(blank=True, null=True, help_text="Paste YouTube or Resource Link here")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='materials')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.course.name})"

class ClassSchedule(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='schedules')
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True)
    subject = models.CharField(max_length=200, help_text="e.g. Django Views, Python Intro")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    mode = models.CharField(max_length=20, choices=[('Online', 'Online'), ('Offline', 'Offline')], default='Offline')
    meeting_link = models.URLField(blank=True, null=True)
    room_number = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.subject} ({self.start_time.strftime('%d %b')})"

# ==========================================
# 5. SYLLABUS TRACKER
# ==========================================

class Syllabus(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='syllabus')
    unit_name = models.CharField(max_length=200, help_text="e.g. Unit 1: Introduction")
    topic = models.CharField(max_length=200, help_text="e.g. Variables & Data Types")
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.name} - {self.topic}"

class BatchProgress(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE)
    syllabus_topic = models.ForeignKey(Syllabus, on_delete=models.CASCADE)
    completed_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.batch.name} - {self.syllabus_topic.topic} (Done)"

# ==========================================
# 6. EXAMS & PLACEMENT & LIBRARY
# ==========================================

class ExamResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='results')
    exam_name = models.CharField(max_length=100)
    marks_obtained = models.IntegerField()
    total_marks = models.IntegerField(default=100)
    is_passed = models.BooleanField(default=False)
    date_conducted = models.DateField()

    def percentage(self):
        return (self.marks_obtained / self.total_marks) * 100

    def __str__(self):
        return f"{self.student.user.username} - {self.exam_name}"

class BookIssue(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    book_name = models.CharField(max_length=200)
    isbn = models.CharField(max_length=50, blank=True, null=True)
    issued_on = models.DateField(auto_now_add=True)
    return_date = models.DateField()
    status = models.CharField(max_length=20, choices=[
        ('Issued', 'Issued'), ('Returned', 'Returned'), ('Overdue', 'Overdue')
    ], default='Issued')

    def __str__(self):
        return f"{self.book_name} - {self.student.user.username}"

class PlacementDrive(models.Model):
    company_name = models.CharField(max_length=200)
    job_role = models.CharField(max_length=200)
    description = models.TextField()
    date_of_drive = models.DateTimeField()
    venue = models.CharField(max_length=200)
    eligibility_criteria = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.company_name} ({self.job_role})"