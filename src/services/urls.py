from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    # Appointment booking
    path('book/<int:provider_id>/', views.book_appointment, name='book_appointment'),
    path('payment/<uuid:appointment_id>/', views.payment_page, name='payment_page'),
    path('payment/status/<uuid:payment_id>/', views.payment_status, name='payment_status'),
    
    # Appointment management
    path('appointment/<uuid:appointment_id>/', views.appointment_detail, name='appointment_detail'),
    path('appointment/<uuid:appointment_id>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointment/<uuid:appointment_id>/join/', views.join_virtual_consultation, name='join_virtual_consultation'),
    
    # AJAX endpoints
    path('api/provider/<int:provider_id>/availability/', views.get_provider_availability, name='get_provider_availability'),
    path('api/service/<int:service_id>/pricing/<int:provider_id>/', views.get_service_pricing, name='get_service_pricing'),
]