from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, PatientProfile, HealthcareProfessionalProfile, InstitutionProfile

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'county', 'is_approved', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_approved', 'is_active', 'is_staff', 'county')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('email',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('User Information', {
            'fields': ('user_type', 'phone_number', 'is_approved')
        }),
        ('Location', {
            'fields': ('county', 'subcounty')
        }),
        ('Profile', {
            'fields': ('profile_photo',)
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('User Information', {
            'fields': ('user_type', 'phone_number', 'email', 'first_name', 'last_name')
        }),
        ('Location', {
            'fields': ('county', 'subcounty')
        }),
    )
    
    actions = ['approve_users', 'disapprove_users']
    
    def approve_users(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f'{queryset.count()} users approved successfully.')
    approve_users.short_description = "Approve selected users"
    
    def disapprove_users(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f'{queryset.count()} users disapproved.')
    disapprove_users.short_description = "Disapprove selected users"

@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_of_birth', 'gender', 'age_display', 'emergency_contact_name', 'has_medical_history')
    list_filter = ('gender', 'date_of_birth')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'emergency_contact_name')
    readonly_fields = ('age_display',)
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('user', 'date_of_birth', 'gender', 'age_display')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone')
        }),
        ('Medical Information', {
            'fields': ('medical_history', 'allergies')
        }),
        ('Address', {
            'fields': ('address',)
        }),
    )
    
    def age_display(self, obj):
        age = obj.age
        return f"{age} years" if age else "Not specified"
    age_display.short_description = "Age"
    
    def has_medical_history(self, obj):
        return bool(obj.medical_history)
    has_medical_history.boolean = True
    has_medical_history.short_description = "Has Medical History"

@admin.register(HealthcareProfessionalProfile)
class HealthcareProfessionalProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 
        'specialization', 
        'years_of_experience', 
        'experience_level_display',
        'kmpdu_license_number', 
        'consultation_fee',
        'average_rating',
        'total_reviews',
        'is_available',
        'approval_status'
    )
    list_filter = (
        'specialization', 
        'years_of_experience',
        'available_for_home_visits', 
        'available_for_virtual_consultations',
        'is_available',
        'user__is_approved',
        'user__county'
    )
    search_fields = (
        'user__email', 
        'user__first_name', 
        'user__last_name', 
        'kmpdu_license_number',
        'bio'
    )
    readonly_fields = ('average_rating', 'total_reviews', 'experience_level_display')
    
    fieldsets = (
        ('Professional Information', {
            'fields': ('user', 'specialization', 'years_of_experience', 'experience_level_display', 'kmpdu_license_number')
        }),
        ('Documents', {
            'fields': ('national_id', 'kmpdu_license'),
            'description': 'Upload professional documents for verification'
        }),
        ('Profile Details', {
            'fields': ('bio', 'consultation_fee')
        }),
        ('Service Availability', {
            'fields': ('is_available', 'available_for_home_visits', 'available_for_virtual_consultations')
        }),
        ('Ratings & Reviews', {
            'fields': ('average_rating', 'total_reviews'),
            'description': 'These fields are automatically calculated from patient reviews'
        }),
    )
    
    actions = ['approve_professionals', 'disapprove_professionals', 'mark_available', 'mark_unavailable']
    
    def experience_level_display(self, obj):
        return obj.get_experience_level()
    experience_level_display.short_description = "Experience Level"
    
    def approval_status(self, obj):
        if obj.user.is_approved:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Approved</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Pending</span>'
            )
    approval_status.short_description = "Approval Status"
    
    def approve_professionals(self, request, queryset):
        count = 0
        for profile in queryset:
            profile.user.is_approved = True
            profile.user.save()
            count += 1
        self.message_user(request, f'{count} healthcare professionals approved successfully.')
    approve_professionals.short_description = "Approve selected professionals"
    
    def disapprove_professionals(self, request, queryset):
        count = 0
        for profile in queryset:
            profile.user.is_approved = False
            profile.user.save()
            count += 1
        self.message_user(request, f'{count} healthcare professionals disapproved.')
    disapprove_professionals.short_description = "Disapprove selected professionals"
    
    def mark_available(self, request, queryset):
        queryset.update(is_available=True)
        self.message_user(request, f'{queryset.count()} professionals marked as available.')
    mark_available.short_description = "Mark as available"
    
    def mark_unavailable(self, request, queryset):
        queryset.update(is_available=False)
        self.message_user(request, f'{queryset.count()} professionals marked as unavailable.')
    mark_unavailable.short_description = "Mark as unavailable"

@admin.register(InstitutionProfile)
class InstitutionProfileAdmin(admin.ModelAdmin):
    list_display = (
        'institution_name', 
        'institution_type', 
        'registration_number',
        'location_display',
        'emergency_services',
        'bed_capacity',
        'staff_count',
        'average_rating',
        'total_reviews',
        'approval_status'
    )
    list_filter = (
        'institution_type', 
        'emergency_services', 
        'user__is_approved',
        'user__county'
    )
    search_fields = (
        'institution_name', 
        'registration_number', 
        'user__email',
        'description',
        'services_offered'
    )
    readonly_fields = ('average_rating', 'total_reviews', 'location_display')
    
    fieldsets = (
        ('Institution Information', {
            'fields': ('user', 'institution_name', 'institution_type', 'registration_number')
        }),
        ('Documents', {
            'fields': ('medical_license',),
            'description': 'Upload institution license for verification'
        }),
        ('Contact & Location', {
            'fields': ('physical_address', 'postal_address', 'location_display', 'website')
        }),
        ('Services & Details', {
            'fields': ('description', 'services_offered', 'operating_hours', 'emergency_services')
        }),
        ('Capacity & Staff', {
            'fields': ('bed_capacity', 'staff_count'),
            'description': 'Information about institution capacity and staffing'
        }),
        ('Ratings & Reviews', {
            'fields': ('average_rating', 'total_reviews'),
            'description': 'These fields are automatically calculated from patient reviews'
        }),
    )
    
    actions = ['approve_institutions', 'disapprove_institutions', 'enable_emergency_services', 'disable_emergency_services']
    
    def location_display(self, obj):
        return obj.get_location_display()
    location_display.short_description = "Location"
    
    def approval_status(self, obj):
        if obj.user.is_approved:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Approved</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;">✗ Pending</span>'
            )
    approval_status.short_description = "Approval Status"
    
    def approve_institutions(self, request, queryset):
        count = 0
        for profile in queryset:
            profile.user.is_approved = True
            profile.user.save()
            count += 1
        self.message_user(request, f'{count} institutions approved successfully.')
    approve_institutions.short_description = "Approve selected institutions"
    
    def disapprove_institutions(self, request, queryset):
        count = 0
        for profile in queryset:
            profile.user.is_approved = False
            profile.user.save()
            count += 1
        self.message_user(request, f'{count} institutions disapproved.')
    disapprove_institutions.short_description = "Disapprove selected institutions"
    
    def enable_emergency_services(self, request, queryset):
        queryset.update(emergency_services=True)
        self.message_user(request, f'{queryset.count()} institutions enabled for emergency services.')
    enable_emergency_services.short_description = "Enable emergency services"
    
    def disable_emergency_services(self, request, queryset):
        queryset.update(emergency_services=False)
        self.message_user(request, f'{queryset.count()} institutions disabled for emergency services.')
    disable_emergency_services.short_description = "Disable emergency services"

# Custom admin site configuration
admin.site.register(User, CustomUserAdmin)
admin.site.site_header = "HavenMED Administration"
admin.site.site_title = "HavenMED Admin"
admin.site.index_title = "Welcome to HavenMED Administration"