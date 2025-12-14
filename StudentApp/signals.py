from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import AdmissionRequest, Student

@receiver(post_save, sender=AdmissionRequest)
def create_student_on_approval(sender, instance, created, **kwargs):
    # Check if the admin has marked it as processed
    if instance.is_processed:
        
        # 1. Check if a User with this email already exists to prevent duplicates
        if not User.objects.filter(username=instance.email).exists():
            
            # 2. Create the User Account
            # We use their email as username and phone number as the temporary password
            new_user = User.objects.create_user(
                username=instance.email, 
                email=instance.email, 
                password=instance.phone  # Password = Phone Number
            )
            new_user.first_name = instance.full_name
            new_user.save()

            # 3. Create the Student Profile
            Student.objects.create(
                user=new_user,
                student_id=f"STU-{new_user.id + 1000}", # Generates ID like STU-1001
                course=instance.course,
                phone=instance.phone,
                address=instance.address,
                is_fee_paid=False # Default to false until they pay
            )
            print(f"Student {instance.full_name} created successfully!")