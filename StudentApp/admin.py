from django.contrib import admin
from .models import Student, Batch, Document, FeePayment, LeaveApplication, ExamResult, Placement, Course, Enrollment,Trainer

# --- 1. STUDENT ADMIN ---
class StudentAdmin(admin.ModelAdmin):
    # Define the columns you want to see
    list_display = ('student_id', 'get_student_name', 'course', 'batch', 'is_fee_paid', 'placement_willingness')
    
    # Custom method to fetch the name safely
    def get_student_name(self, obj):
        # Return first_name if it exists, otherwise return the username
        if obj.user.first_name:
            return f"{obj.user.first_name} {obj.user.last_name}"
        return obj.user.username
    
    # Set the column header name
    get_student_name.short_description = 'Student Name'

# Register Student using the class above
admin.site.register(Student, StudentAdmin)


# --- 2. OTHER MODELS ---

# class LeaveApplicationAdmin(admin.ModelAdmin):
#     list_display = ('get_student_name', 'start_date', 'end_date', 'status', 'applied_on')
#     list_filter = ('status', 'applied_on')
#     list_editable = ('status',)

#     def get_student_name(self, obj):
#         # Try to get the full name
#         fname = obj.student.user.first_name
#         lname = obj.student.user.last_name
        
#         if fname:
#             return f"{fname} {lname}"
        
#         # If no name is set, fall back to the username (e.g., 'abhi123')
#         return obj.student.user.username

#     get_student_name.short_description = 'Student'
class LeaveApplicationAdmin(admin.ModelAdmin):
    # --- CRITICAL FIX HERE ---
    # Change 'student' to 'get_student_name' in this list
    list_display = ('get_student_name', 'start_date', 'end_date', 'status', 'applied_on')
    
    list_filter = ('status', 'applied_on')
    list_editable = ('status',)

    def get_student_name(self, obj):
        # This checks if a name exists, otherwise shows the username
        fname = obj.student.user.first_name
        lname = obj.student.user.last_name
        if fname:
            return f"{fname} {lname}"
        return obj.student.user.username

    get_student_name.short_description = 'Student Name'
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')

class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'status', 'enrolled_at')
    list_filter = ('status', 'course')
    search_fields = ('student__name', 'course__title')
admin.site.register(Enrollment, EnrollmentAdmin)

class TrainerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'designation', 'expertise')

admin.site.register(Trainer, TrainerAdmin)

# Simple registration for the rest
admin.site.register(Batch)
admin.site.register(Document)
admin.site.register(FeePayment)
admin.site.register(ExamResult)
admin.site.register(Placement)
admin.site.register(LeaveApplication, LeaveApplicationAdmin)
