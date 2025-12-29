from django.urls import path
from . import views

urlpatterns = [
    # --- AUTHENTICATION ---
    path('', views.student_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # --- DASHBOARDS ---
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.student_profile, name='student_profile'),
    
    # --- TRAINER SECTION (Make sure these lines are present!) ---
    path('trainer/dashboard/', views.trainer_dashboard, name='trainer_dashboard'),
    path('trainer/batch/<int:batch_id>/', views.batch_students, name='batch_students'),
    
    # [NEW] These are the missing lines causing your error:
    path('trainer/batch/<int:batch_id>/leaves/', views.batch_leaves, name='batch_leaves'),
    path('leave/update/<int:leave_id>/<str:status>/', views.update_leave_status, name='update_leave_status'),

    # --- ACADEMICS & ATTENDANCE ---
    path('apply-leave/', views.apply_leave, name='apply_leave'),
    path('attendance/manage/', views.admin_mark_attendance, name='admin_attendance'),
    path('attendance/my-stats/', views.student_my_attendance, name='my_attendance'),
    path('courses/', views.course_list, name='course_list'),

    # --- ENROLLMENT & ONBOARDING ---
    path('enroll/<int:course_id>/', views.enroll_now, name='enroll_now'),
    path('onboarding/', views.complete_onboarding, name='complete_onboarding'),
    
    # --- ADMIN PANELS ---
    path('admin-panel/pending-requests/', views.pending_admissions_list, name='pending_admissions_list'),
    path('admin-panel/approve-guest/<int:pending_id>/', views.approve_guest, name='approve_guest'),
    
    # --- GUEST & STUDENT FEATURES ---
    path('guest-enroll/<int:course_id>/', views.guest_enroll_form, name='guest_enroll_form'),
    path('classroom/', views.my_classroom, name='my_classroom'),
    path('feedback/', views.submit_feedback, name='submit_feedback'),
    path('exams/', views.exam_portal, name='exam_portal'),
    path('placement-toggle/', views.toggle_placement, name='toggle_placement'),
]