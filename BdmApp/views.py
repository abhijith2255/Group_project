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

# --- IMPORT MODELS ---
from .models import Lead, LeadSource, Interaction
from StudentApp.models import Student, Course, FeePayment, Batch,Trainer

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
    """Create a new lead manually"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        city = request.POST.get('city')
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
    """Logic to update a student's batch"""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        batch_id = request.POST.get('batch_id')
        
        student = get_object_or_404(Student, id=student_id)
        batch = get_object_or_404(Batch, id=batch_id)
        
        if student.course != batch.course:
            messages.error(request, f"Error: Student is in {student.course.name} but Batch is for {batch.course.name}")
        else:
            student.batch = batch
            student.save()
            messages.success(request, f"Assigned {student.user.first_name} to {batch.name}")
            
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

@login_required
@user_passes_test(is_bdm)
def add_course(request):
    """Add a new course with image"""
    if request.method == 'POST':
        name = request.POST.get('name')
        duration = request.POST.get('duration')
        price = request.POST.get('price')
        description = request.POST.get('description')
        
        # GET THE IMAGE
        image = request.FILES.get('image') 

        try:
            Course.objects.create(
                name=name,
                duration=duration,
                price=price,
                description=description,
                image=image  # Save the image
            )
            messages.success(request, f"Course '{name}' added successfully!")
            return redirect('course_list')
            
        except Exception as e:
            messages.error(request, f"Error adding course: {str(e)}")
            return redirect('add_course')

    return render(request, 'bdm/add_course.html')