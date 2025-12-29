from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
import string
import random

from .models import (
    LeaveApplication, PendingAdmission, Student, Attendance, 
    Course, FeePayment, Document, StudentFeedback, ExamResult, 
    Trainer, Batch
)
from .forms import LeaveForm

# --- VIEW 1: LOGIN ---
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

# --- VIEW 2: DASHBOARD (Central Hub) ---
@login_required(login_url='login')
def dashboard(request):
    user = request.user

    # --- SCENARIO 1: SUPER ADMIN ---
    if user.is_superuser:
        pending_count = PendingAdmission.objects.filter(is_processed=False).count()
        total_students = Student.objects.count()
        # Points to Templates/bdm/dashboard_admin.html
        return render(request, 'bdm/dashboard_admin.html', {
            'pending_count': pending_count,
            'total_students': total_students
        })

    # --- SCENARIO 2: TRAINER ---
    elif hasattr(user, 'trainer'):
        # Redirects to the URL name 'trainer_dashboard'
        return redirect('trainer_dashboard') 

    # --- SCENARIO 3: STUDENT ---
    else:
        try:
            student = Student.objects.get(user=user)
            # Calculate Attendance Percentage
            records = Attendance.objects.filter(student=student)
            total = records.count()
            present = records.filter(status='Present').count()
            pct = round((present/total)*100, 1) if total > 0 else 0
            
            # Points to Templates/student/dashboard_student.html
            return render(request, 'student/dashboard_student.html', {
                'student': student,
                'percentage': pct
            })
        except Student.DoesNotExist:
            messages.error(request, "Student profile not found.")
            return redirect('login')

# --- VIEW 3: LOGOUT ---
def user_logout(request):
    logout(request)
    return redirect('login')

# --- VIEW 4: STUDENT PROFILE ---
@login_required(login_url='login')
def student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    return render(request, 'student/profile.html', {'student': student})

# --- VIEW 5: APPLY LEAVE ---
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
            return redirect('dashboard') 
    else:
        form = LeaveForm()

    return render(request, 'student/apply_leave.html', {'form': form, 'leaves': leaves})

# --- VIEW 6: ADMIN MARK ATTENDANCE ---
@login_required
def admin_mark_attendance(request):
    user = request.user
    
    # --- 1. SMART BATCH FILTERING ---
    if user.is_superuser:
        # Admin sees ALL batches
        batches = Batch.objects.all()
    elif hasattr(user, 'trainer'):
        # Trainer sees ONLY their assigned batches
        batches = Batch.objects.filter(trainer=user.trainer)
    else:
        # Other staff see nothing
        batches = Batch.objects.none()

    selected_batch_id = request.GET.get('batch_id')
    students = Student.objects.none()

    # --- 2. FETCH STUDENTS ---
    if selected_batch_id:
        # Security: Ensure the logged-in trainer actually owns this batch
        # (Admins can access any batch)
        if user.is_superuser:
            batch = get_object_or_404(Batch, id=selected_batch_id)
        else:
            # If trainer tries to access a batch that isn't theirs -> 404 Error
            batch = get_object_or_404(Batch, id=selected_batch_id, trainer=user.trainer)
            
        students = batch.students.all().select_related('user')

    # --- 3. HANDLE FORM SUBMISSION ---
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

# --- VIEW 7: STUDENT ATTENDANCE STATS ---
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
# --- PASTE THIS AT THE BOTTOM OF StudentApp/views.py ---

# --- ADD THESE TO THE BOTTOM OF StudentApp/views.py ---

@login_required
def batch_leaves(request, batch_id):
    """
    View to show the list of leave requests for a specific batch.
    """
    # 1. Security check: Ensure the trainer owns this batch
    try:
        trainer = request.user.trainer
        batch = get_object_or_404(Batch, id=batch_id, trainer=trainer)
    except (Trainer.DoesNotExist, Batch.DoesNotExist):
        messages.error(request, "Access Denied: Invalid Batch")
        return redirect('trainer_dashboard')

    # 2. Fetch all leaves for this batch (Newest first)
    leaves = LeaveApplication.objects.filter(student__batch=batch).order_by('-applied_on')

    return render(request, 'trainer/leave_requests.html', {
        'batch': batch,
        'leaves': leaves
    })

@login_required
def update_leave_status(request, leave_id, status):
    """
    View to handle Approve/Reject buttons.
    """
    # 1. Security Check: Only Staff or Trainers allowed
    if not (request.user.is_staff or hasattr(request.user, 'trainer')):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')

    # 2. Get the specific leave application
    leave = get_object_or_404(LeaveApplication, id=leave_id)

    # 3. Update the status if valid
    if status in ['Approved', 'Rejected']:
        leave.status = status
        leave.save()
        
        # 4. Show success message
        action = "Approved" if status == 'Approved' else "Rejected"
        messages.success(request, f"Leave for {leave.student.user.first_name} has been {action}.")
    
    # 5. Redirect back to the previous page
    return redirect(request.META.get('HTTP_REFERER', 'trainer_dashboard'))
# --- VIEW 8: COURSE LIST ---
def course_list(request):
    courses = Course.objects.all() 
    return render(request, 'course.html', {'courses': courses})

# --- VIEW 9: ENROLLMENT LOGIC ---
@login_required(login_url='login')
def enroll_now(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    try:
        student = request.user.student
    except Student.DoesNotExist:
        temp_id = f"STU-{request.user.id}-{timezone.now().strftime('%y%m%d')}"
        student = Student.objects.create(user=request.user, student_id=temp_id)

    student.course = course
    student.save()
    return redirect('complete_onboarding')

@login_required(login_url='login')
def complete_onboarding(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return redirect('dashboard')

    if request.method == 'POST':
        pay_mode = request.POST.get('payment_mode')
        amount = request.POST.get('amount', 0)
        
        FeePayment.objects.create(student=student, amount=amount, mode=pay_mode)

        doc_fields = {'photo': 'PHOTO', 'aadhaar': 'AADHAAR', 'residence': 'RESIDENCE', 'degree': 'DEGREE'}
        for field_name, doc_type in doc_fields.items():
            uploaded_file = request.FILES.get(field_name)
            if uploaded_file:
                Document.objects.create(student=student, doc_type=doc_type, file=uploaded_file)

        messages.success(request, "Enrollment details submitted!")
        return redirect('dashboard')

    return render(request, 'onboarding.html', {'student': student})

# --- VIEW 10: GUEST & ADMIN ADMISSION ---
def guest_enroll_form(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        receipt = request.FILES.get('receipt')
        mode = request.POST.get('payment_mode') 

        if full_name and email and receipt and mode:
            try:
                PendingAdmission.objects.create(
                    course=course, full_name=full_name, email=email, 
                    phone=phone, payment_receipt=receipt, payment_mode=mode
                )
                messages.success(request, "Enquiry submitted successfully!")
                return render(request, 'thank_you.html')
            except Exception as e:
                messages.error(request, f"Error: {e}")
        else:
            messages.error(request, "Please fill all fields.")

    return render(request, 'guest_enrollment.html', {'course': course})

@staff_member_required
def convert_to_student(request, pending_id):
    # This view seems to be a duplicate or older logic, but kept for safety.
    # Usually 'approve_guest' covers this.
    pending = get_object_or_404(PendingAdmission, id=pending_id)
    return redirect('approve_guest', pending_id=pending.id)

@staff_member_required
def pending_admissions_list(request):
    pendings = PendingAdmission.objects.filter(is_processed=False)
    return render(request, 'admin_pending_list.html', {'pendings': pendings})

@staff_member_required
def approve_guest(request, pending_id):
    pending = get_object_or_404(PendingAdmission, id=pending_id)
    
    username = pending.email.split('@')[0]
    if User.objects.filter(username=username).exists():
        username = f"{username}{random.randint(10, 99)}"
    
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    user = User.objects.create_user(
        username=username, email=pending.email, password=password, first_name=pending.full_name
    )

    Student.objects.create(
        user=user, student_id=f"STU{user.id:04d}", 
        course=pending.course, phone=pending.phone, is_fee_paid=True
    )

    pending.is_processed = True
    pending.save()

    messages.success(request, f"Account Created! User: {username} | Pass: {password}")
    return redirect('pending_admissions_list')

# --- STUDENT EXTRAS ---
@login_required
def my_classroom(request):
    student = request.user.student
    return render(request, 'student/student_classroom.html', {'student': student})

@login_required
def submit_feedback(request):
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comments = request.POST.get('comments')
        StudentFeedback.objects.create(
            student=request.user.student, rating=rating, comments=comments
        )
        messages.success(request, "Thank you! Your feedback helps us improve.")
        return redirect('dashboard')
    return render(request, 'student/student_feedback.html')

@login_required
def exam_portal(request):
    student = request.user.student
    results = ExamResult.objects.filter(student=student)
    all_passed = not results.filter(is_passed=False).exists() and results.exists()
    can_download_cert = student.is_fee_paid and student.documents_verified and all_passed
    return render(request, 'student_exams.html', {'results': results, 'can_download_cert': can_download_cert})

@login_required
def toggle_placement(request):
    student = request.user.student
    student.placement_willingness = not student.placement_willingness
    student.save()
    status = "Active" if student.placement_willingness else "Inactive"
    messages.info(request, f"Placement status updated to: {status}")
    return redirect('student_profile')

# --- TRAINER DASHBOARD VIEWS ---
@login_required
def trainer_dashboard(request):
    try:
        trainer = request.user.trainer
    except Trainer.DoesNotExist:
        messages.error(request, "Access Denied: You are not a Trainer.")
        return redirect('login')

    my_batches = Batch.objects.filter(trainer=trainer)
    # Points to Templates/trainer/dashboard_trainer.html
    return render(request, 'trainer/dashboard_trainer.html', {
        'trainer': trainer,
        'batches': my_batches
    })

# StudentApp/views.py

@login_required
def batch_students(request, batch_id):
    try:
        trainer = request.user.trainer
        batch = get_object_or_404(Batch, id=batch_id, trainer=trainer)
    except (Trainer.DoesNotExist, Batch.DoesNotExist):
        messages.error(request, "Invalid Batch or Unauthorized Access")
        return redirect('trainer_dashboard')

    students = batch.students.all()

    # --- NEW: Fetch Pending Leaves for this Batch ---
    # We filter leaves where the student is in this batch AND status is 'Pending'
    pending_leaves = LeaveApplication.objects.filter(
        student__batch=batch, 
        status='Pending'
    ).order_by('-applied_on')

    return render(request, 'trainer/batch_students.html', {
        'batch': batch,
        'students': students,
        'pending_leaves': pending_leaves, # <--- Pass this to template
    })