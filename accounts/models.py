# [BACKEND + DATABASE] Django ORM models

#basic User and auditLog models

from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class User(models.Model):
    #user model maps to users table in pgsql
    
    #authentication
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)  # Will store hashed password
    role = models.CharField(max_length=20, default='basic_user')
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    fingerprint_id = models.IntegerField(blank=True, null=True, unique=True)
    
    #timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, db_column='verified_by')
    
    #security
    security_question = models.CharField(max_length=255)
    security_answer = models.CharField(max_length=128)  # Will store hashed answer
    
    #personal info
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100)
    suffix = models.CharField(max_length=10, null=True, blank=True)
    birthdate = models.DateField()
    sex = models.CharField(max_length=1)  # 'M' or 'F'
    religion = models.CharField(max_length=100)
    home_address = models.TextField()
    contact_number = models.CharField(max_length=20)
    nationality = models.CharField(max_length=50, default='Filipino')
    civil_status = models.CharField(max_length=20)
    
    #household info
    educational_attainment = models.CharField(max_length=50)
    employment_status = models.CharField(max_length=20)
    occupation = models.CharField(max_length=100)
    
    #emergency contact
    emergency_contact_name = models.CharField(max_length=200, default="N/A")
    emergency_contact_number = models.CharField(max_length=20, default="0000")
    emergency_contact_address = models.TextField(default="N/A")

    
    #documents
    valid_id_path = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'users'
    
    def __str__(self):
        return self.username
    
    def set_password(self, raw_password):
        #set hash password
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        #check if password is correct
        return check_password(raw_password, self.password)
    
    def is_admin(self):
        #if user == admin
        return self.role == 'admin'


class AuditLog(models.Model):
    #audit log tracks all system activities

    ACTION_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('user_registered', 'User Registered'),
        ('user_verified', 'User Verified'),
        ('user_deactivated', 'User Deactivated'),
        ('user_reactivated', 'User Reactivated'),
        ('password_changed', 'Password Changed'),
        ('password_reset', 'Password Reset'),
        ('admin_reset_password', 'Admin Reset Password'),
        ('profile_updated', 'Profile Updated'),
        ('pwd_registered', 'PWD Registered'),
        ('pwd_updated', 'PWD Updated'),
        ('pwd_archived', 'PWD Archived'),
        ('pwd_reactivated', 'PWD Reactivated'),
    ]
    
    action_type = models.CharField(max_length=50)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.CharField(max_length=45, null=True, blank=True)
    
    #fk
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='actions')
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='targeted_actions')
    target_pwd = models.ForeignKey('pwd.PWDProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    
    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.action_type} - {self.timestamp}"
    
    @classmethod
    def log(cls, action_type, description, user=None, target_user=None, target_pwd=None, ip_address=None):
        #create audit log entry
        return cls.objects.create(
            action_type=action_type,
            description=description,
            user=user,
            target_user=target_user,
            target_pwd=target_pwd,
            ip_address=ip_address,
        )   