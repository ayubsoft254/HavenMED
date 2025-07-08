from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime
import uuid

User = get_user_model()

class AvailabilitySlot(models.Model):
    """Healthcare professional availability slots"""
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    healthcare_professional = models.ForeignKey(
        'accounts.HealthcareProfessionalProfile',
        on_delete=models.CASCADE,
        related_name='availability_slots'
    )
    day_of_week = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.PositiveIntegerField(default=30, help_text="Duration in minutes")
    is_active = models.BooleanField(default=True)
    
    # Service types available during this slot
    virtual_consultations_available = models.BooleanField(default=True)
    home_visits_available = models.BooleanField(default=False)
    in_person_available = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['healthcare_professional', 'day_of_week', 'start_time']
        ordering = ['day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.healthcare_professional.user.get_display_name()} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

class SpecialAvailability(models.Model):
    """Special availability for specific dates (overrides regular schedule)"""
    healthcare_professional = models.ForeignKey(
        'accounts.HealthcareProfessionalProfile',
        on_delete=models.CASCADE,
        related_name='special_availability'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.PositiveIntegerField(default=30)
    is_available = models.BooleanField(default=True)  # False for blocking dates
    
    # Service types
    virtual_consultations_available = models.BooleanField(default=True)
    home_visits_available = models.BooleanField(default=False)
    in_person_available = models.BooleanField(default=True)
    
    reason = models.CharField(max_length=200, blank=True, help_text="Reason for special availability/unavailability")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['healthcare_professional', 'date', 'start_time']
        ordering = ['date', 'start_time']
    
    def __str__(self):
        status = "Available" if self.is_available else "Unavailable"
        return f"{self.healthcare_professional.user.get_display_name()} - {self.date} {status}"

class ServiceType(models.Model):
    """Types of medical services offered"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Base price in KES")
    duration_minutes = models.PositiveIntegerField(default=30)
    
    # Service delivery methods
    virtual_available = models.BooleanField(default=True)
    home_visit_available = models.BooleanField(default=True)
    in_person_available = models.BooleanField(default=True)
    
    # Additional fees
    home_visit_extra_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Additional fee for home visits")
    urgent_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Additional fee for urgent appointments")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Appointment(models.Model):
    """Patient appointments with healthcare professionals"""
    APPOINTMENT_TYPE_CHOICES = [
        ('virtual', 'Virtual Consultation'),
        ('home_visit', 'Home Visit'),
        ('in_person', 'In-Person'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
        ('rescheduled', 'Rescheduled'),
    ]
    
    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'accounts.PatientProfile',
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    healthcare_professional = models.ForeignKey(
        'accounts.HealthcareProfessionalProfile',
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    service_type = models.ForeignKey(ServiceType, on_delete=models.CASCADE)
    
    # Appointment Details
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPE_CHOICES)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Patient Information
    chief_complaint = models.TextField(help_text="Main reason for the appointment")
    symptoms = models.TextField(blank=True, help_text="Current symptoms")
    medical_history_notes = models.TextField(blank=True, help_text="Relevant medical history")
    current_medications = models.TextField(blank=True, help_text="Current medications")
    allergies_notes = models.TextField(blank=True, help_text="Known allergies")
    
    # Location (for home visits)
    visit_address = models.TextField(blank=True, help_text="Address for home visit")
    visit_coordinates = models.CharField(max_length=100, blank=True, help_text="GPS coordinates")
    visit_instructions = models.TextField(blank=True, help_text="Special instructions for finding location")
    
    # Virtual Consultation Details
    google_meet_link = models.URLField(blank=True, help_text="Google Meet link for virtual consultation")
    meeting_room_id = models.CharField(max_length=100, blank=True)
    
    # Pricing
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    additional_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=50, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Communication
    patient_phone = models.CharField(max_length=15, help_text="Patient contact for this appointment")
    patient_email = models.EmailField(blank=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    
    # Doctor's Notes (filled after consultation)
    diagnosis = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)
    prescription = models.TextField(blank=True)
    doctor_notes = models.TextField(blank=True)
    
    # Ratings and Reviews
    patient_rating = models.PositiveIntegerField(null=True, blank=True, help_text="Rating from 1-5")
    patient_review = models.TextField(blank=True)
    doctor_rating = models.PositiveIntegerField(null=True, blank=True, help_text="Doctor's rating of patient")
    doctor_notes_about_patient = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-appointment_date', '-appointment_time']
        indexes = [
            models.Index(fields=['appointment_date', 'appointment_time']),
            models.Index(fields=['healthcare_professional', 'status']),
            models.Index(fields=['patient', 'status']),
        ]
    
    def __str__(self):
        return f"{self.patient.user.get_display_name()} -> {self.healthcare_professional.user.get_display_name()} on {self.appointment_date}"
    
    def save(self, *args, **kwargs):
        # Calculate total amount
        self.total_amount = self.consultation_fee + self.additional_fees
        
        # Set confirmation timestamp
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        
        # Set payment timestamp
        if self.is_paid and not self.paid_at:
            self.paid_at = timezone.now()
            if self.status == 'pending':
                self.status = 'paid'
        
        # Set completion timestamp
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def appointment_datetime(self):
        """Get full datetime of appointment"""
        return datetime.combine(self.appointment_date, self.appointment_time)
    
    @property
    def is_past_due(self):
        """Check if appointment is past due"""
        return self.appointment_datetime < timezone.now()
    
    @property
    def can_be_cancelled(self):
        """Check if appointment can be cancelled"""
        return self.status in ['pending', 'confirmed', 'paid'] and not self.is_past_due
    
    @property
    def time_until_appointment(self):
        """Get time remaining until appointment"""
        return self.appointment_datetime - timezone.now()
    
    def generate_google_meet_link(self):
        """Generate Google Meet link for virtual consultations"""
        if self.appointment_type == 'virtual' and not self.google_meet_link:
            # In a real implementation, you'd integrate with Google Meet API
            # For now, we'll create a placeholder
            meeting_id = f"havenmed-{self.id.hex[:8]}"
            self.meeting_room_id = meeting_id
            self.google_meet_link = f"https://meet.google.com/{meeting_id}"
            self.save()
    
    def send_confirmation_email(self):
        """Send appointment confirmation email"""
        # Implementation for sending confirmation email
        pass
    
    def send_reminder_sms(self):
        """Send appointment reminder SMS"""
        # Implementation for sending reminder SMS
        pass

class Payment(models.Model):
    """Payment records for appointments"""
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='payment')
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # External Payment References
    external_reference = models.CharField(max_length=100, blank=True, help_text="Payment gateway reference")
    mpesa_receipt_number = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    
    # Payment Details
    phone_number = models.CharField(max_length=15, blank=True, help_text="Phone number for M-Pesa")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Payment {self.id} - {self.amount} KES ({self.status})"

class AppointmentReschedule(models.Model):
    """Track appointment reschedule history"""
    original_appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='reschedule_history'
    )
    old_date = models.DateField()
    old_time = models.TimeField()
    new_date = models.DateField()
    new_time = models.TimeField()
    reason = models.TextField()
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Reschedule: {self.old_date} -> {self.new_date}"

class ConsultationNotes(models.Model):
    """Detailed consultation notes and medical records"""
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='consultation_notes'
    )
    
    # Vital Signs
    blood_pressure_systolic = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.PositiveIntegerField(null=True, blank=True)
    heart_rate = models.PositiveIntegerField(null=True, blank=True, help_text="BPM")
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, help_text="Celsius")
    weight = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="KG")
    height = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="CM")
    
    # Clinical Assessment
    chief_complaint_details = models.TextField(blank=True)
    history_of_present_illness = models.TextField(blank=True)
    physical_examination = models.TextField(blank=True)
    assessment_and_plan = models.TextField(blank=True)
    
    # Prescriptions and Recommendations
    medications_prescribed = models.TextField(blank=True)
    lab_tests_ordered = models.TextField(blank=True)
    follow_up_instructions = models.TextField(blank=True)
    lifestyle_recommendations = models.TextField(blank=True)
    
    # Additional Notes
    differential_diagnosis = models.TextField(blank=True)
    clinical_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notes for {self.appointment}"

class AppointmentAttachment(models.Model):
    """File attachments for appointments (medical reports, images, etc.)"""
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='appointment_attachments/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    description = models.CharField(max_length=200, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.filename} - {self.appointment}"

# Signal handlers
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

@receiver(post_save, sender=Appointment)
def handle_appointment_creation(sender, instance, created, **kwargs):
    """Handle appointment creation tasks"""
    if created:
        # Generate Google Meet link for virtual consultations
        if instance.appointment_type == 'virtual':
            instance.generate_google_meet_link()
        
        # Send confirmation notifications
        instance.send_confirmation_email()

@receiver(pre_save, sender=Appointment)
def handle_appointment_status_change(sender, instance, **kwargs):
    """Handle appointment status changes"""
    if instance.pk:  # Only for existing appointments
        try:
            old_instance = Appointment.objects.get(pk=instance.pk)
            
            # If status changed to confirmed, send confirmation
            if old_instance.status != 'confirmed' and instance.status == 'confirmed':
                # Send confirmation notification
                pass
            
            # If payment completed, update appointment status
            if not old_instance.is_paid and instance.is_paid:
                if instance.status == 'pending':
                    instance.status = 'paid'
                    
        except Appointment.DoesNotExist:
            pass