from django.contrib import admin
from .models import AdmissionRequest, Student, Batch, Document, FeePayment, LeaveApplication, ExamResult, Placement, Course, Enrollment

# --- 1. STUDENT ADMIN ---
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'get_student_name', 'course', 'batch_no', 'is_fee_paid', 'placement_willingness')
    
    def get_student_name(self, obj):
        if obj.user.first_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return obj.user.username
    
    get_student_name.short_description = 'Student Name'

admin.site.register(Student, StudentAdmin)


# --- 2. LEAVE APPLICATION ADMIN ---
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ('get_student_name', 'start_date', 'end_date', 'status', 'applied_on')
    list_filter = ('status', 'applied_on')
    list_editable = ('status',)

    def get_student_name(self, obj):
        fname = obj.student.user.first_name
        lname = obj.student.user.last_name
        if fname:
            return f"{fname} {lname}"
        return obj.student.user.username

    get_student_name.short_description = 'Student Name'

admin.site.register(LeaveApplication, LeaveApplicationAdmin)


# --- 3. COURSE ADMIN (Updated) ---
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    # CRITICAL: This allows 'Enrollment' to search for courses
    search_fields = ('name',) 


# --- 4. ENROLLMENT ADMIN (Updated) ---
@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    # Columns to show in the list
    list_display = ('get_username', 'course', 'payment_mode', 'amount_paid', 'is_approved', 'date_enrolled')
    
    # Add filters on the right side
    list_filter = ('payment_mode', 'is_approved', 'course')
    
    # Allow admins to toggle approval directly from the list view
    list_editable = ('is_approved',)

    # --- THE FIX FOR YOUR ISSUE ---
    # This turns the "Student User" dropdown into a SEARCH BOX (autocomplete)
    autocomplete_fields = ['student_user', 'course']

    def get_username(self, obj):
        return obj.student_user.username
    get_username.short_description = 'Student User'

@admin.register(AdmissionRequest)
class AdmissionRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'course', 'payment_mode', 'is_processed', 'request_date')
    list_filter = ('is_processed', 'course')
    search_fields = ('full_name', 'phone')

# --- 5. REGISTER OTHER MODELS ---
admin.site.register(Batch)
admin.site.register(Document)
admin.site.register(FeePayment)
admin.site.register(ExamResult)
admin.site.register(Placement)