    # [BACKEND + DATABASE] Django ORM models
# Models: PWDProfile, PWDDocument
# Maps to PostgreSQL db: pwd_profiles, pwd_documents



from django.db import models
from django.conf import settings
from datetime import date


class PWDProfile(models.Model):
   #PWD profile main record for PWD
    
    #unique ID YYYY-####
    unique_id = models.CharField(max_length=9, unique=True)
    fingerprint_id = models.IntegerField(blank=True, null=True, unique=True)
    
    #personal info
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=10, blank=True, null=True)
    birthdate = models.DateField()
    sex = models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female')])
    civil_status = models.CharField(max_length=20, choices=[
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Widowed', 'Widowed'),
        ('Divorced', 'Divorced'),
        ('Separated', 'Separated'),
    ])
    barangay = models.CharField(max_length=100)
    address = models.TextField()
    contact_number = models.CharField(max_length=20)
    religion = models.CharField(max_length=100, default="N/A")
    nationality = models.CharField(max_length=50, default='Filipino')
    photo_path = models.CharField(max_length=255, blank=True, null=True)
    
    #household info
    educational_attainment = models.CharField(max_length=50, choices=[
        ('None', 'None'),
        ('Elementary', 'Elementary'),
        ('High School', 'High School'),
        ('College', 'College'),
        ('Vocational', 'Vocational'),
        ('College Graduate', 'College Graduate'),
        ('Masters', 'Masters'),
        ('Doctorate', 'Doctorate'),
    ])
    employment_status = models.CharField(max_length=20, choices=[
        ('Employed', 'Employed'),
        ('Unemployed', 'Unemployed'),
        ('Self-Employed', 'Self-Employed'),
        ('Student', 'Student'),
        ('Retired', 'Retired'),
    ])
    occupation = models.CharField(max_length=100, blank=True, null=True)
    type_of_employment = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('', ''),
        ('Permanent', 'Permanent'),
        ('Contractual', 'Contractual'),
        ('Casual', 'Casual'),
        ('Part-time', 'Part-time'),
        ('Self-employed', 'Self-employed'),
    ])
    
    #socio economic info
    household_income = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    household_size = models.IntegerField(blank=True, null=True)
    living_situation = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('', ''),
        ('Living Alone', 'Living Alone'),
        ('Living with Family', 'Living with Family'),
        ('Living with Relatives', 'Living with Relatives'),
        ('Living with Friends', 'Living with Friends'),
        ('Institution', 'Institution'),
    ])
    housing_type = models.CharField(max_length=50, blank=True, null=True, choices=[
        ('', ''),
        ('Owned', 'Owned'),
        ('Rented', 'Rented'),
        ('Shared', 'Shared'),
        ('Informal Settler', 'Informal Settler'),
    ])
    guardian_name = models.CharField(max_length=200, default="N/A")
    guardian_contact = models.CharField(max_length=20, default="0000")
    
    #medical info
    disability_type = models.CharField(max_length=100, choices=[
        ('Visual', 'Visual Disability'),
        ('Hearing', 'Hearing Disability'),
        ('Speech', 'Speech Disability'),
        ('Physical', 'Physical Disability'),
        ('Mental', 'Mental Disability'),
        ('Intellectual', 'Intellectual Disability'),
        ('Learning', 'Learning Disability'),
        ('Psychosocial', 'Psychosocial Disability'),
        ('Multiple', 'Multiple Disabilities'),
    ])
    degree_of_disability = models.CharField(max_length=20, choices=[
        ('Low', 'Low'),
        ('Moderate', 'Moderate'),
        ('High', 'High'),
    ])
    cause_of_disability = models.CharField(max_length=100, blank=True, null=True, choices=[
        ('', ''),
        ('Congenital', 'Congenital/Birth'),
        ('Illness', 'Illness'),
        ('Accident', 'Accident'),
        ('Age', 'Age-related'),
        ('Other', 'Other'),
    ])
    date_diagnosed = models.DateField(blank=True, null=True)
    assistive_devices = models.TextField(blank=True, null=True)
    medication = models.TextField(blank=True, null=True)
    
    #0ther info
    philhealth_number = models.CharField(max_length=20, blank=True, null=True)
    sss_gsis_number = models.CharField(max_length=20, blank=True, null=True)
    skills_hobbies = models.TextField(blank=True, null=True)
    organization_membership = models.TextField(blank=True, null=True)
    
    #emergency contact info
    emergency_contact_name = models.CharField(max_length=200, default="N/A")
    emergency_contact_number = models.CharField(max_length=20, default="0000")
    emergency_contact_address = models.TextField(default="N/A")

    
    #status
    is_active = models.BooleanField(default=True)
    
    #timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    #audit whom created/updated
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='pwd_created',
        db_column='created_by'
    )
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='pwd_updated',
        db_column='updated_by'
    )
    
    
    #fingerprint_data = models.BinaryField(blank=True, null=True)
    
    class Meta:
        db_table = 'pwd_profile'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.unique_id} - {self.first_name} {self.last_name}"
    
    def get_full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        if self.suffix:
            parts.append(self.suffix)
        return ' '.join(parts)
    
    def get_age(self):
        #calculate age from bday
        today = date.today()
        age = today.year - self.birthdate.year
        if (today.month, today.day) < (self.birthdate.month, self.birthdate.day):
            age -= 1
        return age
    
    @staticmethod
    def generate_unique_id():
        #generate unique ID
        current_year = date.today().year
        
        #find last PWD registered this year
        last_pwd = PWDProfile.objects.filter(
            unique_id__startswith=str(current_year)
        ).order_by('-unique_id').first()
        
        if last_pwd:
            #extract sequence number and increment
            last_seq = int(last_pwd.unique_id.split('-')[1])
            new_seq = last_seq + 1
        else:
            #first PWD of the year
            new_seq = 1
        
        #format YYYY-#### 4 digit sequence
        return f"{current_year}-{new_seq:04d}"


class PWDDocument(models.Model):
    
    pwd_profile = models.ForeignKey(
        PWDProfile,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    file_path = models.CharField(max_length=255)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10, default='pdf')
    file_size = models.IntegerField(default=0)  
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='pwd_documents_uploaded',
        db_column='uploaded_by'
    )
    
    class Meta:
        db_table = 'pwd_documents'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.pwd_profile.unique_id} - {self.file_name}"
    
    def get_file_size_display(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"