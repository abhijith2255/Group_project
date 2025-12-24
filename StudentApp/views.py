from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import LeaveApplication, PendingAdmission,Student,Attendance,Course,FeePayment,Document,StudentFeedback,ExamResult
from .forms import LeaveForm
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
import string
import random
# --- VIEW 1: LOGIN ---
def student_login(request):
    if request.method == 'POST':
        # In Django, 'username' is the field name for auth, even if we use Student ID
        username_input = request.POST['username']
        password_input = request.POST['password']

        user = authenticate(request, username=username_input, password=password_input)

        if user is not None:
            login(request, user)
            return redirect('dashboard') 
        else:
            messages.error(request, "Invalid Student ID or Password")
    
    return render(request, 'index.html')

# --- VIEW 2: DASHBOARD ---
# StudentApp/views.py

@login_required(login_url='login')
def dashboard(request):
    user = request.user

    # --- SCENARIO 1: SUPER ADMIN ---
    if user.is_superuser:
        pending_count = PendingAdmission.objects.filter(is_processed=False).count()
        total_students = Student.objects.count()
        return render(request, 'dashboard_admin.html', {
            'pending_count': pending_count,
            'total_students': total_students
        })

    # --- SCENARIO 2: TRAINER (Staff but not Superuser) ---
    elif user.is_staff:
        # Assuming you will link trainers to batches later
        # my_batches = Batch.objects.filter(trainer=user) 
        return render(request, 'dashboard_trainer.html')

    # --- SCENARIO 3: STUDENT ---
    else:
        try:
            student = Student.objects.get(user=user)
            # Calculate Attendance Pct
            records = Attendance.objects.filter(student=student)
            total = records.count()
            present = records.filter(status='Present').count()
            pct = round((present/total)*100, 1) if total > 0 else 0
            
            return render(request, 'dashboard_student.html', {
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

@login_required(login_url='login')
def student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student = None
    
    # We pass the 'student' object. 
    # The HTML will automatically get the image from 'student.profile_image'
    return render(request, 'profile.html', {'student': student})

@login_required(login_url='login')
def apply_leave(request):
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return render(request, 'error.html', {'message': 'You are not a registered student.'})

    # --- NEW: Fetch the leave history for this student ---
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

    # --- NEW: Pass 'leaves' to the template ---
    return render(request, 'apply_leave.html', {'form': form, 'leaves': leaves})

# --- VIEW 5: VIEW LEAVE STATUS ---
@staff_member_required # Only Admin/Staff can access this
def admin_mark_attendance(request):
    batches = Student.objects.values_list('batch_no', flat=True).distinct()
    selected_batch = request.GET.get('batch')
    students = Student.objects.none()

    if selected_batch:
        students = Student.objects.filter(batch_no=selected_batch).select_related('user')

    if request.method == 'POST':
        date = request.POST.get('date')
        for student in students:
            status = request.POST.get(f'status_{student.id}')
            if status:
                Attendance.objects.update_or_create(
                    student=student, 
                    date=date, 
                    defaults={'status': status}
                )
        return redirect(f'{request.path}?batch={selected_batch}')

    return render(request, 'admin_mark.html', {
        'batches': batches,
        'students': students,
        'selected_batch': selected_batch,
        'today': timezone.now().date()
    })

# --- STUDENT VIEW: See My Stats ---
@login_required # Login required, but any user can access
def student_my_attendance(request):
    # 1. Get the logged-in student profile
    try:
        student = request.user.student 
    except Student.DoesNotExist:
        return render(request, 'attendance/error.html', {'message': "No student profile found for this user."})

    # 2. Get all records for this student
    records = Attendance.objects.filter(student=student).order_by('-date')

    # 3. Calculate Stats (Present vs Total)
    total_days = records.count()
    present_days = records.filter(status='Present').count()
    
    attendance_percentage = 0
    if total_days > 0:
        attendance_percentage = (present_days / total_days) * 100

    return render(request, 'student_view.html', {
        'records': records,
        'present_days': present_days,
        'total_days': total_days,
        'percentage': round(attendance_percentage, 1)
    })

def course_list(request):
    # Fetch all courses from the database
    courses = Course.objects.all() 
    
    context = {
        'courses': courses
    }
    
    # Render the course.html template with the data
    return render(request, 'course.html', context)
@login_required(login_url='login')
def enroll_now(request, course_id):
    """
    Step 1: Links the selected course to the logged-in student.
    """
    # 1. Get the course or show 404
    course = get_object_or_404(Course, id=course_id)
    
    # 2. Find or create the student profile
    try:
        student = request.user.student
    except Student.DoesNotExist:
        # Generate a simple unique ID if it doesn't exist
        temp_id = f"STU-{request.user.id}-{timezone.now().strftime('%y%m%d')}"
        student = Student.objects.create(user=request.user, student_id=temp_id)

    # 3. Assign the course to the student
    student.course = course
    student.save()

    # 4. Redirect to the onboarding form where they pay and upload docs
    return redirect('complete_onboarding')

@login_required(login_url='login')
def complete_onboarding(request):
    """
    Step 2: Handles Fee Mode selection and Document Uploads.
    """
    try:
        student = request.user.student
    except Student.DoesNotExist:
        return redirect('dashboard')

    if request.method == 'POST':
        # 1. Capture Payment Info
        pay_mode = request.POST.get('payment_mode')
        amount = request.POST.get('amount', 0)
        
        FeePayment.objects.create(
            student=student,
            amount=amount,
            mode=pay_mode
        )

        # 2. Capture Document Uploads
        # We loop through the expected files to save them in the Document model
        doc_fields = {
            'photo': 'PHOTO',
            'aadhaar': 'AADHAAR',
            'residence': 'RESIDENCE',
            'degree': 'DEGREE'
        }

        for field_name, doc_type in doc_fields.items():
            uploaded_file = request.FILES.get(field_name)
            if uploaded_file:
                Document.objects.create(
                    student=student,
                    doc_type=doc_type,
                    file=uploaded_file
                )

        # 3. Update Student Status
        messages.success(request, "Enrollment details and documents submitted successfully!")
        return redirect('dashboard')

    return render(request, 'onboarding.html', {'student': student})

def guest_enroll_form(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        # Capture standard fields
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        receipt = request.FILES.get('receipt')
        
        # --- NEW: Capture Payment Mode ---
        mode = request.POST.get('payment_mode') 

        if full_name and email and receipt and mode:
            try:
                PendingAdmission.objects.create(
                    course=course,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    payment_receipt=receipt,
                    payment_mode=mode  # Saving the mode
                )
                messages.success(request, "Enquiry submitted successfully!")
                return render(request, 'thank_you.html')
            except Exception as e:
                messages.error(request, f"Error: {e}")
        else:
            messages.error(request, "Please fill all fields including Payment Mode.")

    return render(request, 'guest_enrollment.html', {'course': course})

@staff_member_required
def convert_to_student(request, pending_id):
    pending = get_object_or_404(PendingAdmission, id=pending_id)
    
    # 1. Create the Django User
    # You can auto-generate a password or set a default one
    username = pending.email.split('@')[0] # Example: abhi from abhi@email.com
    password = User.objects.make_random_password()
    
    user = User.objects.create_user(
        username=username,
        email=pending.email,
        password=password,
        first_name=pending.full_name
    )

    # 2. Create the Student Profile
    Student.objects.create(
        user=user,
        student_id=f"STU{user.id}",
        course=pending.course,
        is_fee_paid=True
    )

    # 3. Mark the lead as processed
    pending.is_processed = True
    pending.save()

    # 4. Here you would normally send an email to the user with their password
    messages.success(request, f"Student created! Username: {username}, Password: {password}")
    return redirect('pending_list')

@staff_member_required
def pending_admissions_list(request):
    # Fetch guests who paid but don't have accounts yet
    pendings = PendingAdmission.objects.filter(is_processed=False)
    return render(request, 'admin_pending_list.html', {'pendings': pendings})

@staff_member_required
def approve_guest(request, pending_id):
    pending = get_object_or_404(PendingAdmission, id=pending_id)
    
    # 1. Generate a unique Username and a random Password
    username = pending.email.split('@')[0]
    # Ensure username is unique in the system
    if User.objects.filter(username=username).exists():
        username = f"{username}{random.randint(10, 99)}"
    
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    # 2. Create the User Account
    user = User.objects.create_user(
        username=username,
        email=pending.email,
        password=password,
        first_name=pending.full_name
    )

    # 3. Create the Student Profile & link to the selected Course
    Student.objects.create(
        user=user,
        student_id=f"STU{user.id:04d}",
        course=pending.course,
        phone=pending.phone,
        is_fee_paid=True # Since admin is approving after seeing receipt
    )

    # 4. Finalize the Pending record
    pending.is_processed = True
    pending.save()

    # Success message with credentials to be shared with the student
    messages.success(request, f"Account Created! User: {username} | Pass: {password}")
    return redirect('pending_admissions_list')


@login_required
def my_classroom(request):
    """ Shows Batch schedule, LMS link, and issued books """
    student = request.user.student
    # Assuming you add a 'timetable_image' or link to the Course model
    return render(request, 'student_classroom.html', {'student': student})

# --- ACTION 2: FEEDBACK ---
@login_required
def submit_feedback(request):
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comments = request.POST.get('comments')
        StudentFeedback.objects.create(
            student=request.user.student,
            rating=rating,
            comments=comments
        )
        messages.success(request, "Thank you! Your feedback helps us improve.")
        return redirect('dashboard')
    return render(request, 'student_feedback.html')

# --- ACTION 3: EXAMS & CERTIFICATES ---
@login_required
def exam_portal(request):
    student = request.user.student
    results = ExamResult.objects.filter(student=student)
    
    # Gatekeeper Logic for Certification
    # Criteria: Fees Paid + Docs Verified + Passed All Exams
    all_passed = not results.filter(is_passed=False).exists() and results.exists()
    can_download_cert = student.is_fee_paid and student.documents_verified and all_passed

    return render(request, 'student_exams.html', {
        'results': results,
        'can_download_cert': can_download_cert
    })

# --- ACTION 4: PLACEMENT WILLINGNESS ---
@login_required
def toggle_placement(request):
    student = request.user.student
    # Switch the boolean status (True -> False or False -> True)
    student.placement_willingness = not student.placement_willingness
    student.save()
    
    status = "Active" if student.placement_willingness else "Inactive"
    messages.info(request, f"Placement status updated to: {status}")
    return redirect('student_profile')
    
