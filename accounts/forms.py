# [BACKEND] Django forms for validation
# Forms: RegistrationForm, LoginForm, ChangePasswordForm, etc.


from django import forms
from django.core.exceptions import ValidationError
from datetime import datetime

class LoginForm(forms.Form):
    """Simple login form"""
    
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Username'})
    )
    
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )
    
    def clean(self):
        
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if not username:
            raise forms.ValidationError('Username is required')
        
        if not password:
            raise forms.ValidationError('Password is required')
        
        return cleaned_data


class RegistrationStep1Form(forms.Form):
    #step 1 account credentials
    
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput(), required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=True)
    security_question = forms.CharField(max_length=255, required=True)
    security_answer = forms.CharField(max_length=128, required=True)
    
    def clean_username(self):
        #check if username already exists
        from .models import User
        username = self.cleaned_data['username']
        
        if User.objects.filter(username=username).exists():
            raise ValidationError('Username already exists')
        
        return username
    
    def clean(self):
        #check if passwords match
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError('Passwords do not match')
        
        return cleaned_data


class RegistrationStep2Form(forms.Form):
    #step 2 personal info
    
    first_name = forms.CharField(max_length=100, required=True)
    middle_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, required=True)
    suffix = forms.CharField(max_length=10, required=False)
    birthdate = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    sex = forms.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female')],
        required=True
    )
    religion = forms.CharField(max_length=100, required=True)
    nationality = forms.CharField(max_length=50, initial='Filipino', required=True)
    civil_status = forms.ChoiceField(
        choices=[
            ('Single', 'Single'),
            ('Married', 'Married'),
            ('Widowed', 'Widowed'),
            ('Divorced', 'Divorced'),
            ('Separated', 'Separated')
        ],
        required=True
    )
    home_address = forms.CharField(widget=forms.Textarea(), required=True)
    contact_number = forms.CharField(max_length=20, required=True)
    
    def clean_birthdate(self):
        """Check if user is 18+ years old"""
        birthdate = self.cleaned_data['birthdate']
        today = datetime.now().date()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        
        if age < 18:
            raise ValidationError('You must be at least 18 years old to register')
        
        return birthdate


class RegistrationStep3Form(forms.Form):
    #step 3 household info
    
    educational_attainment = forms.ChoiceField(
        choices=[
            ('Elementary', 'Elementary'),
            ('High School', 'High School'),
            ('College', 'College'),
            ('Vocational', 'Vocational'),
            ('College Graduate', 'College Graduate'),
            ('Masters', 'Masters'),
            ('Doctorate', 'Doctorate'),
        ],
        required=True
    )
    employment_status = forms.ChoiceField(
        choices=[
            ('Employed', 'Employed'),
            ('Unemployed', 'Unemployed'),
            ('Self-Employed', 'Self-Employed'),
            ('Student', 'Student'),
            ('Retired', 'Retired'),
        ],
        required=True
    )
    occupation = forms.CharField(max_length=100, required=True)


class RegistrationStep4Form(forms.Form):
    #step 4 emergency contact
    
    emergency_contact_name = forms.CharField(max_length=200, required=True)
    emergency_contact_number = forms.CharField(max_length=20, required=True)
    emergency_contact_address = forms.CharField(widget=forms.Textarea(), required=True)


class RegistrationStep5Form(forms.Form):
    #step 5 valid ID upload
    
    valid_id = forms.ImageField(required=True)
    
    def clean_valid_id(self):
        #validate file size
        valid_id = self.cleaned_data['valid_id']
        
        if valid_id.size > 5 * 1024 * 1024: 
            raise ValidationError('File size must be less than 5MB')
        
        return valid_id



class ChangePasswordForm(forms.Form):
    #user changes own passwor
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True
    )
    security_answer = forms.CharField(
        required=True,
        help_text='Verify your identity'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError('New passwords do not match')
        
        return cleaned_data


class ForgotPasswordStep1Form(forms.Form):
    #step 1 enter username
    
    username = forms.CharField(max_length=150, required=True)


class ForgotPasswordStep2Form(forms.Form):
    #step 2 answer security question
    
    security_answer = forms.CharField(required=True)


class ForgotPasswordStep3Form(forms.Form):
    #step 3 set new password
    
    new_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError('Passwords do not match')
        
        return cleaned_data


class EditProfileForm(forms.Form):
    """User edits own profile (cannot change username or role)"""
    
    #personal info
    first_name = forms.CharField(max_length=100, required=True)
    middle_name = forms.CharField(max_length=100, required=False)
    last_name = forms.CharField(max_length=100, required=True)
    suffix = forms.CharField(max_length=10, required=False)
    birthdate = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    sex = forms.ChoiceField(
        choices=[('M', 'Male'), ('F', 'Female')],
        required=True
    )
    religion = forms.CharField(max_length=100, required=True)
    nationality = forms.CharField(max_length=50, required=True)
    civil_status = forms.ChoiceField(
        choices=[
            ('Single', 'Single'),
            ('Married', 'Married'),
            ('Widowed', 'Widowed'),
            ('Divorced', 'Divorced'),
            ('Separated', 'Separated')
        ],
        required=True
    )
    home_address = forms.CharField(widget=forms.Textarea(), required=True)
    contact_number = forms.CharField(max_length=20, required=True)
    
    #household info
    educational_attainment = forms.ChoiceField(
        choices=[
            ('Elementary', 'Elementary'),
            ('High School', 'High School'),
            ('College', 'College'),
            ('Vocational', 'Vocational'),
            ('College Graduate', 'College Graduate'),
            ('Masters', 'Masters'),
            ('Doctorate', 'Doctorate'),
        ],
        required=True
    )
    employment_status = forms.ChoiceField(
        choices=[
            ('Employed', 'Employed'),
            ('Unemployed', 'Unemployed'),
            ('Self-Employed', 'Self-Employed'),
            ('Student', 'Student'),
            ('Retired', 'Retired'),
        ],
        required=True
    )
    occupation = forms.CharField(max_length=100, required=True)
    
    
    emergency_contact_name = forms.CharField(max_length=200, required=True)
    emergency_contact_number = forms.CharField(max_length=20, required=True)
    emergency_contact_address = forms.CharField(widget=forms.Textarea(), required=True)


class AdminResetPasswordForm(forms.Form):
    #ddmin resets user password
    
    new_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password != confirm_password:
                raise ValidationError('Passwords do not match')
        
        return cleaned_data


class AuditLogFilterForm(forms.Form):
    #Filter audit logs
    
    action_type = forms.ChoiceField(
        choices=[
            ('', 'All Actions'),
            ('login', 'Login'),
            ('logout', 'Logout'),
            ('user_registered', 'User Registered'),
            ('user_verified', 'User Verified'),
            ('user_deactivated', 'User Deactivated'),
            ('user_reactivated', 'User Reactivated'),
            ('password_changed', 'Password Changed'),
            ('password_reset', 'Password Reset'),
            ('profile_updated', 'Profile Updated'),
        ],
        required=False
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    search = forms.CharField(max_length=100, required=False)