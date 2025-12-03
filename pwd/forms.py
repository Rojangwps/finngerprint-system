from django import forms
from django.core.exceptions import ValidationError

# Optional import to validate username uniqueness at form validation time.
# If your accounts app uses a custom user model in a different path, change this import or rely on get_user_model in the view.
try:
    from accounts.models import User as AccountsUser
except Exception:
    AccountsUser = None


class MultiFileInput(forms.ClearableFileInput):
    """
    Allow multiple file selection. Django's FileInput/ ClearableFileInput
    will raise if you set 'multiple' unless the widget sets
    `allow_multiple_selected = True`.
    """
    allow_multiple_selected = True


class PWDRegistrationForm(forms.Form):
    # PWD registration

    # section 1 personal info
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
    civil_status = forms.ChoiceField(
        choices=[
            ('Single', 'Single'),
            ('Married', 'Married'),
            ('Widowed', 'Widowed'),
            ('Divorced', 'Divorced'),
            ('Separated', 'Separated'),
        ],
        required=True
    )
    barangay = forms.CharField(max_length=100, required=True)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)
    contact_number = forms.CharField(max_length=20, required=True)
    religion = forms.CharField(max_length=100, required=True)
    nationality = forms.CharField(max_length=50, initial='Filipino', required=True)
    photo = forms.ImageField(required=False)

    # fingerprint slot (filled by front-end after enrollment)
    fingerprint_slot = forms.CharField(required=False, label="Fingerprint slot", widget=forms.TextInput(attrs={
        "placeholder": "e.g. 10",
        "id": "id_fingerprint_slot"
    }))

    # section 2 household info
    educational_attainment = forms.ChoiceField(
        choices=[
            ('None', 'None'),
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
    occupation = forms.CharField(max_length=100, required=False)
    type_of_employment = forms.ChoiceField(
        choices=[
            ('', '-- Select --'),
            ('Permanent', 'Permanent'),
            ('Contractual', 'Contractual'),
            ('Casual', 'Casual'),
            ('Part-time', 'Part-time'),
            ('Self-employed', 'Self-employed'),
        ],
        required=False
    )

    # section 3 socio economic info
    household_income = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=0
    )
    household_size = forms.IntegerField(required=False, min_value=1)
    living_situation = forms.ChoiceField(
        choices=[
            ('', '-- Select --'),
            ('Living Alone', 'Living Alone'),
            ('Living with Family', 'Living with Family'),
            ('Living with Relatives', 'Living with Relatives'),
            ('Living with Friends', 'Living with Friends'),
            ('Institution', 'Institution'),
        ],
        required=False
    )
    housing_type = forms.ChoiceField(
        choices=[
            ('', '-- Select --'),
            ('Owned', 'Owned'),
            ('Rented', 'Rented'),
            ('Shared', 'Shared'),
            ('Informal Settler', 'Informal Settler'),
        ],
        required=False
    )
    guardian_name = forms.CharField(max_length=200, required=True)
    guardian_contact = forms.CharField(max_length=20, required=True)

    # section 4 medical info
    disability_type = forms.ChoiceField(
        choices=[
            ('Visual', 'Visual Disability'),
            ('Hearing', 'Hearing Disability'),
            ('Speech', 'Speech Disability'),
            ('Physical', 'Physical Disability'),
            ('Mental', 'Mental Disability'),
            ('Intellectual', 'Intellectual Disability'),
            ('Learning', 'Learning Disability'),
            ('Psychosocial', 'Psychosocial Disability'),
            ('Multiple', 'Multiple Disabilities'),
        ],
        required=True
    )
    degree_of_disability = forms.ChoiceField(
        choices=[
            ('Low', 'Low'),
            ('Moderate', 'Moderate'),
            ('High', 'High'),
        ],
        required=True
    )
    cause_of_disability = forms.ChoiceField(
        choices=[
            ('', '-- Select --'),
            ('Congenital', 'Congenital/Birth'),
            ('Illness', 'Illness'),
            ('Accident', 'Accident'),
            ('Age', 'Age-related'),
            ('Other', 'Other'),
        ],
        required=False
    )
    date_diagnosed = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    assistive_devices = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False
    )
    medication = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False
    )

    # section 5 other info
    philhealth_number = forms.CharField(max_length=20, required=False)
    sss_gsis_number = forms.CharField(max_length=20, required=False)
    skills_hobbies = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False
    )
    organization_membership = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}),
        required=False
    )

    # emergency contact info
    emergency_contact_name = forms.CharField(max_length=200, required=True)
    emergency_contact_number = forms.CharField(max_length=20, required=True)
    emergency_contact_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=True)

    # supporting docs
    documents = forms.FileField(
        required=False,
        widget=MultiFileInput(attrs={'accept': '.pdf', 'multiple': True})
    )

    # optional account creation fields (admin can create user during registration)
    create_account = forms.BooleanField(required=False, initial=False, label="Create login account for this PWD")
    account_username = forms.CharField(required=False, max_length=150, label="Account username")
    account_password1 = forms.CharField(required=False, widget=forms.PasswordInput, label="Password")
    account_password2 = forms.CharField(required=False, widget=forms.PasswordInput, label="Confirm password")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('create_account'):
            username = cleaned.get('account_username')
            pw1 = cleaned.get('account_password1')
            pw2 = cleaned.get('account_password2')

            if not username:
                raise ValidationError("Username is required when creating an account for the PWD.")
            if not pw1 or not pw2:
                raise ValidationError("Both password fields are required when creating an account.")
            if pw1 != pw2:
                raise ValidationError("Passwords do not match.")
            if AccountsUser is not None:
                if AccountsUser.objects.filter(username=username).exists():
                    raise ValidationError("Username already exists; choose another username.")
        return cleaned

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            if photo.size > 5 * 1024 * 1024:
                raise ValidationError('Photo must be less than 5MB')
        return photo