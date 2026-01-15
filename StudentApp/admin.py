from django.contrib import admin
from .models import (
    Student, Course, Batch, Trainer, FeePayment, Document, 
    Attendance, LeaveApplication, PendingAdmission, StudentFeedback,
    ExamResult, StudyMaterial, BookIssue, PlacementDrive, 
    ClassSchedule, Syllabus, BatchProgress
)

# ==========================================
# 1. ACADEMIC & STAFF
# ==========================================

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_info', 'price', 'trainer')
    search_fields = ('name',)
    
    def duration_info(self, obj):
        # FIX: Change 'batches' to 'batch_set'
        return f"{obj.batch_set.count()} Batches Running"
    duration_info.short_description = 'Status'

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'course', 'trainer', 'start_date', 'end_date')
    list_filter = ('course', 'trainer')
    search_fields = ('name',)

@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'designation', 'phone_number', 'expertise')
    search_fields = ('full_name', 'user__username')
    
    def phone_number(self, obj):
        return "N/A" # Update this if you add phone to Trainer model
    phone_number.short_description = 'Contact'

# ==========================================
# 2. STUDENTS
# ==========================================

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('student_id', 'get_full_name', 'course', 'batch', 'is_fee_paid', 'placement_willingness')
    list_filter = ('course', 'batch', 'is_fee_paid', 'placement_willingness')
    search_fields = ('student_id', 'user__username', 'phone')
    list_editable = ('is_fee_paid',)

    def get_full_name(self, obj):
        if obj.user.first_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return obj.user.username
    get_full_name.short_description = 'Name'

# ==========================================
# 3. ADMISSIONS & FEES
# ==========================================

@admin.register(PendingAdmission)
class PendingAdmissionAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'course', 'email', 'phone', 'is_processed', 'date_created')
    list_filter = ('is_processed', 'course')
    list_editable = ('is_processed',)

@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = ('student', 'amount', 'mode', 'date_paid')
    list_filter = ('mode', 'date_paid')
    search_fields = ('student__student_id',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('student', 'doc_type', 'uploaded_at')
    list_filter = ('doc_type',)

# ==========================================
# 4. ATTENDANCE & LEAVES
# ==========================================

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status')
    list_filter = ('date', 'status', 'student__batch')
    search_fields = ('student__student_id',)

@admin.register(LeaveApplication)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ('get_student_name', 'start_date', 'end_date', 'status', 'applied_on')
    list_filter = ('status', 'applied_on')
    list_editable = ('status',)

    def get_student_name(self, obj):
        return f"{obj.student.user.first_name} {obj.student.user.last_name}"
    get_student_name.short_description = 'Student'

# ==========================================
# 5. CLASSROOM, SYLLABUS & SCHEDULE
# ==========================================

@admin.register(ClassSchedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ('subject', 'batch', 'start_time', 'mode', 'trainer')
    list_filter = ('batch', 'mode', 'trainer')
    ordering = ('start_time',)

@admin.register(StudyMaterial)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'course', 'batch', 'created_at')
    list_filter = ('type', 'course')
    search_fields = ('title',)

@admin.register(Syllabus)
class SyllabusAdmin(admin.ModelAdmin):
    list_display = ('order', 'topic', 'unit_name', 'course')
    list_filter = ('course',)
    ordering = ('course', 'order')

@admin.register(BatchProgress)
class BatchProgressAdmin(admin.ModelAdmin):
    list_display = ('batch', 'syllabus_topic', 'completed_date')
    list_filter = ('batch',)

# ==========================================
# 6. EXAMS, LIBRARY & PLACEMENTS
# ==========================================

@admin.register(ExamResult)
class ExamResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam_name', 'marks_obtained', 'is_passed', 'date_conducted')
    list_filter = ('exam_name', 'is_passed')
    search_fields = ('student__user__username',)

@admin.register(BookIssue)
class LibraryAdmin(admin.ModelAdmin):
    list_display = ('book_name', 'student', 'issued_on', 'return_date', 'status')
    list_filter = ('status',)
    list_editable = ('status',)

@admin.register(PlacementDrive)
class PlacementAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'job_role', 'date_of_drive', 'venue', 'is_active')
    list_filter = ('is_active',)

@admin.register(StudentFeedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('student', 'rating', 'feedback_type', 'date_submitted')
    list_filter = ('rating', 'feedback_type')