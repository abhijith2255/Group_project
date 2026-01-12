from django.urls import path
from . import views

urlpatterns = [
    # Dashboard (If you moved it here, otherwise keep your existing dashboard url)
 
    # Leave Application (THIS IS THE MISSING LINK)
    path('leave/apply/', views.apply_leave, name='trainer_apply_leave'),
]