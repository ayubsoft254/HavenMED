from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import os
from PIL import Image

# Kenya Counties and Subcounties data
KENYA_COUNTIES = [
    ('baringo', 'Baringo'),
    ('bomet', 'Bomet'),
    ('bungoma', 'Bungoma'),
    ('busia', 'Busia'),
    ('elgeyo_marakwet', 'Elgeyo-Marakwet'),
    ('embu', 'Embu'),
    ('garissa', 'Garissa'),
    ('homa_bay', 'Homa Bay'),
    ('isiolo', 'Isiolo'),
    ('kajiado', 'Kajiado'),
    ('kakamega', 'Kakamega'),
    ('kericho', 'Kericho'),
    ('kiambu', 'Kiambu'),
    ('kilifi', 'Kilifi'),
    ('kirinyaga', 'Kirinyaga'),
    ('kisii', 'Kisii'),
    ('kisumu', 'Kisumu'),
    ('kitui', 'Kitui'),
    ('kwale', 'Kwale'),
    ('laikipia', 'Laikipia'),
    ('lamu', 'Lamu'),
    ('machakos', 'Machakos'),
    ('makueni', 'Makueni'),
    ('mandera', 'Mandera'),
    ('marsabit', 'Marsabit'),
    ('meru', 'Meru'),
    ('migori', 'Migori'),
    ('mombasa', 'Mombasa'),
    ('murang_a', 'Murang\'a'),
    ('nairobi', 'Nairobi'),
    ('nakuru', 'Nakuru'),
    ('nandi', 'Nandi'),
    ('narok', 'Narok'),
    ('nyamira', 'Nyamira'),
    ('nyandarua', 'Nyandarua'),
    ('nyeri', 'Nyeri'),
    ('samburu', 'Samburu'),
    ('siaya', 'Siaya'),
    ('taita_taveta', 'Taita-Taveta'),
    ('tana_river', 'Tana River'),
    ('tharaka_nithi', 'Tharaka-Nithi'),
    ('trans_nzoia', 'Trans Nzoia'),
    ('turkana', 'Turkana'),
    ('uasin_gishu', 'Uasin Gishu'),
    ('vihiga', 'Vihiga'),
    ('wajir', 'Wajir'),
    ('west_pokot', 'West Pokot'),
]

# Subcounties mapping (sample - you can expand this)
KENYA_SUBCOUNTIES = {
    'nairobi': [
        ('westlands', 'Westlands'),
        ('dagoretti_north', 'Dagoretti North'),
        ('dagoretti_south', 'Dagoretti South'),
        ('langata', 'Lang\'ata'),
        ('kibra', 'Kibra'),
        ('roysambu', 'Roysambu'),
        ('kasarani', 'Kasarani'),
        ('ruaraka', 'Ruaraka'),
        ('embakasi_south', 'Embakasi South'),
        ('embakasi_north', 'Embakasi North'),
        ('embakasi_central', 'Embakasi Central'),
        ('embakasi_east', 'Embakasi East'),
        ('embakasi_west', 'Embakasi West'),
        ('makadara', 'Makadara'),
        ('kamukunji', 'Kamukunji'),
        ('starehe', 'Starehe'),
        ('mathare', 'Mathare'),
    ],
    'kiambu': [
        ('gatundu_south', 'Gatundu South'),
        ('gatundu_north', 'Gatundu North'),
        ('juja', 'Juja'),
        ('thika_town', 'Thika Town'),
        ('ruiru', 'Ruiru'),
        ('githunguri', 'Githunguri'),
        ('kiambu_town', 'Kiambu Town'),
        ('kiambaa', 'Kiambaa'),
        ('kabete', 'Kabete'),
        ('kikuyu', 'Kikuyu'),
        ('limuru', 'Limuru'),
        ('lari', 'Lari'),
    ],
    'nakuru': [
        ('nakuru_town_east', 'Nakuru Town East'),
        ('nakuru_town_west', 'Nakuru Town West'),
        ('bahati', 'Bahati'),
        ('subukia', 'Subukia'),
        ('rongai', 'Rongai'),
        ('molo', 'Molo'),
        ('njoro', 'Njoro'),
        ('naivasha', 'Naivasha'),
        ('gilgil', 'Gilgil'),
        ('kuresoi_south', 'Kuresoi South'),
        ('kuresoi_north', 'Kuresoi North'),
    ],
    'mombasa': [
        ('changamwe', 'Changamwe'),
        ('jomba', 'Jomba'),
        ('kisauni', 'Kisauni'),
        ('nyali', 'Nyali'),
        ('likoni', 'Likoni'),
        ('mvita', 'Mvita'),
    ],
    # Add more counties and their subcounties as needed
}

def user_profile_photo_path(instance, filename):
    """Generate file path for user profile photos"""
    ext = filename.split('.')[-1]
    filename = f"{instance.id}_profile.{ext}"
    return os.path.join('profile_photos/', filename)

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
    
    # Location fields
    county = models.CharField(max_length=50, choices=KENYA_COUNTIES, blank=True)
    subcounty = models.CharField(max_length=50, blank=True)
    
    # Profile photo
    profile_photo = models.ImageField(
        upload_to=user_profile_photo_path,
        blank=True,
        null=True,
        help_text="Upload a profile photo (recommended size: 400x400px)"
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Resize profile photo if it exists
        if self.profile_photo:
            self.resize_profile_photo()
    
    def resize_profile_photo(self):
        """Resize profile photo to optimize storage and loading"""
        try:
            img = Image.open(self.profile_photo.path)
            
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Resize image
            max_size = (400, 400)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save optimized image
            img.save(self.profile_photo.path, "JPEG", quality=85, optimize=True)
        except Exception as e:
            # Log error but don't break the save process
            print(f"Error resizing profile photo: {e}")
    
    def get_profile_photo_url(self):
        """Get profile photo URL or return default avatar"""
        if self.profile_photo and hasattr(self.profile_photo, 'url'):
            return self.profile_photo.url
        else:
            # Return default avatar based on user type
            if self.user_type == 'healthcare_professional':
                return '/static/images/default_doctor_avatar.png'
            elif self.user_type in ['clinic', 'hospital']:
                return '/static/images/default_institution_avatar.png'
            else:
                return '/static/images/default_patient_avatar.png'
    
    def get_display_name(self):
        """Get display name for the user"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email.split('@')[0]

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
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            from datetime import date
            today = date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None

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
        ('dentistry', 'Dentistry'),
        ('ophthalmology', 'Ophthalmology'),
        ('ent', 'ENT (Ear, Nose, Throat)'),
        ('radiology', 'Radiology'),
        ('pathology', 'Pathology'),
        ('anesthesiology', 'Anesthesiology'),
        ('emergency_medicine', 'Emergency Medicine'),
        ('family_medicine', 'Family Medicine'),
        ('internal_medicine', 'Internal Medicine'),
        ('nursing', 'Nursing'),
        ('pharmacy', 'Pharmacy'),
        ('physiotherapy', 'Physiotherapy'),
        ('medical Officer', 'Medical Officer'),
        ('clinical_officer', 'Clinical Officer'),
        ('nutrition', 'Nutrition'),
        ('occupational_therapy', 'Occupational Therapy'),
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
    bio = models.TextField(blank=True, help_text="Brief professional biography")
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Consultation fee in KES")
    available_for_home_visits = models.BooleanField(default=False)
    available_for_virtual_consultations = models.BooleanField(default=True)
    
    # Professional ratings and reviews
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_reviews = models.PositiveIntegerField(default=0)
    
    # Availability
    is_available = models.BooleanField(default=True, help_text="Currently accepting new patients")
    
    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.get_specialization_display()}"
    
    def get_experience_level(self):
        """Get experience level description"""
        if self.years_of_experience < 2:
            return "Junior"
        elif self.years_of_experience < 5:
            return "Mid-level"
        elif self.years_of_experience < 10:
            return "Senior"
        else:
            return "Expert"

class InstitutionProfile(models.Model):
    INSTITUTION_TYPE_CHOICES = [
        ('clinic', 'Clinic'),
        ('hospital', 'Hospital'),
        ('diagnostic_center', 'Diagnostic Center'),
        ('pharmacy', 'Pharmacy'),
        ('laboratory', 'Laboratory'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='institution_profile')
    institution_type = models.CharField(max_length=20, choices=INSTITUTION_TYPE_CHOICES)
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
    operating_hours = models.TextField(help_text="Operating hours and days", blank=True)
    emergency_services = models.BooleanField(default=False)
    
    # Institution ratings and reviews
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    total_reviews = models.PositiveIntegerField(default=0)
    
    # Capacity and staff
    bed_capacity = models.PositiveIntegerField(null=True, blank=True, help_text="Number of beds (for hospitals)")
    staff_count = models.PositiveIntegerField(null=True, blank=True, help_text="Total number of staff")
    
    def __str__(self):
        return f"{self.institution_name} ({self.get_institution_type_display()})"
    
    def get_location_display(self):
        """Get formatted location string"""
        county_name = dict(KENYA_COUNTIES).get(self.user.county, self.user.county)
        return f"{self.user.subcounty}, {county_name}" if self.user.subcounty and county_name else county_name or "Location not specified"

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
        elif instance.user_type in ['clinic', 'hospital', 'diagnostic_center', 'pharmacy', 'laboratory']:
            InstitutionProfile.objects.create(
                user=instance,
                institution_type=instance.user_type
            )

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Ensure profile exists for all users"""
    try:
        if instance.user_type == 'patient' and not hasattr(instance, 'patient_profile'):
            PatientProfile.objects.create(user=instance)
        elif instance.user_type == 'healthcare_professional' and not hasattr(instance, 'healthcare_profile'):
            HealthcareProfessionalProfile.objects.create(user=instance)
        elif instance.user_type in ['clinic', 'hospital', 'diagnostic_center', 'pharmacy', 'laboratory'] and not hasattr(instance, 'institution_profile'):
            InstitutionProfile.objects.create(user=instance, institution_type=instance.user_type)
    except Exception as e:
        print(f"Error creating profile: {e}")