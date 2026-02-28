from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Citizen, PoliceOfficer, CrimeReport, Area


class CitizenSignupForm(UserCreationForm):
    """Form for citizen registration"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('This email is already registered.')
        return email

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})


class CitizenProfileForm(forms.ModelForm):
    """Form to complete citizen profile"""
    class Meta:
        model = Citizen
        fields = ('phone', 'address', 'city', 'profile_area')
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91 XXXXX XXXXX',
                'maxlength': '15'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your residential address',
                'rows': 3
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'profile_area': forms.Select(attrs={
                'class': 'form-control'
            })
        }


class CrimeReportForm(forms.ModelForm):
    """Form for citizens to report crimes"""
    latitude = forms.FloatField(
        required=False,
        widget=forms.HiddenInput()
    )
    longitude = forms.FloatField(
        required=False,
        widget=forms.HiddenInput()
    )

    class Meta:
        model = CrimeReport
        fields = ('crime_type', 'description', 'location_name', 'area', 'crime_date', 'evidence_file')
        widgets = {
            'crime_type': forms.Select(attrs={
                'class': 'form-control',
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Describe the crime in detail...',
                'rows': 5,
                'required': 'required'
            }),
            'location_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Area/Location name',
                'required': 'required'
            }),
            'area': forms.Select(attrs={
                'class': 'form-control',
                'required': 'required'
            }),
            'crime_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'required': 'required'
            }),
            'evidence_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,video/*'
            })
        }

    def clean_evidence_file(self):
        file = self.cleaned_data.get('evidence_file')
        if file:
            # Limit file size to 10MB
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('File size must not exceed 10MB.')
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'video/mp4', 'video/quicktime']
            if file.content_type not in allowed_types:
                raise ValidationError('Only image and video files are allowed.')
        return file


class CrimeReportUpdateForm(forms.ModelForm):
    """Form for police officers to update crime reports"""
    class Meta:
        model = CrimeReport
        fields = ('status', 'officer_notes', 'is_priority')
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'officer_notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Add your investigation notes...',
                'rows': 4
            }),
            'is_priority': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class PoliceOfficerLoginForm(forms.Form):
    """Form for police officer login using Officer ID"""
    officer_id = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your Officer ID',
            'autofocus': 'autofocus',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password'
        })
    )
