from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import LeaveApplication, Student
from .forms import LeaveForm
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