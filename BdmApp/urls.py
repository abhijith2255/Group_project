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

    # Operations (Admissions)
    path('admissions/', views.admission_list, name='admission_list'),
    path('admissions/<int:student_id>/pay/', views.record_payment, name='record_payment'),

    # Batch Management
    path('batches/', views.batch_list, name='batch_list'),
    path('batches/add/', views.add_batch, name='add_batch'),
    path('batches/assign/', views.assign_student_batch, name='assign_student_batch'),

    # --- NEW BATCH DETAIL PATHS ADDED HERE ---
    path('batches/<int:batch_id>/', views.batch_detail, name='batch_detail'),
    path('batches/<int:batch_id>/edit/', views.edit_batch, name='edit_batch'),
    path('batches/<int:batch_id>/add-student/', views.add_student_to_specific_batch, name='add_student_to_specific_batch'),
    # -----------------------------------------

    # Trainers & Courses
    path('trainers/', views.trainer_list, name='trainer_list'),
    path('trainers/add/', views.add_trainer, name='add_trainer'),
    path('courses/', views.course_list, name='course_list'),
    path('courses/add/', views.add_course, name='add_course'),
]