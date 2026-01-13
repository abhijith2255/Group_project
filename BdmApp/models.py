from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from StudentApp.models import Student,Course
# ==========================================
# 1. SETTINGS & MARKETING
# ==========================================

class LeadSource(models.Model):
    """Where did the lead come from? (e.g., Facebook, Walk-in, Referral)"""
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Campaign(models.Model):
    """Marketing campaigns (e.g., 'New Year Promo 2026')"""
    name = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

# ========================================co==
# 2. LEAD MANAGEMENT (CORE)
# ==========================================

class Lead(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'New Lead'),
        ('CONTACTED', 'Contacted / Follow-up'),
        ('INTERESTED', 'Interested / Hot'),
        ('CONVERTED', 'Converted / Admitted'),      # Success state
        ('LOST', 'Lost / Dropped'),
        ('JUNK', 'Junk Lead'),
    ]

    # --- Basic Details ---
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True)
    city = models.CharField(max_length=100, blank=True)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male','Male'), ('Female','Female'), ('Other','Other')], null=True, blank=True)
    qualification = models.CharField(max_length=100, null=True, blank=True, help_text="e.g. B.Tech, MCA, 12th")
    payment_type = models.CharField(max_length=20, choices=[('One-Time','One-Time'), ('Installment','Installment')], null=True, blank=True)
    
    # --- Integration with StudentApp ---
    # We use a string reference 'StudentApp.Course' to avoid circular import errors
    course_interested = models.ForeignKey(
        'StudentApp.Course', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='leads'
    )
    
    # --- Marketing Info ---
    source = models.ForeignKey(LeadSource, on_delete=models.SET_NULL, null=True)
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True)
    
    # --- Assignment ---
    # Who is the BDM/Counselor handling this lead?
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True, 
        limit_choices_to={'is_staff': True}, 
        related_name='assigned_leads'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    
    # --- Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.status})"

# ==========================================
# 3. COUNSELING LOGS (HISTORY)
# ==========================================

class Interaction(models.Model):
    """Logs every call, email, or meeting with the lead"""
    INTERACTION_TYPES = [
        ('CALL', 'Phone Call'),
        ('WHATSAPP', 'WhatsApp Chat'),
        ('EMAIL', 'Email'),
        ('MEETING', 'In-Person Meeting'),
        ('OTHER', 'Other'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='interactions')
    counselor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    notes = models.TextField(help_text="Summary of the conversation")
    
    interaction_date = models.DateTimeField(default=timezone.now)
    next_follow_up = models.DateField(null=True, blank=True, help_text="Set a reminder for next call")

    class Meta:
        ordering = ['-interaction_date']

    def __str__(self):
        return f"{self.lead.first_name} - {self.interaction_type}"
    
class FeeInstallment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='installments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.student.user.username} - {self.amount} Due: {self.due_date}"
    
# StudentApp/models.py
from django.db import models

class Enquiry(models.Model):
    # --- Personal Details ---
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    
    # --- Demographics (From Lead Model) ---
    city = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male','Male'), ('Female','Female'), ('Other','Other')], null=True, blank=True)
    qualification = models.CharField(max_length=100, null=True, blank=True, help_text="e.g. B.Tech, MCA, 12th")
    
    # --- Course Interest ---
    course_interested = models.ForeignKey('StudentApp.Course', on_delete=models.SET_NULL, null=True, blank=True)
    
    # --- Message ---
    message = models.TextField(blank=True)
    
    # --- System Fields ---
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"