# [BACKEND] Business logic (OOP classes)
# Classes: AuthenticationService, RegistrationService, UserService, PasswordManager, AuditLogService


#simple registration service

from .models import User, AuditLog
from django.contrib.auth.hashers import make_password
import os
from django.conf import settings

class RegistrationService:
    #handle user registration
    
    @staticmethod
    def create_user(registration_data, valid_id_file, ip_address=None):
        
        try:
            #save valid ID file
            valid_id_path = RegistrationService._save_valid_id(valid_id_file, registration_data['username'])
            
            #create user
            user = User.objects.create(
                #step 1 account credentials
                username=registration_data['username'],
                password=make_password(registration_data['password']),
                security_question=registration_data['security_question'],
                security_answer=make_password(registration_data['security_answer']),
                
                #step 2 personal info
                first_name=registration_data['first_name'],
                middle_name=registration_data.get('middle_name', ''),
                last_name=registration_data['last_name'],
                suffix=registration_data.get('suffix', ''),
                birthdate=registration_data['birthdate'],
                sex=registration_data['sex'],
                religion=registration_data['religion'],
                nationality=registration_data['nationality'],
                civil_status=registration_data['civil_status'],
                home_address=registration_data['home_address'],
                contact_number=registration_data['contact_number'],
                
                #step 3 household info
                educational_attainment=registration_data['educational_attainment'],
                employment_status=registration_data['employment_status'],
                occupation=registration_data['occupation'],
                
                #step 4 emergency cont
                emergency_contact_name=registration_data['emergency_contact_name'],
                emergency_contact_number=registration_data['emergency_contact_number'],
                emergency_contact_address=registration_data['emergency_contact_address'],
                
                #step 5 valid ID
                valid_id_path=valid_id_path,
                
                #default values
                role='basic_user',
                is_active=True,
                is_verified=False,  # Admin must verify
            )
            
            #log registration
            AuditLog.log(
                action_type='user_registered',
                description=f'New user registered: {user.username}',
                user=user,
                ip_address=ip_address
            )
            
            return user
            
        except Exception as e:
            print(f"Error creating user: {e}")
            return None
    
    @staticmethod
    def _save_valid_id(file, username):
        
        #create directory if notexists
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'user_ids')
        os.makedirs(upload_dir, exist_ok=True)
        
        #generate filename username_validid.ext
        ext = os.path.splitext(file.name)[1]
        filename = f"{username}_validid{ext}"
        filepath = os.path.join(upload_dir, filename)
        
        #save file
        with open(filepath, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        #return relative path
        return f'user_ids/{filename}'
    
    # setup_admin.py
from accounts.models import User
from django.contrib.auth.hashers import make_password
from datetime import date

def create_default_admin():
    # Check if admin already exists
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create(
            username='admin',
            password=make_password('admin123'),  # default password
            role='admin',
            is_active=True,
            is_verified=True,
            first_name='Admin',
            last_name='User',
            birthdate=date(2000, 1, 1),
            sex='M',
            religion='N/A',
            nationality='Filipino',
            civil_status='Single',
            home_address='N/A',
            contact_number='0000',
            educational_attainment='N/A',
            employment_status='N/A',
            occupation='N/A',
            security_question='N/A',
            security_answer=make_password('admin_answer'),
            emergency_contact_name='N/A',
            emergency_contact_number='0000',
            emergency_contact_address='N/A',
            valid_id_path='N/A'
        )
        print("Admin user created successfully!")
    else:
        print("Admin user already exists.")

# Call the function if you want it to run automatically
create_default_admin()
