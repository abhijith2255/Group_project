# TrainerApp/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from StudentApp.models import Trainer 
from .models import TrainerLeave
from .forms import TrainerLeaveForm

@login_required
def apply_leave(request):
    try:
        trainer = request.user.trainer
    except:
        messages.error(request, "Access Denied")
        return redirect('login')

    # Handle Form Submission
    if request.method == 'POST':
        form = TrainerLeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.trainer = trainer
            leave.save()
            messages.success(request, "Leave application submitted successfully!")
            return redirect('trainer_apply_leave')
    else:
        form = TrainerLeaveForm()

    # Fetch History
    leave_history = TrainerLeave.objects.filter(trainer=trainer).order_by('-applied_on')

    return render(request, 'trainer/apply_leave.html', {
        'form': form,
        'leave_history': leave_history
    })