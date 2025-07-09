from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q, Avg, Count
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.paginator import Paginator
from .models import (
    Appointment, AvailabilitySlot, SpecialAvailability, 
    ServiceType, Payment
)
from accounts.models import HealthcareProfessionalProfile, KENYA_COUNTIES

@login_required
def book_appointment(request, provider_id):
    """Book an appointment with a healthcare provider"""
    provider = get_object_or_404(HealthcareProfessionalProfile, id=provider_id)
    
    if request.user.user_type != 'patient':
        messages.error(request, 'Only patients can book appointments.')
        return redirect('services:provider_directory')
    
    patient_profile = request.user.patient_profile
    service_types = ServiceType.objects.filter(is_active=True)
    
    # Get available slots for the next 30 days
    today = timezone.now().date()
    end_date = today + timedelta(days=30)
    available_slots = get_available_slots(provider, today, end_date)
    
    if request.method == 'POST':
        # Process booking form
        service_type_id = request.POST.get('service_type')
        appointment_type = request.POST.get('appointment_type')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')
        priority = request.POST.get('priority', 'normal')
        
        # Patient information
        chief_complaint = request.POST.get('chief_complaint')
        symptoms = request.POST.get('symptoms', '')
        medical_history_notes = request.POST.get('medical_history_notes', '')
        current_medications = request.POST.get('current_medications', '')
        allergies_notes = request.POST.get('allergies_notes', '')
        
        # Contact information
        patient_phone = request.POST.get('patient_phone')
        patient_email = request.POST.get('patient_email', '')
        
        # Location for home visits
        visit_address = request.POST.get('visit_address', '')
        visit_instructions = request.POST.get('visit_instructions', '')
        
        # Validate required fields
        if not all([service_type_id, appointment_type, appointment_date, appointment_time, chief_complaint, patient_phone]):
            messages.error(request, 'Please fill in all required fields.')
            context = {
                'provider': provider,
                'service_types': service_types,
                'available_slots': available_slots,
                'patient_profile': patient_profile,
                'today': today,
                'max_date': end_date,
            }
            return render(request, 'services/book_appointment.html', context)
        
        try:
            service_type = ServiceType.objects.get(id=service_type_id)
            appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(appointment_time, '%H:%M').time()
            
            # Validate slot availability
            if not is_slot_available(provider, appointment_date, appointment_time, service_type.duration_minutes):
                messages.error(request, 'Selected time slot is not available.')
                context = {
                    'provider': provider,
                    'service_types': service_types,
                    'available_slots': available_slots,
                    'patient_profile': patient_profile,
                    'today': today,
                    'max_date': end_date,
                }
                return render(request, 'services/book_appointment.html', context)
            
            # Calculate fees
            consultation_fee = provider.consultation_fee or service_type.base_price
            additional_fees = Decimal('0.00')
            
            if appointment_type == 'home_visit':
                additional_fees += service_type.home_visit_extra_fee
            
            if priority == 'urgent':
                additional_fees += service_type.urgent_fee
            
            # Create appointment
            appointment = Appointment.objects.create(
                patient=patient_profile,
                healthcare_professional=provider,
                service_type=service_type,
                appointment_type=appointment_type,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                duration_minutes=service_type.duration_minutes,
                priority=priority,
                chief_complaint=chief_complaint,
                symptoms=symptoms,
                medical_history_notes=medical_history_notes,
                current_medications=current_medications,
                allergies_notes=allergies_notes,
                visit_address=visit_address,
                visit_instructions=visit_instructions,
                consultation_fee=consultation_fee,
                additional_fees=additional_fees,
                patient_phone=patient_phone,
                patient_email=patient_email,
                status='pending'  # Set initial status
            )
            
            messages.success(request, 'Appointment created successfully! Please proceed with payment.')
            
            # Redirect to payment with correct URL namespace
            return redirect('services:payment_page', appointment_id=appointment.id)
            
        except ServiceType.DoesNotExist:
            messages.error(request, 'Invalid service type selected.')
        except ValueError as e:
            messages.error(request, f'Invalid date or time format: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error creating appointment: {str(e)}')
    
    context = {
        'provider': provider,
        'service_types': service_types,
        'available_slots': available_slots,
        'patient_profile': patient_profile,
        'today': today,
        'max_date': end_date,
    }
    
    return render(request, 'services/book_appointment.html', context)

@login_required
def payment_page(request, appointment_id):
    """Payment page for appointment booking"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Verify user can access this appointment
    if request.user.user_type != 'patient' or appointment.patient.user != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        phone_number = request.POST.get('phone_number', '')
        
        # Create payment record
        payment = Payment.objects.create(
            appointment=appointment,
            amount=appointment.total_amount,
            payment_method=payment_method,
            phone_number=phone_number,
        )
        
        if payment_method == 'mpesa':
            # Initiate M-Pesa payment
            result = initiate_mpesa_payment(payment)
            if result['success']:
                payment.external_reference = result['checkout_request_id']
                payment.status = 'processing'
                payment.save()
                
                messages.success(request, 'M-Pesa payment initiated. Please check your phone to complete payment.')
                return redirect('payment_status', payment_id=payment.id)
            else:
                messages.error(request, f'Payment failed: {result["message"]}')
        
        elif payment_method == 'card':
            # Redirect to card payment gateway
            return redirect('card_payment', payment_id=payment.id)
    
    context = {
        'appointment': appointment,
    }
    
    return render(request, 'services/payment_page.html', context)

def get_available_slots(provider, start_date, end_date):
    """Get available time slots for a provider within date range"""
    available_slots = {}
    current_date = start_date
    
    while current_date <= end_date:
        day_name = current_date.strftime('%A').lower()
        
        # Check for special availability first
        special_availability = SpecialAvailability.objects.filter(
            healthcare_professional=provider,
            date=current_date
        ).first()
        
        if special_availability:
            if special_availability.is_available:
                slots = generate_time_slots(
                    special_availability.start_time,
                    special_availability.end_time,
                    special_availability.slot_duration
                )
                available_slots[current_date.isoformat()] = {
                    'date': current_date,
                    'slots': filter_available_slots(provider, current_date, slots)
                }
        else:
            # Check regular availability
            regular_slots = AvailabilitySlot.objects.filter(
                healthcare_professional=provider,
                day_of_week=day_name,
                is_active=True
            )
            
            if regular_slots.exists():
                all_slots = []
                for slot in regular_slots:
                    slots = generate_time_slots(
                        slot.start_time,
                        slot.end_time,
                        slot.slot_duration
                    )
                    all_slots.extend(slots)
                
                if all_slots:
                    available_slots[current_date.isoformat()] = {
                        'date': current_date,
                        'slots': filter_available_slots(provider, current_date, all_slots)
                    }
        
        current_date += timedelta(days=1)
    
    return available_slots

def generate_time_slots(start_time, end_time, duration_minutes):
    """Generate time slots between start and end time"""
    slots = []
    current_time = datetime.combine(datetime.today(), start_time)
    end_datetime = datetime.combine(datetime.today(), end_time)
    
    while current_time < end_datetime:
        slots.append(current_time.time())
        current_time += timedelta(minutes=duration_minutes)
    
    return slots

def filter_available_slots(provider, date, slots):
    """Filter out already booked slots"""
    booked_appointments = Appointment.objects.filter(
        healthcare_professional=provider,
        appointment_date=date,
        status__in=['confirmed', 'paid', 'in_progress']
    ).values_list('appointment_time', flat=True)
    
    available_slots = []
    for slot in slots:
        if slot not in booked_appointments:
            # Also check if slot is not in the past
            slot_datetime = datetime.combine(date, slot)
            # Make slot_datetime timezone-aware
            slot_datetime = timezone.make_aware(slot_datetime)
            if slot_datetime > timezone.now():
                available_slots.append(slot)
    
    return available_slots

def is_slot_available(provider, date, time, duration_minutes):
    """Check if a specific time slot is available"""
    # Check if there's an existing appointment at this time
    existing_appointment = Appointment.objects.filter(
        healthcare_professional=provider,
        appointment_date=date,
        appointment_time=time,
        status__in=['confirmed', 'paid', 'in_progress']
    ).exists()
    
    if existing_appointment:
        return False
    
    # Check if slot is in the past
    slot_datetime = datetime.combine(date, time)
    # Make slot_datetime timezone-aware
    slot_datetime = timezone.make_aware(slot_datetime)
    if slot_datetime <= timezone.now():
        return False
    
    # Check if provider has availability at this time
    day_name = date.strftime('%A').lower()
    
    # Check special availability first
    special_availability = SpecialAvailability.objects.filter(
        healthcare_professional=provider,
        date=date,
        start_time__lte=time,
        end_time__gt=time,
        is_available=True
    ).exists()
    
    if special_availability:
        return True
    
    # Check regular availability
    regular_availability = AvailabilitySlot.objects.filter(
        healthcare_professional=provider,
        day_of_week=day_name,
        start_time__lte=time,
        end_time__gt=time,
        is_active=True
    ).exists()
    
    return regular_availability

def initiate_mpesa_payment(payment):
    """Initiate M-Pesa STK Push payment"""
    # This would integrate with M-Pesa API
    # For now, return a mock response
    return {
        'success': True,
        'checkout_request_id': f'ws_CO_{payment.id}',
        'message': 'Payment initiated successfully'
    }

@login_required
def payment_status(request, payment_id):
    """Check payment status"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Verify user can access this payment
    if payment.appointment.patient.user != request.user:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    context = {
        'payment': payment,
        'appointment': payment.appointment,
    }
    
    return render(request, 'services/payment_status.html', context)

@login_required
@require_POST
def cancel_appointment(request, appointment_id):
    """Cancel an appointment"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check permissions
    if (request.user.user_type == 'patient' and appointment.patient.user != request.user) or \
       (request.user.user_type == 'healthcare_professional' and appointment.healthcare_professional.user != request.user):
        return JsonResponse({'success': False, 'message': 'Access denied'})
    
    if not appointment.can_be_cancelled:
        return JsonResponse({'success': False, 'message': 'Appointment cannot be cancelled'})
    
    reason = request.POST.get('reason', '')
    appointment.status = 'cancelled'
    appointment.doctor_notes = f"Cancelled by {request.user.get_display_name()}. Reason: {reason}"
    appointment.save()
    
    # Handle refund if payment was made
    if appointment.is_paid:
        # Process refund logic here
        pass
    
    return JsonResponse({'success': True, 'message': 'Appointment cancelled successfully'})

@login_required
def appointment_detail(request, appointment_id):
    """View appointment details"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check permissions
    if (request.user.user_type == 'patient' and appointment.patient.user != request.user) and \
       (request.user.user_type == 'healthcare_professional' and appointment.healthcare_professional.user != request.user):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    context = {
        'appointment': appointment,
    }
    
    return render(request, 'services/appointment_detail.html', context)

@login_required
def join_virtual_consultation(request, appointment_id):
    """Join virtual consultation"""
    appointment = get_object_or_404(Appointment, id=appointment_id)
    
    # Check permissions
    if (request.user.user_type == 'patient' and appointment.patient.user != request.user) and \
       (request.user.user_type == 'healthcare_professional' and appointment.healthcare_professional.user != request.user):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    if appointment.appointment_type != 'virtual':
        messages.error(request, 'This is not a virtual consultation.')
        return redirect('appointment_detail', appointment_id=appointment_id)
    
    if not appointment.google_meet_link:
        appointment.generate_google_meet_link()
    
    # Update appointment status
    if appointment.status == 'paid':
        appointment.status = 'in_progress'
        appointment.started_at = timezone.now()
        appointment.save()
    
    context = {
        'appointment': appointment,
        'google_meet_link': appointment.google_meet_link,
    }
    
    return render(request, 'services/virtual_consultation.html', context)

# AJAX views for dynamic updates
@login_required
def get_provider_availability(request, provider_id):
    """Get provider availability for a specific date"""
    provider = get_object_or_404(HealthcareProfessionalProfile, id=provider_id)
    date_str = request.GET.get('date')
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        end_date = date + timedelta(days=1)
        available_slots = get_available_slots(provider, date, end_date)
        
        slots_data = []
        if date_str in available_slots:
            for slot in available_slots[date_str]['slots']:
                slots_data.append({
                    'time': slot.strftime('%H:%M'),
                    'display': slot.strftime('%I:%M %p')
                })
        
        return JsonResponse({
            'success': True,
            'slots': slots_data
        })
        
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid date format'
        })

@login_required
def get_service_pricing(request, service_id, provider_id):
    """Get pricing for a specific service and provider"""
    service = get_object_or_404(ServiceType, id=service_id)
    provider = get_object_or_404(HealthcareProfessionalProfile, id=provider_id)
    
    consultation_fee = provider.consultation_fee or service.base_price
    
    return JsonResponse({
        'consultation_fee': float(consultation_fee),
        'home_visit_extra': float(service.home_visit_extra_fee),
        'urgent_fee': float(service.urgent_fee),
        'virtual_available': service.virtual_available,
        'home_visit_available': service.home_visit_available,
        'in_person_available': service.in_person_available,
    })

def provider_directory(request):
    """Public directory of healthcare providers with filtering and search"""
    
    # Get filter parameters
    county = request.GET.get('county', '')
    specialization = request.GET.get('specialization', '')
    service_type = request.GET.get('service_type', '')
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', 'rating')  # rating, experience, fee_low, fee_high
    min_rating = request.GET.get('min_rating', '')
    max_fee = request.GET.get('max_fee', '')
    availability = request.GET.get('availability', '')  # virtual, home_visits, in_person
    
    # Base queryset - only approved and available providers
    providers = HealthcareProfessionalProfile.objects.filter(
        user__is_approved=True,
        is_available=True
    ).select_related('user').annotate(
        avg_rating=Avg('appointments__patient_rating'),
        total_appointments=Count('appointments'),
        completed_appointments=Count('appointments', filter=Q(appointments__status='completed'))
    )
    
    # Apply filters
    if county:
        providers = providers.filter(user__county=county)
    
    if specialization:
        providers = providers.filter(specialization=specialization)
    
    if search_query:
        providers = providers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(specialization__icontains=search_query) |
            Q(bio__icontains=search_query)
        )
    
    if min_rating:
        try:
            min_rating_value = float(min_rating)
            providers = providers.filter(average_rating__gte=min_rating_value)
        except ValueError:
            pass
    
    if max_fee:
        try:
            max_fee_value = float(max_fee)
            providers = providers.filter(consultation_fee__lte=max_fee_value)
        except ValueError:
            pass
    
    # Availability filters
    if availability == 'virtual':
        providers = providers.filter(available_for_virtual_consultations=True)
    elif availability == 'home_visits':
        providers = providers.filter(available_for_home_visits=True)
    elif availability == 'in_person':
        # Assuming in-person is always available unless specified otherwise
        pass
    
    # Sorting
    if sort_by == 'rating':
        providers = providers.order_by('-average_rating', '-total_reviews')
    elif sort_by == 'experience':
        providers = providers.order_by('-years_of_experience')
    elif sort_by == 'fee_low':
        providers = providers.order_by('consultation_fee')
    elif sort_by == 'fee_high':
        providers = providers.order_by('-consultation_fee')
    elif sort_by == 'name':
        providers = providers.order_by('user__first_name', 'user__last_name')
    else:
        providers = providers.order_by('-average_rating', '-total_reviews')
    
    # Pagination
    paginator = Paginator(providers, 12)  # 12 providers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options for the template
    specializations = HealthcareProfessionalProfile.SPECIALIZATION_CHOICES
    service_types = ServiceType.objects.filter(is_active=True)
    counties = KENYA_COUNTIES
    
    # Statistics for the directory
    stats = {
        'total_providers': providers.count(),
        'avg_rating': providers.aggregate(avg=Avg('average_rating'))['avg'] or 0,
        'specializations_count': providers.values('specialization').distinct().count(),
        'counties_count': providers.values('user__county').distinct().count(),
    }
    
    context = {
        'page_obj': page_obj,
        'providers': page_obj.object_list,
        'specializations': specializations,
        'service_types': service_types,
        'counties': counties,
        'stats': stats,
        'current_filters': {
            'county': county,
            'specialization': specialization,
            'service_type': service_type,
            'search_query': search_query,
            'sort_by': sort_by,
            'min_rating': min_rating,
            'max_fee': max_fee,
            'availability': availability,
        },
        'total_results': paginator.count,
    }
    
    return render(request, 'services/provider_directory.html', context)

def provider_detail(request, provider_id):
    """Detailed view of a healthcare provider"""
    provider = get_object_or_404(HealthcareProfessionalProfile, id=provider_id)
    
    # Get provider's recent reviews
    recent_reviews = provider.appointments.filter(
        patient_rating__isnull=False,
        patient_review__isnull=False
    ).exclude(patient_review='').order_by('-completed_at')[:10]
    
    # Get provider's availability (simplified - you can make this more complex)
    from datetime import date, timedelta
    today = date.today()
    next_week = today + timedelta(days=7)
    
    # Calculate rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        count = provider.appointments.filter(patient_rating=i).count()
        rating_distribution[i] = count
    
    # Get service types
    service_types = ServiceType.objects.filter(is_active=True)
    
    # Calculate response time (mock data - implement based on your needs)
    avg_response_time = "Within 2 hours"  # You can calculate this from actual data
    
    context = {
        'provider': provider,
        'recent_reviews': recent_reviews,
        'rating_distribution': rating_distribution,
        'service_types': service_types,
        'avg_response_time': avg_response_time,
        'can_book': request.user.is_authenticated and request.user.user_type == 'patient',
    }
    
    return render(request, 'services/provider_detail.html', context)

# AJAX view for quick provider info
def provider_quick_info(request, provider_id):
    """AJAX endpoint for quick provider information"""
    provider = get_object_or_404(HealthcareProfessionalProfile, id=provider_id)
    
    data = {
        'name': provider.user.get_display_name(),
        'specialization': provider.get_specialization_display(),
        'experience': provider.years_of_experience,
        'rating': float(provider.average_rating),
        'total_reviews': provider.total_reviews,
        'consultation_fee': float(provider.consultation_fee) if provider.consultation_fee else None,
        'bio': provider.bio,
        'available_virtual': provider.available_for_virtual_consultations,
        'available_home_visits': provider.available_for_home_visits,
        'profile_photo': provider.user.get_profile_photo_url(),
        'location': f"{provider.user.subcounty}, {dict(KENYA_COUNTIES).get(provider.user.county, '')}" if provider.user.county else "Location not specified",
    }
    
    return JsonResponse(data)