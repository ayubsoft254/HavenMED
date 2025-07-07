from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ('patient', 'Patient'),
        ('healthcare_professional', 'Healthcare Professional'),
        ('clinic', 'Clinic'),
        ('hospital', 'Hospital'),
    ]
    
    email = models.EmailField(_('email address'), unique=True)
    user_type = models.CharField(max_length=25, choices=USER_TYPE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email

class PatientProfile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    medical_history = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    address = models.TextField(blank=True)
    
    def __str__(self):
        return f"Patient: {self.user.get_full_name()}"

class HealthcareProfessionalProfile(models.Model):
    SPECIALIZATION_CHOICES = [
        ('general_practice', 'General Practice'),
        ('cardiology', 'Cardiology'),
        ('dermatology', 'Dermatology'),
        ('pediatrics', 'Pediatrics'),
        ('psychiatry', 'Psychiatry'),
        ('surgery', 'Surgery'),
        ('gynecology', 'Gynecology'),
        ('orthopedics', 'Orthopedics'),
        ('neurology', 'Neurology'),
        ('oncology', 'Oncology'),
        ('other', 'Other'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='healthcare_profile')
    specialization = models.CharField(max_length=50, choices=SPECIALIZATION_CHOICES)
    years_of_experience = models.PositiveIntegerField()
    kmpdu_license_number = models.CharField(max_length=50, unique=True)
    
    # Document uploads
    national_id = models.ImageField(upload_to='documents/healthcare_professionals/ids/')
    kmpdu_license = models.ImageField(upload_to='documents/healthcare_professionals/licenses/')
    
    # Additional details
    bio = models.TextField(blank=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    available_for_home_visits = models.BooleanField(default=False)
    available_for_virtual_consultations = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialization}"

class InstitutionProfile(models.Model):
    INSTITUTION_TYPE_CHOICES = [
        ('clinic', 'Clinic'),
        ('hospital', 'Hospital'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='institution_profile')
    institution_type = models.CharField(max_length=10, choices=INSTITUTION_TYPE_CHOICES)
    institution_name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True)
    
    # Document uploads
    medical_license = models.ImageField(upload_to='documents/institutions/licenses/')
    
    # Contact and location details
    physical_address = models.TextField()
    postal_address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    description = models.TextField(blank=True)
    
    # Services
    services_offered = models.TextField(help_text="List the services your institution offers")
    operating_hours = models.TextField(help_text="Operating hours and days")
    emergency_services = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.institution_name} ({self.institution_type})"

# Signal to create profiles automatically
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 'patient':
            PatientProfile.objects.create(user=instance)
            instance.is_approved = True  # Patients are auto-approved
            instance.save()
        elif instance.user_type == 'healthcare_professional':
            HealthcareProfessionalProfile.objects.create(user=instance)
        elif instance.user_type in ['clinic', 'hospital']:
            InstitutionProfile.objects.create(
                user=instance,
                institution_type=instance.user_type
            )