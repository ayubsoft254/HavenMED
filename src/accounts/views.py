from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import HealthcareProfessionalProfile, InstitutionProfile
from django.utils import timezone
from datetime import timedelta, date

@login_required
def dashboard_view(request):
    """Main dashboard view - redirects to user-specific dashboard"""
    user = request.user
    
    if user.user_type == 'patient':
        return redirect('patient_dashboard')
    elif user.user_type == 'healthcare_professional':
        return redirect('healthcare_dashboard')
    elif user.user_type in ['clinic', 'hospital']:
        return redirect('institution_dashboard')
    else:
        messages.error(request, 'Invalid user type')
        return redirect('landing_page')

@login_required
def patient_dashboard(request):
    """Patient dashboard view"""
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    user = request.user
    profile = user.patient_profile
    
    # Import the Appointment model
    from services.models import Appointment
    
    # Get recent and upcoming appointments
    today = timezone.now().date()
    
    # Get all upcoming appointments first (before slicing)
    upcoming_appointments_queryset = Appointment.objects.filter(
        patient=profile,
        appointment_date__gte=today,
        status__in=['confirmed', 'paid']
    ).select_related(
        'healthcare_professional__user',
        'service_type'
    ).order_by('appointment_date', 'appointment_time')
    
    # Now slice to get the first 5
    upcoming_appointments = upcoming_appointments_queryset[:5]
    
    # Get recent past appointments (before slicing)
    past_appointments_queryset = Appointment.objects.filter(
        patient=profile,
        appointment_date__lt=today,
        status__in=['completed', 'cancelled']
    ).select_related(
        'healthcare_professional__user',
        'service_type'
    ).order_by('-appointment_date', '-appointment_time')
    
    # Now slice to get the first 3
    past_appointments = past_appointments_queryset[:3]
    
    # Get appointment statistics
    total_appointments = Appointment.objects.filter(patient=profile).count()
    completed_appointments = Appointment.objects.filter(
        patient=profile,
        status='completed'
    ).count()
    
    # Get next appointment
    next_appointment = upcoming_appointments_queryset.first()
    
    # Get last checkup from past appointments (filter before slicing)
    last_checkup = Appointment.objects.filter(
        patient=profile,
        appointment_date__lt=today,
        status='completed',
        service_type__name__icontains='checkup'
    ).order_by('-appointment_date', '-appointment_time').first()
    
    # Get recommended doctors based on location and ratings
    recommended_doctors = HealthcareProfessionalProfile.objects.filter(
        user__is_approved=True,
        user__county=user.county,
        is_available=True
    ).select_related('user').order_by('-average_rating', '-total_reviews')[:6]
    
    # Get nearby institutions
    nearby_institutions = InstitutionProfile.objects.filter(
        user__is_approved=True,
        user__county=user.county
    ).select_related('user').order_by('-average_rating', '-total_reviews')[:5]
    
    # Health metrics
    health_metrics = {
        'last_checkup': last_checkup,
        'total_appointments': total_appointments,
        'completed_appointments': completed_appointments,
        'upcoming_appointments': upcoming_appointments_queryset.count(),
    }
    
    context = {
        'user': user,
        'profile': profile,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'next_appointment': next_appointment,
        'recommended_doctors': recommended_doctors,
        'nearby_institutions': nearby_institutions,
        'health_metrics': health_metrics,
    }
    
    return render(request, 'accounts/dashboard/patient_dashboard.html', context)

@login_required
def healthcare_dashboard(request):
    """Healthcare professional dashboard view"""
    if request.user.user_type != 'healthcare_professional':
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    user = request.user
    profile = user.healthcare_profile
    
    # Dashboard statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # TODO: Implement appointments, consultations models
    stats = {
        'total_patients': 0,  # profile.consultations.values('patient').distinct().count()
        'appointments_today': 0,  # profile.appointments.filter(date=today).count()
        'appointments_this_week': 0,  # profile.appointments.filter(date__gte=week_ago).count()
        'total_consultations': 0,  # profile.consultations.count()
        'revenue_this_month': 0,  # Calculate from consultations
    }
    
    # Recent activities
    recent_appointments = []  # TODO: Get from appointments model
    pending_requests = []  # TODO: Get pending appointment requests
    
    context = {
        'user': user,
        'profile': profile,
        'stats': stats,
        'recent_appointments': recent_appointments,
        'pending_requests': pending_requests,
    }
    
    return render(request, 'accounts/dashboard/healthcare_dashboard.html', context)

@login_required
def institution_dashboard(request):
    """Institution dashboard view"""
    if request.user.user_type not in ['clinic', 'hospital']:
        messages.error(request, 'Access denied')
        return redirect('dashboard')
    
    user = request.user
    profile = user.institution_profile
    
    # Dashboard statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # TODO: Implement appointments, staff models
    stats = {
        'total_patients': 0,  # appointments.values('patient').distinct().count()
        'appointments_today': 0,
        'staff_count': profile.staff_count or 0,
        'bed_capacity': profile.bed_capacity or 0,
        'occupancy_rate': 0,  # Calculate from current admissions
    }
    
    # Recent activities
    recent_appointments = []
    staff_members = []  # TODO: Get staff associated with institution
    
    context = {
        'user': user,
        'profile': profile,
        'stats': stats,
        'recent_appointments': recent_appointments,
        'staff_members': staff_members,
    }
    
    return render(request, 'accounts/dashboard/institution_dashboard.html', context)

@login_required
def profile_edit(request):
    """Edit user profile"""
    user = request.user
    
    if request.method == 'POST':
        # Handle profile updates
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        
        # Handle profile photo upload
        if 'profile_photo' in request.FILES:
            user.profile_photo = request.FILES['profile_photo']
        
        user.save()
        
        # Update specific profile fields based on user type
        if user.user_type == 'patient':
            profile = user.patient_profile
            profile.date_of_birth = request.POST.get('date_of_birth') or profile.date_of_birth
            profile.gender = request.POST.get('gender', profile.gender)
            profile.emergency_contact_name = request.POST.get('emergency_contact_name', profile.emergency_contact_name)
            profile.emergency_contact_phone = request.POST.get('emergency_contact_phone', profile.emergency_contact_phone)
            profile.address = request.POST.get('address', profile.address)
            profile.medical_history = request.POST.get('medical_history', profile.medical_history)
            profile.allergies = request.POST.get('allergies', profile.allergies)
            profile.save()
            
        elif user.user_type == 'healthcare_professional':
            profile = user.healthcare_profile
            profile.bio = request.POST.get('bio', profile.bio)
            profile.consultation_fee = request.POST.get('consultation_fee') or profile.consultation_fee
            profile.available_for_home_visits = 'available_for_home_visits' in request.POST
            profile.available_for_virtual_consultations = 'available_for_virtual_consultations' in request.POST
            profile.is_available = 'is_available' in request.POST
            profile.save()
            
        elif user.user_type in ['clinic', 'hospital']:
            profile = user.institution_profile
            profile.description = request.POST.get('description', profile.description)
            profile.services_offered = request.POST.get('services_offered', profile.services_offered)
            profile.operating_hours = request.POST.get('operating_hours', profile.operating_hours)
            profile.emergency_services = 'emergency_services' in request.POST
            profile.website = request.POST.get('website', profile.website)
            profile.bed_capacity = request.POST.get('bed_capacity') or profile.bed_capacity
            profile.staff_count = request.POST.get('staff_count') or profile.staff_count
            profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('dashboard')
    
    context = {
        'user': user,
    }
    
    return render(request, 'accounts/dashboard/profile_edit.html', context)

@login_required
def dashboard_search(request):
    """Search functionality within dashboard"""
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'all')
    user = request.user
    
    results = {
        'doctors': [],
        'institutions': [],
        'patients': [],
    }
    
    if query and len(query) >= 2:
        if search_type in ['all', 'doctors']:
            doctors = HealthcareProfessionalProfile.objects.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(specialization__icontains=query) |
                Q(bio__icontains=query),
                user__is_approved=True
            ).select_related('user')[:10]
            results['doctors'] = doctors
        
        if search_type in ['all', 'institutions']:
            institutions = InstitutionProfile.objects.filter(
                Q(institution_name__icontains=query) |
                Q(services_offered__icontains=query) |
                Q(description__icontains=query),
                user__is_approved=True
            ).select_related('user')[:10]
            results['institutions'] = institutions
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return JSON response for AJAX requests
        data = {
            'doctors': [
                {
                    'id': doctor.id,
                    'name': doctor.user.get_display_name(),
                    'specialization': doctor.get_specialization_display(),
                    'rating': float(doctor.average_rating),
                    'photo_url': doctor.user.get_profile_photo_url(),
                    'location': f"{doctor.user.subcounty}, {dict(doctor.user._meta.get_field('county').choices).get(doctor.user.county, doctor.user.county)}"
                } for doctor in results['doctors']
            ],
            'institutions': [
                {
                    'id': inst.id,
                    'name': inst.institution_name,
                    'type': inst.get_institution_type_display(),
                    'rating': float(inst.average_rating),
                    'photo_url': inst.user.get_profile_photo_url(),
                    'location': inst.get_location_display()
                } for inst in results['institutions']
            ]
        }
        return JsonResponse(data)
    
    context = {
        'query': query,
        'search_type': search_type,
        'results': results,
    }
    
    return render(request, 'accounts/dashboard/search_results.html', context)

def provider_directory(request):
    """Public directory of healthcare providers"""
    # Filters
    county = request.GET.get('county', '')
    specialization = request.GET.get('specialization', '')
    institution_type = request.GET.get('institution_type', '')
    search_query = request.GET.get('q', '')
    
    # Healthcare professionals
    doctors = HealthcareProfessionalProfile.objects.filter(
        user__is_approved=True,
        is_available=True
    ).select_related('user')
    
    if county:
        doctors = doctors.filter(user__county=county)
    if specialization:
        doctors = doctors.filter(specialization=specialization)
    if search_query:
        doctors = doctors.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(bio__icontains=search_query)
        )
    
    # Institutions
    institutions = InstitutionProfile.objects.filter(
        user__is_approved=True
    ).select_related('user')
    
    if county:
        institutions = institutions.filter(user__county=county)
    if institution_type:
        institutions = institutions.filter(institution_type=institution_type)
    if search_query:
        institutions = institutions.filter(
            Q(institution_name__icontains=search_query) |
            Q(services_offered__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    doctors_paginator = Paginator(doctors.order_by('-average_rating'), 12)
    institutions_paginator = Paginator(institutions.order_by('-average_rating'), 12)
    
    doctors_page = request.GET.get('doctors_page', 1)
    institutions_page = request.GET.get('institutions_page', 1)
    
    doctors = doctors_paginator.get_page(doctors_page)
    institutions = institutions_paginator.get_page(institutions_page)
    
    # Get filter choices
    from .models import KENYA_COUNTIES
    counties = KENYA_COUNTIES
    specializations = HealthcareProfessionalProfile.SPECIALIZATION_CHOICES
    institution_types = InstitutionProfile.INSTITUTION_TYPE_CHOICES
    
    context = {
        'doctors': doctors,
        'institutions': institutions,
        'counties': counties,
        'specializations': specializations,
        'institution_types': institution_types,
        'filters': {
            'county': county,
            'specialization': specialization,
            'institution_type': institution_type,
            'search_query': search_query,
        }
    }
    
    return render(request, 'accounts/provider_directory.html', context)
