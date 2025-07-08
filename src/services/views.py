from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta, time
from decimal import Decimal
import json

from .models import (
    Appointment, AvailabilitySlot, SpecialAvailability, 
    ServiceType, Payment, ConsultationNotes
)
from accounts.models import HealthcareProfessionalProfile, PatientProfile

@login_required
def book_appointment(request, provider_id):
    """Book an appointment with a healthcare provider"""
    provider = get_object_or_404(HealthcareProfessionalProfile, id=provider_id)
    
    if request.user.user_type != 'patient':
        messages.error(request, 'Only patients can book appointments.')
        return redirect('provider_directory')
    
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
        
        try:
            service_type = ServiceType.objects.get(id=service_type_id)
            appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            appointment_time = datetime.strptime(appointment_time, '%H:%M').time()
            
            # Validate slot availability
            if not is_slot_available(provider, appointment_date, appointment_time, service_type.duration_minutes):
                messages.error(request, 'Selected time slot is not available.')
                return render(request, 'services/book_appointment.html', {
                    'provider': provider,
                    'service_types': service_types,
                    'available_slots': available_slots,
                })
            
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
            )
            
            # Redirect to payment
            return redirect('payment_page', appointment_id=appointment.id)
            
        except Exception as e:
            messages.error(request, f'Error creating appointment: {str(e)}')
    
    context = {
        'provider': provider,
        'service_types': service_types,
        'available_slots': available_slots,
        'patient_profile': patient_profile,
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