from django import forms
from allauth.account.forms import SignupForm
from ..landing.models import User, PatientProfile, HealthcareProfessionalProfile, InstitutionProfile

class CustomSignupForm(SignupForm):
    USER_TYPE_CHOICES = [
        ('', 'Select Account Type'),
        ('patient', 'Patient'),
        ('healthcare_professional', 'Healthcare Professional'),
        ('clinic', 'Clinic'),
        ('hospital', 'Hospital'),
    ]
    
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone_number = forms.CharField(max_length=15, required=True)
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, required=True)
    
    # Healthcare Professional fields
    specialization = forms.ChoiceField(
        choices=HealthcareProfessionalProfile.SPECIALIZATION_CHOICES,
        required=False
    )
    years_of_experience = forms.IntegerField(required=False, min_value=0)
    kmpdu_license_number = forms.CharField(max_length=50, required=False)
    national_id = forms.ImageField(required=False)
    kmpdu_license = forms.ImageField(required=False)
    bio = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)
    
    # Institution fields
    institution_name = forms.CharField(max_length=200, required=False)
    registration_number = forms.CharField(max_length=100, required=False)
    medical_license = forms.ImageField(required=False)
    physical_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    services_offered = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=False)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition duration-200'
            })
        
        # Special styling for select fields
        self.fields['user_type'].widget.attrs.update({
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition duration-200 bg-white'
        })
        
        # File input styling
        for field_name in ['national_id', 'kmpdu_license', 'medical_license']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition duration-200 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'
                })

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        
        if user_type == 'healthcare_professional':
            required_fields = ['specialization', 'years_of_experience', 'kmpdu_license_number', 'national_id', 'kmpdu_license']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'This field is required for healthcare professionals.')
        
        elif user_type in ['clinic', 'hospital']:
            required_fields = ['institution_name', 'registration_number', 'medical_license', 'physical_address']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f'This field is required for {user_type}s.')
        
        return cleaned_data

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.phone_number = self.cleaned_data['phone_number']
        user.user_type = self.cleaned_data['user_type']
        user.save()
        
        # Save additional profile data
        if user.user_type == 'healthcare_professional':
            profile = user.healthcare_profile
            profile.specialization = self.cleaned_data['specialization']
            profile.years_of_experience = self.cleaned_data['years_of_experience']
            profile.kmpdu_license_number = self.cleaned_data['kmpdu_license_number']
            profile.national_id = self.cleaned_data['national_id']
            profile.kmpdu_license = self.cleaned_data['kmpdu_license']
            profile.bio = self.cleaned_data['bio']
            profile.save()
            
        elif user.user_type in ['clinic', 'hospital']:
            profile = user.institution_profile
            profile.institution_name = self.cleaned_data['institution_name']
            profile.registration_number = self.cleaned_data['registration_number']
            profile.medical_license = self.cleaned_data['medical_license']
            profile.physical_address = self.cleaned_data['physical_address']
            profile.services_offered = self.cleaned_data['services_offered']
            profile.save()
        
        return user