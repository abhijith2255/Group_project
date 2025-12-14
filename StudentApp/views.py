from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import LeaveApplication,Student,Attendance,Course
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
@login_required(login_url='login')
def dashboard(request):
    try:
        # Try to find the student profile linked to this user
        student_profile = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        student_profile = None

    context = {
        'student': student_profile,
        'user': request.user
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