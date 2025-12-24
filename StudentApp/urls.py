from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.student_profile, name='student_profile'),
    
    # --- ACADEMICS & ATTENDANCE ---
    path('apply-leave/', views.apply_leave, name='apply_leave'),
    path('attendance/manage/', views.admin_mark_attendance, name='admin_attendance'),
    path('attendance/my-stats/', views.student_my_attendance, name='my_attendance'),
    path('courses/', views.course_list, name='course_list'),

    # --- NEW: ENROLLMENT & ONBOARDING ---
    # Triggered when student clicks "Take This Course"
    path('enroll/<int:course_id>/', views.enroll_now, name='enroll_now'),
    
    # The form for Fee Payment and Document Upload
    path('onboarding/', views.complete_onboarding, name='complete_onboarding'),
    path('admin-panel/pending-requests/', views.pending_admissions_list, name='pending_admissions_list'),
    path('admin-panel/approve-guest/<int:pending_id>/', views.approve_guest, name='approve_guest'),
    # In StudentApp/urls.py
    path('guest-enroll/<int:course_id>/', views.guest_enroll_form, name='guest_enroll_form'),
    path('classroom/', views.my_classroom, name='my_classroom'),
    path('feedback/', views.submit_feedback, name='submit_feedback'),
    path('exams/', views.exam_portal, name='exam_portal'),
    path('placement-toggle/', views.toggle_placement, name='toggle_placement'),
]