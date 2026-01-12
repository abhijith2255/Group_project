from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.db import transaction
import random
import json
import string # Added for robust password generation
from dateutil.relativedelta import relativedelta # You might need to install this: pip install python-dateutil
import datetime

from TrainerApp.models import TrainerLeave
# Make sure to import FeeInstallment at the top
# --- IMPORT MODELS ---
from .models import Lead, LeadSource, Interaction,FeeInstallment
from StudentApp.models import Student, Course, FeePayment, Batch, StudentFeedback,Trainer

# --- ACCESS CONTROL ---
def is_bdm(user):
    # Checks if user is Staff or Superuser
    return user.is_staff or user.is_superuser

# ==========================================
# 1. DASHBOARD VIEW
# ==========================================
@login_required
@user_passes_test(is_bdm)
def bdm_dashboard(request):
    # 1. Basic Counts
    total_students = Student.objects.count()
    total_batches = Batch.objects.count()
    total_courses = Course.objects.count()   # <--- New
    total_trainers = Trainer.objects.count() # <--- New

    # 2. Total Revenue (Collected)
    total_revenue = FeePayment.objects.aggregate(total=Sum('amount'))['total'] or 0

    # 3. Pending Fees Calculation
    pending_students = Student.objects.filter(is_fee_paid=False).select_related('course')
    total_pending_amount = 0
    
    for student in pending_students:
        if student.course:
            paid_agg = student.feepayment_set.aggregate(total=Sum('amount'))
            paid = paid_agg['total'] or 0
            balance = student.course.price - paid
            if balance > 0:
                total_pending_amount += balance

    # 4. Chart Data
    six_months_ago = timezone.now() - timezone.timedelta(days=180)
    admission_data_query = Lead.objects.filter(status='CONVERTED', updated_at__gte=six_months_ago).annotate(month=TruncMonth('updated_at')).values('month').annotate(count=Count('id')).order_by('month')

    labels = []
    data = []
    for entry in admission_data_query:
        labels.append(entry['month'].strftime("%b"))
        data.append(entry['count'])

    context = {
        'total_students': total_students,
        'total_batches': total_batches,
        'total_courses': total_courses,       # <--- Pass to template
        'total_trainers': total_trainers,     # <--- Pass to template
        'total_revenue': total_revenue,
        'total_pending_amount': total_pending_amount,
        'admission_labels': json.dumps(labels),
        'admission_data': json.dumps(data),
    }
    return render(request, 'bdm/dashboard.html', context)

# ==========================================
# 2. LEAD LIST VIEW
# ==========================================
@login_required
@user_passes_test(is_bdm)
def lead_list(request):
    leads = Lead.objects.all().order_by('-created_at')
    
    # -- Filter Logic --
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if status:
        leads = leads.filter(status=status)
    
    if search:
        leads = leads.filter(
            Q(first_name__icontains=search) | 
            Q(email__icontains=search) | 
            Q(phone__icontains=search)
        )

    return render(request, 'bdm/lead_list.html', {'leads': leads})

# ==========================================
# 3. LEAD DETAIL & INTERACTION LOG
# ==========================================
@login_required
@user_passes_test(is_bdm)
def lead_detail(request, lead_id):
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Handle "Add Interaction" Form Submission
    if request.method == 'POST':
        i_type = request.POST.get('type')
        notes = request.POST.get('notes')
        next_date = request.POST.get('next_follow_up')
        
        # Save Interaction
        Interaction.objects.create(
            lead=lead,
            counselor=request.user,
            interaction_type=i_type,
            notes=notes,
            next_follow_up=next_date if next_date else None
        )
        
        # Auto-update status if it was 'NEW'
        if lead.status == 'NEW':
            lead.status = 'CONTACTED'
            lead.save()
            
        messages.success(request, "Interaction logged successfully.")
        return redirect('lead_detail', lead_id=lead.id)

    # Fetch History
    interactions = lead.interactions.all().order_by('-interaction_date')
    
    return render(request, 'bdm/lead_detail.html', {
        'lead': lead,
        'interactions': interactions
    })

# ==========================================
# 4. CONVERT LEAD -> STUDENT (ROBUST VERSION)
# ==========================================
@login_required
@user_passes_test(is_bdm)
@transaction.atomic
def convert_lead(request, lead_id):
    # 1. Get the lead
    lead = get_object_or_404(Lead, id=lead_id)
    
    if lead.status == 'CONVERTED':
        messages.warning(request, "This lead is already a student.")
        return redirect('lead_detail', lead_id=lead.id)

    # --- REMOVED TRY/EXCEPT BLOCK SO WE CAN SEE ERRORS ---

    # 2. Generate Username
    clean_name = lead.first_name.lower().replace(" ", "") or "student"
    username = f"{clean_name}{random.randint(100, 999)}"
    while User.objects.filter(username=username).exists():
        username = f"{clean_name}{random.randint(1000, 9999)}"

    # 3. Generate Details
    password = "Student@123"
    current_year = timezone.now().year
    unique_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    student_id_code = f"STU-{current_year}-{unique_code}"

    # 4. Create User
    user = User.objects.create_user(
        username=username,
        email=lead.email,
        password=password,
        first_name=lead.first_name,
        last_name=lead.last_name
    )

    # 5. Create Student
    Student.objects.create(
        user=user,
        student_id=student_id_code,
        course=lead.course_interested,
        phone=lead.phone,
        address=lead.city,
        is_fee_paid=False,
        documents_verified=False
    )

    # 6. Update Lead
    lead.status = 'CONVERTED'
    lead.save()

    # 7. Render Success Page
    context = {
        'student_name': f"{lead.first_name} {lead.last_name}",
        'student_id': student_id_code,
        'username': username,
        'password': password,
        'course': lead.course_interested.name,
        'phone': lead.phone
    }
    return render(request, 'bdm/conversion_success.html', context)

# ==========================================
# 5. ADMISSIONS & FEE MANAGEMENT
# ==========================================
@login_required
@user_passes_test(is_bdm)
def admission_list(request):
    """List of all converted students with fee status"""
    students = Student.objects.all().select_related('course', 'user').order_by('-id')
    
    student_data = []
    
    for student in students:
        total_fee = student.course.price
        
        # Aggregate total paid from FeePayment table
        paid_agg = student.feepayment_set.aggregate(total=Sum('amount'))
        paid_amount = paid_agg['total'] or 0
        
        balance = total_fee - paid_amount
        
        student_data.append({
            'obj': student,
            'total_fee': total_fee,
            'paid_amount': paid_amount,
            'balance': balance,
            'status': 'Paid' if balance <= 0 else 'Pending'
        })

    return render(request, 'bdm/admission_list.html', {'students': student_data})

@login_required
@user_passes_test(is_bdm)
def record_payment(request, student_id):
    """View to record a payment for a specific student"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        mode = request.POST.get('mode') # CASH, UPI, BANK
        
        if amount:
            FeePayment.objects.create(
                student=student,
                amount=amount,
                mode=mode
            )
            
            # Check if full fee is paid
            total_fee = student.course.price
            paid_so_far = student.feepayment_set.aggregate(total=Sum('amount'))['total'] or 0
            
            if paid_so_far >= total_fee:
                student.is_fee_paid = True
                student.save()
                
            messages.success(request, f"Payment of {amount} recorded for {student.user.first_name}")
        
    return redirect('admission_list')

# ==========================================
# 6. ADD LEAD MANUALLY
# ==========================================
@login_required
@user_passes_test(is_bdm)
def add_lead(request):
    """Create a new lead manually (Updated with new fields)"""
    if request.method == 'POST':
        # Basic Info
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        city = request.POST.get('city')
        
        # New Fields
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        qualification = request.POST.get('qualification')
        payment_type = request.POST.get('payment_type')

        # Relations
        course_id = request.POST.get('course_id')
        source_id = request.POST.get('source_id')
        status = request.POST.get('status')

        try:
            course = Course.objects.get(id=course_id)
            source = LeadSource.objects.get(id=source_id) if source_id else None

            Lead.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                city=city,
                # Save new fields
                age=age if age else None,
                gender=gender,
                qualification=qualification,
                payment_type=payment_type,
                # Save relations
                course_interested=course,
                source=source,
                status=status,
                assigned_to=request.user 
            )
            
            messages.success(request, f"Lead '{first_name}' added successfully!")
            return redirect('lead_list')

        except Exception as e:
            messages.error(request, f"Error adding lead: {str(e)}")
            return redirect('add_lead')

    courses = Course.objects.all()
    sources = LeadSource.objects.filter(is_active=True)
    
    return render(request, 'bdm/add_lead.html', {
        'courses': courses, 
        'sources': sources
    })
# ==========================================
# 7. BATCH MANAGEMENT
# ==========================================
@login_required
@user_passes_test(is_bdm)
def batch_list(request):
    """List all batches with student count and status"""
    batches = Batch.objects.annotate(student_count=Count('students')).order_by('-start_date')
    
    unassigned_students = Student.objects.filter(batch__isnull=True).select_related('user', 'course')
    
    return render(request, 'bdm/batch_list.html', {
        'batches': batches,
        'unassigned_students': unassigned_students
    })

@login_required
@user_passes_test(is_bdm)
def assign_student_batch(request):
    """Assign a student to a specific batch"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        batch_id = request.POST.get('batch_id')

        try:
            student = Student.objects.get(id=student_id)
            batch = Batch.objects.get(id=batch_id)

            # 1. Validation: Check if Course Matches
            # We shouldn't put a 'Python' student in a 'Java' batch
            if student.course != batch.course:
                messages.error(request, f"Error: Student is enrolled in {student.course.name}, but Batch is {batch.course.name}.")
                return redirect('batch_list')

            # 2. Assign Batch
            student.batch = batch
            student.save()

            messages.success(request, f"Successfully assigned {student.user.first_name} to {batch.name}")
            return redirect('batch_list')

        except Exception as e:
            messages.error(request, f"Assignment Failed: {str(e)}")
            return redirect('batch_list')

    return redirect('batch_list')


# ==========================================
# 8. TRAINER MANAGEMENT
# ==========================================
@login_required
@user_passes_test(is_bdm)
def trainer_list(request):
    """List all trainers"""
    trainers = Trainer.objects.all().order_by('-joined_at')
    return render(request, 'bdm/trainer_list.html', {'trainers': trainers})

@login_required
@user_passes_test(is_bdm)
def add_trainer(request):
    """Add a new trainer with auto-generated login"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        designation = request.POST.get('designation')
        expertise = request.POST.get('expertise')
        bio = request.POST.get('bio')
        profile_image = request.FILES.get('profile_image')

        try:
            # 1. Create Django User for Login
            # Format: rahul.852
            username = f"{first_name.lower()}.{random.randint(100, 999)}"
            password = "Trainer@123" # Default password
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # 2. Create Trainer Profile
            Trainer.objects.create(
                user=user,
                full_name=f"{first_name} {last_name}",
                designation=designation,
                expertise=expertise,
                bio=bio,
                profile_image=profile_image
            )

            # 3. RENDER SUCCESS PAGE (New Code)
            context = {
                'trainer_name': f"{first_name} {last_name}",
                'designation': designation,
                'username': username,
                'password': password,
                'email': email
            }
            return render(request, 'bdm/trainer_success.html', context)

        except Exception as e:
            messages.error(request, f"Error adding trainer: {str(e)}")
            return redirect('add_trainer')

    return render(request, 'bdm/add_trainer.html')

@login_required
@user_passes_test(is_bdm)
def course_list(request):
    """Show all courses"""
    courses = Course.objects.all().order_by('name')
    return render(request, 'bdm/course_list.html', {'courses': courses})

# BdmApp/views.py

@login_required
@user_passes_test(is_bdm)
def add_course(request):
    if request.method == 'POST':
        # 1. Capture Data
        name = request.POST.get('name')
        duration = request.POST.get('duration')
        price = request.POST.get('price')
        description = request.POST.get('description')
        trainer_id = request.POST.get('trainer_id')
        
        image = request.FILES.get('image') # Requires enctype="multipart/form-data" in HTML

        # 2. Process Logic (NO TRY/EXCEPT BLOCK)
        trainer_obj = None
        if trainer_id and trainer_id.strip() != "":
            trainer_obj = Trainer.objects.get(id=trainer_id)

        # 3. Create Course
        Course.objects.create(
            name=name,
            duration=duration,
            price=price,
            description=description,
            image=image, 
            trainer=trainer_obj
        )
        
        messages.success(request, f"Course '{name}' added successfully!")
        return redirect('course_list')

    # GET Request
    trainers = Trainer.objects.all()
    return render(request, 'bdm/add_course.html', {'trainers': trainers})
@login_required
@user_passes_test(is_bdm)
def add_batch(request):
    """Create a new batch (Debug Version)"""
    if request.method == 'POST':
        name = request.POST.get('name')
        course_id = request.POST.get('course_id')
        trainer_id = request.POST.get('trainer_id')
        start_date = request.POST.get('start_date')
        time_slot = request.POST.get('time_slot')

        # --- NO ERROR HANDLING: SHOW ME THE ERROR ---
        
        # 1. Get Course (This must exist)
        course = Course.objects.get(id=course_id)

        # 2. Get Trainer (Handle Empty Selection)
        trainer = None
        if trainer_id and trainer_id.strip() != "":
            trainer = Trainer.objects.get(id=trainer_id)

        # 3. Create the Batch
        Batch.objects.create(
            name=name,
            course=course,
            trainer=trainer,
            start_date=start_date,
            time_slot=time_slot
        )
        
        messages.success(request, f"Batch '{name}' created successfully!")
        return redirect('batch_list')

    # GET Request
    courses = Course.objects.all()
    trainers = Trainer.objects.all()

    return render(request, 'bdm/add_batch.html', {
        'courses': courses,
        'trainers': trainers
    })
# BdmApp/views.py

@login_required
@user_passes_test(is_bdm)
def batch_detail(request, batch_id):
    """Show details + Handle Edit + Handle Add Student"""
    batch = get_object_or_404(Batch, id=batch_id)
    students = batch.students.all()
    
    # Get students who are in this course but NOT in any batch
    available_students = Student.objects.filter(course=batch.course, batch__isnull=True)
    
    # Get all trainers for the Edit Modal dropdown
    all_trainers = Trainer.objects.all()
    
    return render(request, 'bdm/batch_detail.html', {
        'batch': batch, 
        'students': students,
        'available_students': available_students,
        'all_trainers': all_trainers # Needed for Edit Modal
    })

@login_required
@user_passes_test(is_bdm)
def edit_batch(request, batch_id):
    """Process the Edit Modal form"""
    if request.method == 'POST':
        batch = get_object_or_404(Batch, id=batch_id)
        
        batch.name = request.POST.get('name')
        batch.start_date = request.POST.get('start_date')
        batch.time_slot = request.POST.get('time_slot')
        
        trainer_id = request.POST.get('trainer_id')
        if trainer_id:
            batch.trainer = Trainer.objects.get(id=trainer_id)
        else:
            batch.trainer = None
            
        batch.save()
        messages.success(request, "Batch details updated!")
        
    # Redirect back to the detail page
    return redirect('batch_detail', batch_id=batch_id)

@login_required
@user_passes_test(is_bdm)
def add_student_to_specific_batch(request, batch_id):
    """Process the Add Student Modal form"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        batch = get_object_or_404(Batch, id=batch_id)
        student = get_object_or_404(Student, id=student_id)
        
        student.batch = batch
        student.save()
        messages.success(request, f"Added {student.user.first_name} to batch.")
        
    return redirect('batch_detail', batch_id=batch_id)

# BdmApp/views.py

@login_required
@user_passes_test(is_bdm)
def onboarding_checklist(request, student_id):
    """Manage student onboarding tasks"""
    student = get_object_or_404(Student, id=student_id)

    # Define standard tasks (You could make a model for this later if needed)
    default_tasks = [
        {'id': 'fee', 'label': 'Registration Fee Paid', 'completed': student.is_fee_paid},
        {'id': 'id_card', 'label': 'ID Card Issued', 'completed': False},
        {'id': 'lms', 'label': 'LMS Access Granted', 'completed': False},
        {'id': 'kit', 'label': 'Welcome Kit Given', 'completed': False},
        {'id': 'whatsapp', 'label': 'Added to WhatsApp Group', 'completed': False},
    ]

    if request.method == 'POST':
        # In a real app, you would save these statuses to a model.
        # For now, we will simulate completing the onboarding.
        
        # Example: Mark student as 'Active' if they weren't already
        completed_tasks = request.POST.getlist('tasks')
        
        if len(completed_tasks) >= 3: # If mostly done
            messages.success(request, f"Onboarding updated for {student.user.first_name}!")
            return redirect('admission_list')
        else:
            messages.warning(request, "Please complete key tasks before finishing.")

    return render(request, 'bdm/onboarding.html', {
        'student': student,
        'tasks': default_tasks
    })
@login_required
@user_passes_test(is_bdm)
def onboarding_list(request):
    """Show list of students for onboarding"""
    # You might want to filter this later (e.g., only students who paid fees)
    students = Student.objects.all().order_by('-id')
    return render(request, 'bdm/onboarding_list.html', {'students': students})

# BdmApp/views.py

@login_required
@user_passes_test(is_bdm)
def student_detail(request, student_id):
    """View full profile of a student"""
    student = get_object_or_404(Student, id=student_id)
    
    # 1. Get Course Price
    # Your model uses 'price', so we use student.course.price
    total_fee = student.course.price 
    
    # 2. Calculate Total Paid
    # We look at the 'FeePayment' table (accessed via feepayment_set) and sum the 'amount'
    payment_data = student.feepayment_set.aggregate(total=Sum('amount'))
    
    # If no payments exist, the result is None, so we default to 0
    paid_amount = payment_data['total'] or 0

    # 3. Calculate Balance
    balance = total_fee - paid_amount
    
    return render(request, 'bdm/student_detail.html', {
        'student': student,
        'total_fee': total_fee,
        'paid_amount': paid_amount,
        'balance': balance
    })
# BdmApp/views.py

@login_required
@user_passes_test(is_bdm)
def edit_student(request, student_id):
    """Edit student profile details"""
    student = get_object_or_404(Student, id=student_id)
    courses = Course.objects.all()
    batches = Batch.objects.filter(course=student.course) if student.course else Batch.objects.none()

    if request.method == 'POST':
        # 1. Update User Model (Name, Email)
        user = student.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()

        # 2. Update Student Model (Phone, Address, etc.)
        student.phone = request.POST.get('phone')
        student.address = request.POST.get('address')
        student.gender = request.POST.get('gender')
        
        # Handle Date of Birth (check if empty)
        dob = request.POST.get('dob')
        if dob:
            student.date_of_birth = dob

        # Handle Course & Batch changes
        course_id = request.POST.get('course')
        batch_id = request.POST.get('batch')
        
        if course_id:
            student.course_id = course_id
        if batch_id:
            student.batch_id = batch_id
            
        student.save()
        
        messages.success(request, "Student profile updated successfully!")
        return redirect('student_detail', student_id=student.id)

    # If GET request, show the form
    # We fetch all courses to populate dropdown
    all_courses = Course.objects.all()
    # We fetch batches related to the current course
    if student.course:
        related_batches = Batch.objects.filter(course=student.course)
    else:
        related_batches = Batch.objects.all()

    return render(request, 'bdm/edit_student.html', {
        'student': student,
        'courses': all_courses,
        'batches': related_batches
    })

@login_required
@user_passes_test(is_bdm)
def record_payment(request, student_id):
    """Record a payment (Down Payment) and optionally generate EMIs"""
    student = get_object_or_404(Student, id=student_id)
    
    if request.method == 'POST':
        try:
            amount = float(request.POST.get('amount', 0)) # Default to 0 if empty
        except ValueError:
            amount = 0.0
            
        mode = request.POST.get('mode') # CASH, UPI, EMI
        installments_count = request.POST.get('installments')
        
        # 1. Record the Immediate Payment (Down Payment)
        if amount > 0:
            FeePayment.objects.create(
                student=student,
                amount=amount,
                mode=mode
            )
        
        # 2. IF EMI: Generate Future Installments
        if mode == 'EMI' and installments_count:
            try:
                count = int(installments_count)
            except ValueError:
                count = 1

            # Calculate Remaining Balance
            total_fee = float(student.course.price)
            # This sum now INCLUDES the payment we just recorded above
            paid_so_far = student.feepayment_set.aggregate(total=Sum('amount'))['total'] or 0
            
            balance = total_fee - float(paid_so_far)
            
            if balance > 0:
                emi_amount = balance / count
                today = datetime.date.today()
                
                # Loop to create future records
                for i in range(1, count + 1):
                    # Calculate date: Today + i months
                    next_date = today + relativedelta(months=+i)
                    
                    FeeInstallment.objects.create(
                        student=student,
                        amount=emi_amount,
                        due_date=next_date,
                        is_paid=False
                    )
                
                messages.success(request, f"Payment recorded & {count} EMIs generated!")
            else:
                messages.warning(request, "Payment recorded, but no balance left for EMIs.")

        # 3. Check if full fee is paid (Standard Logic)
        total_fee = student.course.price
        paid_final = student.feepayment_set.aggregate(total=Sum('amount'))['total'] or 0
        
        # Use a small buffer for float comparison errors
        if paid_final >= (float(total_fee) - 1.0):
            student.is_fee_paid = True
            student.save()
            
        if mode != 'EMI':
            messages.success(request, f"Payment of ₹{amount} recorded successfully.")
            
        return redirect('admission_list')
    
    return redirect('admission_list')

# BdmApp/views.py

@login_required
@user_passes_test(is_bdm)
def edit_course(request, course_id):
    """Edit an existing course"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        # 1. Update Fields
        course.name = request.POST.get('name')
        course.duration = request.POST.get('duration')
        course.price = request.POST.get('price')
        course.description = request.POST.get('description')
        
        # 2. Update Trainer
        trainer_id = request.POST.get('trainer_id')
        if trainer_id:
            course.trainer = Trainer.objects.get(id=trainer_id)
        else:
            course.trainer = None # Allow removing trainer
            
        # 3. Update Image (Only if a new one is uploaded)
        new_image = request.FILES.get('image')
        if new_image:
            course.image = new_image
            
        course.save()
        messages.success(request, f"Course '{course.name}' updated successfully!")
        return redirect('course_list')

    # GET Request: Show form with existing data
    trainers = Trainer.objects.all()
    return render(request, 'bdm/edit_course.html', {
        'course': course, 
        'trainers': trainers
    })

@login_required
@user_passes_test(is_bdm)
def feedback_list(request):
    """List all student feedbacks"""
    feedbacks = StudentFeedback.objects.select_related('student__user').order_by('-date_submitted')
    return render(request, 'bdm/feedback_list.html', {'feedbacks': feedbacks})


@login_required
@user_passes_test(is_bdm)
def manage_trainer_leaves(request):
    """List all leave requests"""
    # Separate lists for clearer UI
    pending_leaves = TrainerLeave.objects.filter(status='Pending').order_by('start_date')
    history_leaves = TrainerLeave.objects.exclude(status='Pending').order_by('-applied_on')[:10] # Show last 10
    
    return render(request, 'bdm/manage_leaves.html', {
        'pending_leaves': pending_leaves,
        'history_leaves': history_leaves
    })

@login_required
@user_passes_test(is_bdm)
def update_leave_status(request, leave_id, status):
    """Approve or Reject a leave"""
    leave = get_object_or_404(TrainerLeave, id=leave_id)
    
    if status in ['Approved', 'Rejected']:
        leave.status = status
        leave.save()
        
        # Optional: Add a success message
        action = "Approved" if status == 'Approved' else "Rejected"
        messages.success(request, f"Leave for {leave.trainer.full_name} has been {action}.")
        
    return redirect('manage_trainer_leaves')