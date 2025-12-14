from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import AdmissionRequest, Enrollment, LeaveApplication,Student,Attendance,Course
from .forms import LeaveForm
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
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
@login_required(login_url='login')  # Force them to login first
def dashboard(request):
    user = request.user
    
    # 1. If the user is an Admin/Staff, show a different view or just the sidebar links
    if user.is_staff:
        # You can pass total student count, etc., for admins here
        return render(request, 'dashboard.html', {'is_admin': True})

    # 2. If it's a Student, try to get their profile
    try:
        student_profile = Student.objects.get(user=user)
    except Student.DoesNotExist:
        # If they are logged in but don't have a Student profile yet (e.g., just signed up)
        return render(request, 'dashboard.html', {
            'error': 'Profile not found. Please contact admin.'
        })

    # 3. Calculate Attendance Percentage (Optional Logic)
    # This is a simple calculation: (Days Present / Total Days) * 100
    total_days = Attendance.objects.filter(student=student_profile).count()
    present_days = Attendance.objects.filter(student=student_profile, status='Present').count()
    
    attendance_percentage = 0
    if total_days > 0:
        attendance_percentage = int((present_days / total_days) * 100)

    # 4. Pass data to the template
    context = {
        'student': student_profile,
        'attendance_percentage': attendance_percentage,
    }
    return render(request, 'dashboard.html', context)

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
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    # Now it is safe to check for the student profile because the user is definitely logged in.
    if not hasattr(request.user, 'student'):
        from .models import Student
        import uuid
        Student.objects.create(user=request.user, student_id=str(uuid.uuid4())[:8])

    if request.method == 'POST':
        # 1. UPDATE STUDENT DETAILS FIRST
        try:
            student = request.user.student
        except Student.DoesNotExist:
             # Just in case the signal didn't work, create it again safely
             from .models import Student
             import uuid
             student = Student.objects.create(user=request.user, student_id=str(uuid.uuid4())[:8])

        student.phone = request.POST.get('phone')
        student.address = request.POST.get('address')
        student.gender = request.POST.get('gender')
        student.save()

        # 2. CREATE ENROLLMENT
        selected_mode = request.POST.get('payment_mode')
        
        enrollment = Enrollment(
            student_user=request.user,
            course=course,
            payment_mode=selected_mode,
            amount_paid=5000 if selected_mode != 'full' else course.price
        )
        enrollment.save()
        
        return redirect('enroll_success', enrollment_id=enrollment.id) 

    context = {
        'course': course,
    }
    return render(request, 'enroll_payment.html', context)

def enroll_success(request, enrollment_id):
    # Fetch the enrollment record by ID
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    context = {
        'enrollment': enrollment,
        'course': enrollment.course
    }
    return render(request, 'enroll_success.html', context)


def guest_admission(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        # Get data from the form
        name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        address = request.POST.get('address')
        
        # Save to the new Request table
        AdmissionRequest.objects.create(
            full_name=name,
            phone=phone,
            email=email,
            address=address,
            course=course
        )
        
        # Show a success message
        return render(request, 'admission_sent.html')

    return render(request, 'guest_form.html', {'course': course})