from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.student_profile, name='student_profile'),
    path('apply-leave/', views.apply_leave, name='apply_leave'),
    path('attendance/manage/', views.admin_mark_attendance, name='admin_attendance'),
    path('attendance/my-stats/', views.student_my_attendance, name='my_attendance'),
    
]