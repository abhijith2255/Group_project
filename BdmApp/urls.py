from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.bdm_dashboard, name='bdm_dashboard'),

    # Leads
    path('leads/', views.lead_list, name='lead_list'),
    path('leads/<int:lead_id>/', views.lead_detail, name='lead_detail'),
    path('leads/add/', views.add_lead, name='add_lead'),
    
    # --- DELETE OR COMMENT OUT THIS LINE (The duplicate) ---
    # path('leads/<int:lead_id>/convert/', views.convert_lead, name='convert_lead'), 

    # Operations
    path('admissions/', views.admission_list, name='admission_list'),
    path('admissions/<int:student_id>/pay/', views.record_payment, name='record_payment'),
    
    # Onboarding
    path('onboarding/', views.onboarding_list, name='onboarding_list'),
    path('admissions/<int:student_id>/onboard/', views.onboarding_checklist, name='onboarding_checklist'),

    # Batch Management
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/add/', views.add_batch, name='add_batch'),
    path('batches/assign/', views.assign_student_batch, name='assign_student_batch'),

    # Batch Details
    path('batches/<int:batch_id>/', views.batch_detail, name='batch_detail'),
    path('batches/<int:batch_id>/edit/', views.edit_batch, name='edit_batch'),
    path('batches/<int:batch_id>/add-student/', views.add_student_to_specific_batch, name='add_student_to_specific_batch'),

    # Trainers & Courses
    path('trainers/', views.trainer_list, name='trainer_list'),
    path('trainers/add/', views.add_trainer, name='add_trainer'),
    path('courses/', views.course_list, name='bdm_course_list'),
    path('courses/add/', views.add_course, name='add_course'),
    path('courses/edit/<int:course_id>/', views.edit_course, name='edit_course'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    path('students/<int:student_id>/edit/', views.edit_student, name='edit_student'),
    path('feedbacks/', views.feedback_list, name='feedback_list'),
    path('leaves/manage/', views.manage_trainer_leaves, name='manage_trainer_leaves'),
    path('leaves/update/<int:leave_id>/<str:status>/', views.update_leave_status, name='update_trainer_leave'),
    
    # Enquiries
    path('enquiry/', views.enquiry_form, name='enquiry_form'),
    
    # --- THIS IS THE CORRECT ONE (Keep this) ---
    path('lead/convert/<int:lead_id>/', views.register_student_from_lead, name='convert_lead'),
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/pending-emis/', views.pending_emi_list, name='pending_emi_list'),
]