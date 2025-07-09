from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Avg
from django.utils import timezone
from .models import (
    AvailabilitySlot,
    SpecialAvailability,
    ServiceType,
    Appointment,
    Payment,
    AppointmentReschedule,
    ConsultationNotes,
    AppointmentAttachment
)

@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = (
        'healthcare_professional',
        'day_of_week',
        'start_time',
        'end_time',
        'slot_duration',
        'service_types_available',
        'is_active'
    )
    list_filter = (
        'day_of_week',
        'is_active',
        'virtual_consultations_available',
        'home_visits_available',
        'in_person_available',
        'healthcare_professional__specialization'
    )
    search_fields = (
        'healthcare_professional__user__first_name',
        'healthcare_professional__user__last_name',
        'healthcare_professional__user__email'
    )
    ordering = ('healthcare_professional', 'day_of_week', 'start_time')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('healthcare_professional', 'day_of_week', 'start_time', 'end_time', 'slot_duration')
        }),
        ('Service Types Available', {
            'fields': ('virtual_consultations_available', 'home_visits_available', 'in_person_available')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def service_types_available(self, obj):
        services = []
        if obj.virtual_consultations_available:
            services.append('<span class="badge badge-success">Virtual</span>')
        if obj.home_visits_available:
            services.append('<span class="badge badge-primary">Home</span>')
        if obj.in_person_available:
            services.append('<span class="badge badge-info">In-Person</span>')
        return format_html(' '.join(services))
    service_types_available.short_description = "Available Services"
    
    actions = ['activate_slots', 'deactivate_slots']
    
    def activate_slots(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} slots activated.')
    activate_slots.short_description = "Activate selected slots"
    
    def deactivate_slots(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} slots deactivated.')
    deactivate_slots.short_description = "Deactivate selected slots"

@admin.register(SpecialAvailability)
class SpecialAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        'healthcare_professional',
        'date',
        'start_time',
        'end_time',
        'availability_status',
        'reason'
    )
    list_filter = (
        'is_available',
        'date',
        'healthcare_professional__specialization'
    )
    search_fields = (
        'healthcare_professional__user__first_name',
        'healthcare_professional__user__last_name',
        'reason'
    )
    ordering = ('date', 'start_time')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('healthcare_professional', 'date', 'start_time', 'end_time', 'slot_duration')
        }),
        ('Availability', {
            'fields': ('is_available', 'reason')
        }),
        ('Service Types', {
            'fields': ('virtual_consultations_available', 'home_visits_available', 'in_person_available')
        }),
    )
    
    def availability_status(self, obj):
        if obj.is_available:
            return format_html('<span style="color: green; font-weight: bold;">Available</span>')
        else:
            return format_html('<span style="color: red; font-weight: bold;">Unavailable</span>')
    availability_status.short_description = "Status"
    
    date_hierarchy = 'date'

@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'base_price',
        'duration_minutes',
        'service_delivery_methods',
        'is_active',
        'appointments_count'
    )
    list_filter = (
        'is_active',
        'virtual_available',
        'home_visit_available',
        'in_person_available'
    )
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'base_price', 'duration_minutes')
        }),
        ('Service Delivery', {
            'fields': ('virtual_available', 'home_visit_available', 'in_person_available')
        }),
        ('Additional Fees', {
            'fields': ('home_visit_extra_fee', 'urgent_fee')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    def service_delivery_methods(self, obj):
        methods = []
        if obj.virtual_available:
            methods.append('<span class="badge badge-success">Virtual</span>')
        if obj.home_visit_available:
            methods.append('<span class="badge badge-primary">Home Visit</span>')
        if obj.in_person_available:
            methods.append('<span class="badge badge-info">In-Person</span>')
        return format_html(' '.join(methods))
    service_delivery_methods.short_description = "Delivery Methods"
    
    def appointments_count(self, obj):
        return obj.appointment_set.count()
    appointments_count.short_description = "Appointments"
    
    actions = ['activate_services', 'deactivate_services']
    
    def activate_services(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f'{queryset.count()} services activated.')
    activate_services.short_description = "Activate selected services"
    
    def deactivate_services(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} services deactivated.')
    deactivate_services.short_description = "Deactivate selected services"

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'appointment_id',
        'patient_name',
        'healthcare_professional',
        'service_type',
        'appointment_date',
        'appointment_time',
        'appointment_type',
        'status_display',
        'priority_display',
        'total_amount',
        'payment_status'
    )
    list_filter = (
        'status',
        'appointment_type',
        'priority',
        'is_paid',
        'appointment_date',
        'healthcare_professional__specialization',
        'service_type'
    )
    search_fields = (
        'patient__user__first_name',
        'patient__user__last_name',
        'patient__user__email',
        'healthcare_professional__user__first_name',
        'healthcare_professional__user__last_name',
        'chief_complaint'
    )
    ordering = ('-appointment_date', '-appointment_time')
    readonly_fields = ('id', 'total_amount', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'patient', 'healthcare_professional', 'service_type')
        }),
        ('Appointment Details', {
            'fields': ('appointment_type', 'appointment_date', 'appointment_time', 'duration_minutes', 'priority', 'status')
        }),
        ('Medical Information', {
            'fields': ('chief_complaint', 'symptoms', 'medical_history_notes', 'current_medications', 'allergies_notes')
        }),
        ('Location & Virtual Details', {
            'fields': ('visit_address', 'visit_coordinates', 'visit_instructions', 'google_meet_link', 'meeting_room_id'),
            'classes': ['collapse']
        }),
        ('Pricing & Payment', {
            'fields': ('consultation_fee', 'additional_fees', 'total_amount', 'is_paid', 'payment_method', 'payment_reference', 'paid_at')
        }),
        ('Communication', {
            'fields': ('patient_phone', 'patient_email'),
            'classes': ['collapse']
        }),
        ('Medical Notes', {
            'fields': ('diagnosis', 'treatment_plan', 'prescription', 'doctor_notes'),
            'classes': ['collapse']
        }),
        ('Follow-up', {
            'fields': ('follow_up_required', 'follow_up_date', 'follow_up_notes'),
            'classes': ['collapse']
        }),
        ('Ratings & Reviews', {
            'fields': ('patient_rating', 'patient_review', 'doctor_rating', 'doctor_notes_about_patient'),
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'started_at', 'completed_at'),
            'classes': ['collapse']
        }),
    )
    
    def appointment_id(self, obj):
        return str(obj.id)[:8]
    appointment_id.short_description = "ID"
    
    def patient_name(self, obj):
        return obj.patient.user.get_display_name()
    patient_name.short_description = "Patient"
    
    def status_display(self, obj):
        status_colors = {
            'pending': 'orange',
            'confirmed': 'blue',
            'paid': 'green',
            'in_progress': 'purple',
            'completed': 'green',
            'cancelled': 'red',
            'no_show': 'gray',
            'rescheduled': 'yellow'
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    
    def priority_display(self, obj):
        colors = {
            'normal': 'green',
            'urgent': 'orange',
            'emergency': 'red'
        }
        color = colors.get(obj.priority, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_display.short_description = "Priority"
    
    def payment_status(self, obj):
        if obj.is_paid:
            return format_html('<span style="color: green;">✓ Paid</span>')
        else:
            return format_html('<span style="color: red;">✗ Unpaid</span>')
    payment_status.short_description = "Payment"
    
    date_hierarchy = 'appointment_date'
    
    actions = ['confirm_appointments', 'cancel_appointments', 'mark_completed']
    
    def confirm_appointments(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, f'{queryset.count()} appointments confirmed.')
    confirm_appointments.short_description = "Confirm selected appointments"
    
    def cancel_appointments(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, f'{queryset.count()} appointments cancelled.')
    cancel_appointments.short_description = "Cancel selected appointments"
    
    def mark_completed(self, request, queryset):
        queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{queryset.count()} appointments marked as completed.')
    mark_completed.short_description = "Mark as completed"

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'payment_id',
        'appointment_patient',
        'amount',
        'payment_method',
        'status_display',
        'created_at',
        'completed_at'
    )
    list_filter = (
        'status',
        'payment_method',
        'created_at',
        'completed_at'
    )
    search_fields = (
        'appointment__patient__user__first_name',
        'appointment__patient__user__last_name',
        'external_reference',
        'mpesa_receipt_number',
        'transaction_id'
    )
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'appointment', 'amount', 'payment_method', 'status')
        }),
        ('Payment References', {
            'fields': ('external_reference', 'mpesa_receipt_number', 'transaction_id', 'phone_number')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )
    
    def payment_id(self, obj):
        return str(obj.id)[:8]
    payment_id.short_description = "ID"
    
    def appointment_patient(self, obj):
        return obj.appointment.patient.user.get_display_name()
    appointment_patient.short_description = "Patient"
    
    def status_display(self, obj):
        status_colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'refunded': 'purple',
            'cancelled': 'gray'
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    
    actions = ['mark_completed', 'mark_failed']
    
    def mark_completed(self, request, queryset):
        queryset.update(status='completed', completed_at=timezone.now())
        self.message_user(request, f'{queryset.count()} payments marked as completed.')
    mark_completed.short_description = "Mark as completed"
    
    def mark_failed(self, request, queryset):
        queryset.update(status='failed')
        self.message_user(request, f'{queryset.count()} payments marked as failed.')
    mark_failed.short_description = "Mark as failed"

@admin.register(AppointmentReschedule)
class AppointmentRescheduleAdmin(admin.ModelAdmin):
    list_display = (
        'original_appointment',
        'old_date',
        'old_time',
        'new_date',
        'new_time',
        'requested_by',
        'created_at'
    )
    list_filter = (
        'old_date',
        'new_date',
        'created_at'
    )
    search_fields = (
        'original_appointment__patient__user__first_name',
        'original_appointment__patient__user__last_name',
        'requested_by__first_name',
        'requested_by__last_name',
        'reason'
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Reschedule Details', {
            'fields': ('original_appointment', 'old_date', 'old_time', 'new_date', 'new_time')
        }),
        ('Request Information', {
            'fields': ('reason', 'requested_by', 'created_at')
        }),
    )

@admin.register(ConsultationNotes)
class ConsultationNotesAdmin(admin.ModelAdmin):
    list_display = (
        'appointment',
        'patient_name',
        'healthcare_professional',
        'has_vital_signs',
        'has_prescription',
        'created_at'
    )
    list_filter = (
        'created_at',
        'appointment__healthcare_professional__specialization'
    )
    search_fields = (
        'appointment__patient__user__first_name',
        'appointment__patient__user__last_name',
        'chief_complaint_details',
        'assessment_and_plan'
    )
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Appointment', {
            'fields': ('appointment',)
        }),
        ('Vital Signs', {
            'fields': ('blood_pressure_systolic', 'blood_pressure_diastolic', 'heart_rate', 'temperature', 'weight', 'height')
        }),
        ('Clinical Assessment', {
            'fields': ('chief_complaint_details', 'history_of_present_illness', 'physical_examination', 'assessment_and_plan')
        }),
        ('Prescriptions & Recommendations', {
            'fields': ('medications_prescribed', 'lab_tests_ordered', 'follow_up_instructions', 'lifestyle_recommendations')
        }),
        ('Additional Notes', {
            'fields': ('differential_diagnosis', 'clinical_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def patient_name(self, obj):
        return obj.appointment.patient.user.get_display_name()
    patient_name.short_description = "Patient"
    
    def healthcare_professional(self, obj):
        return obj.appointment.healthcare_professional.user.get_display_name()
    healthcare_professional.short_description = "Healthcare Professional"
    
    def has_vital_signs(self, obj):
        return bool(obj.blood_pressure_systolic or obj.heart_rate or obj.temperature)
    has_vital_signs.boolean = True
    has_vital_signs.short_description = "Vital Signs"
    
    def has_prescription(self, obj):
        return bool(obj.medications_prescribed)
    has_prescription.boolean = True
    has_prescription.short_description = "Prescription"

@admin.register(AppointmentAttachment)
class AppointmentAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        'filename',
        'appointment',
        'patient_name',
        'file_type',
        'uploaded_by',
        'uploaded_at'
    )
    list_filter = (
        'file_type',
        'uploaded_at'
    )
    search_fields = (
        'filename',
        'description',
        'appointment__patient__user__first_name',
        'appointment__patient__user__last_name'
    )
    ordering = ('-uploaded_at',)
    readonly_fields = ('uploaded_at',)
    
    fieldsets = (
        ('File Information', {
            'fields': ('appointment', 'file', 'filename', 'file_type', 'description')
        }),
        ('Upload Details', {
            'fields': ('uploaded_by', 'uploaded_at')
        }),
    )
    
    def patient_name(self, obj):
        return obj.appointment.patient.user.get_display_name()
    patient_name.short_description = "Patient"

# Custom admin site configuration
admin.site.site_header = "HavenMED Services Administration"
admin.site.site_title = "HavenMED Services Admin"
admin.site.index_title = "Services Management"