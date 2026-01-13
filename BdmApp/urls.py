from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.bdm_dashboard, name='bdm_dashboard'),

    # Leads
    path('leads/', views.lead_list, name='lead_list'),
    path('leads/<int:lead_id>/', views.lead_detail, name='lead_detail'),
    path('leads/add/', views.add_lead, name='add_lead'),
    path('leads/<int:lead_id>/convert/', views.convert_lead, name='convert_lead'),

    # Operations (Admissions & Onboarding)
    path('admissions/', views.admission_list, name='admission_list'),
    path('admissions/<int:student_id>/pay/', views.record_payment, name='record_payment'),
    
    # --- ONBOARDING PATHS ---
    path('onboarding/', views.onboarding_list, name='onboarding_list'), # <--- THIS WAS MISSING
    path('admissions/<int:student_id>/onboard/', views.onboarding_checklist, name='onboarding_checklist'),

    # Batch Management
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/add/', views.add_batch, name='add_batch'),
    path('batches/assign/', views.assign_student_batch, name='assign_student_batch'),

    # Batch Details & Editing
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
    path('contact-us/', views.public_enquiry, name='public_enquiry'),
    path('enquiries/', views.enquiry_list, name='enquiry_list'),
    path('enquiry/convert/<int:enquiry_id>/', views.convert_enquiry_to_lead, name='convert_enquiry_to_lead'),
    
]
