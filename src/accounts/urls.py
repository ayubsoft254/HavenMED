from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/patient/', views.patient_dashboard, name='patient_dashboard'),
    path('dashboard/healthcare/', views.healthcare_dashboard, name='healthcare_dashboard'),
    path('dashboard/institution/', views.institution_dashboard, name='institution_dashboard'),
    path('dashboard/profile/edit/', views.profile_edit, name='profile_edit'),
    path('dashboard/search/', views.dashboard_search, name='dashboard_search'),
    path('providers/', views.provider_directory, name='provider_directory'),
]