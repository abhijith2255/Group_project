from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
import string
import random
from decimal import Decimal
from django.db.models import Q, Sum  # Standardized imports

from .models import (
    BatchProgress, BookIssue, ClassSchedule, LeaveApplication, PendingAdmission, PlacementDrive, Student, Attendance, 
    Course, FeePayment, Document, StudentFeedback, ExamResult, StudyMaterial, Syllabus, 
    Trainer, Batch
)
from .forms import LeaveForm

# ==========================================
# AUTHENTICATION VIEWS
# ==========================================

def student_login(request):
    if request.method == 'POST':
        username_input = request.POST['username']
        password_input = request.POST['password']

        user = authenticate(request, username=username_input, password=password_input)

        if user is not None:
            login(request, user)
            return redirect('dashboard') 
        else:
            messages.error(request, "Invalid Student ID or Password")
    
    return render(request, 'index.html')

def user_logout(request):
    logout(request)
    return redirect('login')

# ==========================================
# DASHBOARD & PROFILE
# ==========================================

@login_required(login_url='login')
def dashboard(request):
    user = request.user

    # --- SCENARIO 1: SUPER ADMIN ---
    if user.is_superuser:
        pending_count = PendingAdmission.objects.filter(is_processed=False).count()
        total_students = Student.objects.count()
        return render(request, 'bdm/dashboard.html', {
            'pending_count': pending_count,
            'total_students': total_students
        })

    # --- SCENARIO 2: TRAINER ---
    elif hasattr(user, 'trainer'):
        return redirect('trainer_dashboard') 

    # --- SCENARIO 3: STUDENT ---
    else:
        try:
            student = Student.objects.get(user=user)
            
            # 1. Calculate Attendance (Existing code)
            records = Attendance.objects.filter(student=student)
            total = records.count()
            present = records.filter(status='Present').count()
            pct = round((present/total)*100, 1) if total > 0 else 0
            
            # 2. Calculate Fee Balance (NEW CODE)
            # Sum up all payments made by this student
            total_paid = FeePayment.objects.filter(student=student).aggregate(Sum('amount'))['amount__sum']
            
            # If no payments exist, the result is None, so set it to 0
            if total_paid is None:
                total_paid = 0
                
            balance = student.course.price - total_paid

            return render(request, 'student/dashboard_student.html', {
                'student': student,
                'percentage': pct,
                'balance': balance  # <--- Crucial: Pass this to the template
            })

        except Student.DoesNotExist:
            messages.error(request, "Access Denied: Profile not found.")
            return redirect('user_logout')

@login_required(login_url='login')
def student_profile(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        messages.error(request, "Profile not found.")
        return redirect('dashboard')

    if request.method == 'POST':
        # 1. Update User Model Fields
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.save()

        # 2. Update Student Model Fields
        student.phone = request.POST.get('phone')
        student.address = request.POST.get('address')
        
        # Handle Date Safely (Prevents TypeError)
        dob = request.POST.get('date_of_birth')
        if dob: 
            student.date_of_birth = dob
            
        # Handle Checkbox
        student.placement_willingness = request.POST.get('placement_willingness') == 'on'

        # 3. Handle Image Upload
        if 'profile_image' in request.FILES:
            student.profile_image = request.FILES['profile_image']

        student.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('student_profile')

    return render(request, 'student/profile.html', {'student': student})


# StudentApp/views.py

@login_required
# StudentApp/views.py

@login_required
def my_classroom(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return redirect('dashboard')

    # 1. Fetch Materials
    materials = StudyMaterial.objects.filter(
        Q(batch=student.batch) | 
        Q(course=student.course, batch__isnull=True)
    ).order_by('-created_at')

    # 2. Fetch Schedule (Upcoming classes)
    schedule = ClassSchedule.objects.filter(
        batch=student.batch,
        start_time__gte=timezone.now()
    ).order_by('start_time')

    # 3. Fetch Syllabus & Progress (NEW)
    syllabus = Syllabus.objects.filter(course=student.course).order_by('order')
    
    # Get IDs of topics completed by this batch
    completed_ids = BatchProgress.objects.filter(
        batch=student.batch
    ).values_list('syllabus_topic_id', flat=True)

    # Calculate Percentage
    total_topics = syllabus.count()
    completed_count = len(completed_ids)
    progress_percent = int((completed_count / total_topics) * 100) if total_topics > 0 else 0

    return render(request, 'student/classroom.html', {
        'student': student,
        'materials': materials,
        'schedule': schedule,
        'syllabus': syllabus,           # <--- New
        'completed_ids': completed_ids, # <--- New
        'progress_percent': progress_percent # <--- New
    })
@login_required
def exam_portal(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return redirect('dashboard')

    results = ExamResult.objects.filter(student=student)
    
    # Download Certificate Logic
    has_results = results.exists()
    all_passed = not results.filter(is_passed=False).exists()
    
    can_download_cert = (
        has_results and 
        all_passed and 
        student.is_fee_paid and 
        student.documents_verified
    )

    return render(request, 'student/exams.html', {
        'student': student,
        'results': results,
        'can_download_cert': can_download_cert
    })

@login_required
def download_certificate(request):
    # This is a placeholder. In real app, generate PDF here.
    messages.success(request, "Certificate download started...")
    return redirect('exam_portal')

# ==========================================
# ATTENDANCE & LEAVE (Student)
# ==========================================

@login_required(login_url='login')
def apply_leave(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return render(request, 'error.html', {'message': 'You are not a registered student.'})

    leaves = LeaveApplication.objects.filter(student=student).order_by('-applied_on')

    if request.method == 'POST':
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.student = student
            leave_request.save()
            messages.success(request, "Leave application submitted.")
            return redirect('apply_leave') # Redirect to same page to show history
    else:
        form = LeaveForm()

    return render(request, 'student/apply_leave.html', {'form': form, 'leaves': leaves})

@login_required
def student_my_attendance(request):
    try:
        student = request.user.student 
    except Student.DoesNotExist:
        return render(request, 'attendance/error.html', {'message': "No student profile found."})

    records = Attendance.objects.filter(student=student).order_by('-date')
    total_days = records.count()
    present_days = records.filter(status='Present').count()
    
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0

    return render(request, 'student/student_view.html', {
        'records': records,
        'present_days': present_days,
        'total_days': total_days,
        'percentage': round(attendance_percentage, 1)
    })

# ==========================================
# FEES & DOCUMENTS (Student)
# ==========================================

@login_required
def pay_fee(request):
    try:
        student = request.user.student
    except AttributeError:
        return redirect('dashboard')

    # 1. Get Course Price
    # Since you removed 'total_fee_committed', we use the Course price directly.
    if student.course:
        course_price = student.course.price
    else:
        messages.error(request, "You are not enrolled in any course.")
        return redirect('dashboard')

    # 2. Calculate Total Paid
    # We sum up all amounts from the 'FeePayment' table
    total_paid = FeePayment.objects.filter(student=student).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    balance_remaining = course_price - total_paid

    # 3. Handle Payment Submission
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount'))
            mode = request.POST.get('payment_mode') # Maps to 'mode' in your model
            
            # Basic Validation
            if amount <= 0:
                 messages.error(request, "Amount must be greater than 0.")
            elif amount > balance_remaining:
                 messages.error(request, f"You cannot pay more than the remaining balance (₹{balance_remaining}).")
            else:
                # 4. Create the Record (Using your FeePayment model fields)
                FeePayment.objects.create(
                    student=student,
                    amount=amount,
                    mode=mode  # Your model calls this field 'mode'
                )

                # 5. Check if fully paid and update Student model
                # We calculate the NEW total to see if they are done.
                new_total_paid = total_paid + amount
                if course_price - new_total_paid <= 0:
                    student.is_fee_paid = True
                    student.save()

                messages.success(request, "Payment successful!")
                return redirect('dashboard')

        except ValueError:
            messages.error(request, "Invalid amount entered.")

    return render(request, 'student/pay_fee.html', {
        'student': student,
        'course_price': course_price,
        'total_paid': total_paid,
        'balance_remaining': balance_remaining
    })

@login_required
def view_id_card(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return redirect('dashboard')

    if not student.is_fee_paid or not student.documents_verified:
        messages.error(request, "ID Card locked! Please complete payment and document verification.")
        return redirect('dashboard')

    photo_url = student.profile_image.url if student.profile_image else None

    return render(request, 'student/id_card.html', {
        'student': student,
        'photo_url': photo_url
    })

@login_required
def submit_feedback(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return redirect('dashboard')

    if request.method == 'POST':
        rating = request.POST.get('rating')
        feedback_type = request.POST.get('feedback_type')
        comments = request.POST.get('comments')

        if not rating:
            messages.error(request, "Please select a star rating.")
        else:
            StudentFeedback.objects.create(
                student=student,
                rating=rating,
                feedback_type=feedback_type,
                comments=comments
            )
            messages.success(request, "Thank you! Your feedback has been submitted.")
            return redirect('submit_feedback')

    my_feedback = StudentFeedback.objects.filter(student=student).order_by('-date_submitted')

    return render(request, 'student/feedback.html', {
        'student': student, 
        'my_feedback': my_feedback
    })

# ==========================================
# TRAINER / ADMIN VIEWS
# ==========================================

@login_required
def trainer_dashboard(request):
    try:
        trainer = request.user.trainer
    except Trainer.DoesNotExist:
        messages.error(request, "Access Denied")
        return redirect('login')

    # 1. Fetch Batches
    batches = Batch.objects.filter(trainer=trainer).order_by('time_slot')
    today = timezone.now().date()
    
    dashboard_data = []
    
    for batch in batches:
        # --- THE FIX IS HERE ---
        # Old (Error): Attendance.objects.filter(batch=batch, ...)
        # New (Fixed): Attendance.objects.filter(student__batch=batch, ...)
        is_attendance_marked = Attendance.objects.filter(student__batch=batch, date=today).exists()
        
        # Calculate Syllabus Progress
        total_topics = Syllabus.objects.filter(course=batch.course).count()
        completed_topics = BatchProgress.objects.filter(batch=batch).count()
        
        if total_topics > 0:
            progress = int((completed_topics / total_topics) * 100)
        else:
            progress = 0
            
        dashboard_data.append({
            'batch': batch,
            'student_count': batch.students.count(),
            'is_attendance_marked': is_attendance_marked,
            'progress': progress,
            'completed_topics': completed_topics,
            'total_topics': total_topics,
        })

    # 3. Stats
    total_students = Student.objects.filter(batch__in=batches).count()

    return render(request, 'trainer/dashboard_trainer.html', {
        'trainer': trainer,
        'dashboard_data': dashboard_data,
        'total_batches': batches.count(),
        'total_students': total_students,
        'today': today
    })

@login_required
def batch_students(request, batch_id):
    try:
        trainer = request.user.trainer
        batch = get_object_or_404(Batch, id=batch_id, trainer=trainer)
    except (Trainer.DoesNotExist, Batch.DoesNotExist):
        messages.error(request, "Invalid Batch or Unauthorized Access")
        return redirect('trainer_dashboard')

    students = batch.students.all()
    pending_leaves = LeaveApplication.objects.filter(student__batch=batch, status='Pending').order_by('-applied_on')

    return render(request, 'trainer/batch_students.html', {
        'batch': batch,
        'students': students,
        'pending_leaves': pending_leaves,
    })

@login_required
def admin_mark_attendance(request):
    user = request.user
    
    if user.is_superuser:
        batches = Batch.objects.all()
    elif hasattr(user, 'trainer'):
        batches = Batch.objects.filter(trainer=user.trainer)
    else:
        batches = Batch.objects.none()

    selected_batch_id = request.GET.get('batch_id')
    students = Student.objects.none()

    if selected_batch_id:
        if user.is_superuser:
            batch = get_object_or_404(Batch, id=selected_batch_id)
        else:
            batch = get_object_or_404(Batch, id=selected_batch_id, trainer=user.trainer)
        students = batch.students.all().select_related('user')

    if request.method == 'POST':
        date = request.POST.get('date')
        marked_count = 0
        
        for student in students:
            status = request.POST.get(f'status_{student.id}')
            if status:
                Attendance.objects.update_or_create(
                    student=student, 
                    date=date, 
                    defaults={'status': status}
                )
                marked_count += 1
        
        if marked_count > 0:
            messages.success(request, f"Attendance successfully marked for {marked_count} students.")
        else:
            messages.warning(request, "No attendance changes were detected.")

        return redirect(f'{request.path}?batch_id={selected_batch_id}')

    return render(request, 'trainer/mark_attendance.html', {
        'batches': batches,
        'students': students,
        'selected_batch_id': int(selected_batch_id) if selected_batch_id else None,
        'today': timezone.now().date()
    })

@login_required
def batch_leaves(request, batch_id):
    try:
        trainer = request.user.trainer
        batch = get_object_or_404(Batch, id=batch_id, trainer=trainer)
    except (Trainer.DoesNotExist, Batch.DoesNotExist):
        messages.error(request, "Access Denied: Invalid Batch")
        return redirect('trainer_dashboard')

    leaves = LeaveApplication.objects.filter(student__batch=batch).order_by('-applied_on')
    return render(request, 'trainer/leave_requests.html', {'batch': batch, 'leaves': leaves})

@login_required
def update_leave_status(request, leave_id, status):
    if not (request.user.is_staff or hasattr(request.user, 'trainer')):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')

    leave = get_object_or_404(LeaveApplication, id=leave_id)
    if status in ['Approved', 'Rejected']:
        leave.status = status
        leave.save()
        action = "Approved" if status == 'Approved' else "Rejected"
        messages.success(request, f"Leave for {leave.student.user.first_name} has been {action}.")
    
    return redirect(request.META.get('HTTP_REFERER', 'trainer_dashboard'))

# ==========================================
# PUBLIC / ENROLLMENT VIEWS
# ==========================================

def course_listt(request):
    courses = Course.objects.all() 
    return render(request, 'course.html', {'courses': courses})



# StudentApp/views.py

# --- VIEW: MY LIBRARY (Books Issued) ---
@login_required
def my_library(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return redirect('dashboard')

    books = BookIssue.objects.filter(student=student).order_by('-issued_on')
    
    return render(request, 'student/library.html', {'student': student, 'books': books})

# --- VIEW: PLACEMENT PORTAL ---
@login_required
def placement_portal(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return redirect('dashboard')

    # 1. Check if student is eligible (Willingness must be ON)
    if not student.placement_willingness:
        messages.warning(request, "You have opted OUT of placements. Please update your profile to view drives.")
        return redirect('student_profile')

    # 2. Show active drives happening in the future
    upcoming_drives = PlacementDrive.objects.filter(
        is_active=True, 
        date_of_drive__gte=timezone.now()
    ).order_by('date_of_drive')

    return render(request, 'student/placements.html', {
        'student': student,
        'drives': upcoming_drives
    })

# StudentApp/views.py

@login_required
def my_schedule(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return redirect('dashboard')

    if not student.batch:
        messages.warning(request, "You are not assigned to a batch yet.")
        return redirect('dashboard')

    # Get today's date to filter out old classes
    now = timezone.now()

    # Fetch upcoming classes for this student's batch, sorted by nearest time
    upcoming_classes = ClassSchedule.objects.filter(
        batch=student.batch,
        start_time__gte=now
    ).order_by('start_time')

    return render(request, 'student/schedule.html', {
        'student': student,
        'schedule': upcoming_classes
    })

# StudentApp/views.py

@login_required
def lesson_plan(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return redirect('dashboard')

    if not student.batch:
        messages.warning(request, "You are not assigned to a batch yet.")
        return redirect('dashboard')

    # 1. Get the full syllabus for the Student's Course
    syllabus = Syllabus.objects.filter(course=student.course)

    # 2. Get the list of IDs of topics that are completed for this Batch
    completed_ids = BatchProgress.objects.filter(
        batch=student.batch
    ).values_list('syllabus_topic_id', flat=True)

    # 3. Calculate Progress Percentage
    total_topics = syllabus.count()
    completed_count = len(completed_ids)
    progress_percent = int((completed_count / total_topics) * 100) if total_topics > 0 else 0

    return render(request, 'student/lesson_plan.html', {
        'student': student,
        'syllabus': syllabus,
        'completed_ids': completed_ids,
        'progress_percent': progress_percent
    })

