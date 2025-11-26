"""
Django Management Command: Create Admin User
File Location: accounts/management/commands/create_admin.py

Usage:
    python manage.py create_admin

creates the default admin user with password hashing
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import connection
from datetime import datetime


class Command(BaseCommand):
    help = 'Creates the default admin user for PWD Profiling System'

    def handle(self, *args, **kwargs):
        """
        Create admin user with proper Django password hashing
        """
        
        # Admin credentials
        username = 'admin'
        password = 'admin123' 
        security_question = "What is your mother's maiden name?"
        security_answer = 'AdminAnswer123' 
        
        # Hash passwords using Django's PBKDF2
        hashed_password = make_password(password)
        hashed_security_answer = make_password(security_answer)
        
        # SQL to check if admin already exists
        check_sql = "SELECT COUNT(*) FROM users WHERE username = %s"
        
        with connection.cursor() as cursor:
            # Check if admin exists
            cursor.execute(check_sql, [username])
            count = cursor.fetchone()[0]
            
            if count > 0:
                self.stdout.write(
                    self.style.WARNING('Admin user already exists. Skipping creation.')
                )
                return
            
            insert_sql = """
                INSERT INTO users (
                    username,
                    password,
                    role,
                    is_active,
                    is_verified,
                    security_question,
                    security_answer,
                    first_name,
                    middle_name,
                    last_name,
                    suffix,
                    birthdate,
                    sex,
                    religion,
                    home_address,
                    contact_number,
                    nationality,
                    civil_status,
                    educational_attainment,
                    employment_status,
                    occupation,
                    emergency_contact_name,
                    emergency_contact_number,
                    emergency_contact_address,
                    valid_id_path,
                    verified_at,
                    verified_by,
                    created_at,
                    updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) RETURNING id
            """
            
            cursor.execute(insert_sql, [
                username,
                hashed_password,
                'admin',
                True,  # is_active
                True,  # is_verified
                security_question,
                hashed_security_answer,
                'System',
                None,  # middle_name
                'Administrator',
                None,  # suffix
                '1990-01-01',
                'M',
                'N/A',
                'System Office',
                '09171234567',
                'Filipino',
                'Single',
                'College Graduate',
                'Employed',
                'System Administrator',
                'Emergency Contact',
                '09171234567',
                'Emergency Address',
                'admin_id.jpg',
                datetime.now(),  # verified_at
                None,  # verified_by (self-verified)
                datetime.now(),  # created_at
                datetime.now()   # updated_at
            ])
            
            admin_id = cursor.fetchone()[0]
            
            # Log admin creation in audit_log
            audit_sql = """
                INSERT INTO audit_log (action_type, description, user_id, timestamp)
                VALUES (%s, %s, %s, %s)
            """
            
            cursor.execute(audit_sql, [
                'user_registered',
                'System admin account created via management command',
                admin_id,
                datetime.now()
            ])
        
        self.stdout.write(
            self.style.SUCCESS(
                f'  Admin user created successfully!\n'
                f'  Username: {username}\n'
                f'  Password: {password}\n'
                f'  \n'
                f'  WARNING: Change the default password immediately in production!'
            )
        )
