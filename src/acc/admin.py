from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, PatientProfile, HealthcareProfessionalProfile, InstitutionProfile

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_approved', 'is_active', 'date_joined')
    list_filter = ('user_type', 'is_approved', 'is_active', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('user_type', 'phone_number', 'is_approved')}),
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
    list_display = ('user', 'date_of_birth', 'gender', 'emergency_contact_name')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')

@admin.register(HealthcareProfessionalProfile)
class HealthcareProfessionalProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'years_of_experience', 'kmpdu_license_number', 'user__is_approved')
    list_filter = ('specialization', 'available_for_home_visits', 'available_for_virtual_consultations', 'user__is_approved')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'kmpdu_license_number')
    readonly_fields = ('national_id', 'kmpdu_license')

@admin.register(InstitutionProfile)
class InstitutionProfileAdmin(admin.ModelAdmin):
    list_display = ('institution_name', 'institution_type', 'registration_number', 'user__is_approved')
    list_filter = ('institution_type', 'emergency_services', 'user__is_approved')
    search_fields = ('institution_name', 'registration_number', 'user__email')
    readonly_fields = ('medical_license',)

admin.site.register(User, CustomUserAdmin)