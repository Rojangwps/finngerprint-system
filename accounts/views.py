"""
Updated accounts.views — defensive, consistent, and no unexpected DoesNotExist
exceptions on GET requests. This preserves your app's session-based auth model
(uses request.session['user_id']) but adds helpers to safely resolve the current
user and centralizes common checks.

Replace your existing accounts/views.py with this file. After replacing:
 - Restart the dev server
 - Test /accounts/login/, /accounts/profile/, registration steps, fingerprint login, etc.

Notes:
 - This file deliberately avoids raising User.DoesNotExist on GET by using
   safe lookups (filter().first() or try/except around .get()).
 - AuditLog.log calls are wrapped in try/except so failures there won't break UX.
 - Fingerprint serial read is defensive and times out cleanly.
"""

import time as _time
from datetime import datetime, timedelta
from typing import Optional

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.hashers import check_password

# local app imports
from .models import User, AuditLog
from .forms import (
    LoginForm,
    RegistrationStep1Form,
    RegistrationStep2Form,
    RegistrationStep3Form,
    RegistrationStep4Form,
    RegistrationStep5Form,
    ChangePasswordForm,
    ForgotPasswordStep1Form,
    ForgotPasswordStep2Form,
    ForgotPasswordStep3Form,
    EditProfileForm,
    AdminResetPasswordForm,
    AuditLogFilterForm,
)
from .services import RegistrationService

# Serial helper for fingerprint (optional)
try:
    import serial  # pyserial, may not be present in all environments
except Exception:
    serial = None


# -------------------------------
# Utility helpers
# -------------------------------
def get_client_ip(request):
    """Return the client IP (first X-Forwarded-For or REMOTE_ADDR)."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_current_user(request) -> Optional[User]:
    """
    Safe resolver for the logged-in user using your session pattern.
    Returns a User instance or None (never raises).
    """
    uid = request.session.get('user_id')
    if not uid:
        # also accept Django's _auth_user_id if present
        uid = request.session.get('_auth_user_id')
    if not uid:
        return None
    try:
        # numeric string -> int
        if isinstance(uid, str) and uid.isdigit():
            uid = int(uid)
        return User.objects.filter(id=uid).first()
    except Exception:
        return None


def require_login_redirect(request):
    """Helper redirect into login with a message when session missing."""
    messages.error(request, 'Please login first')
    return redirect('accounts:login')


def is_admin_session(request) -> bool:
    role = request.session.get('role') or ''
    return str(role).lower() == 'admin'


# -------------------------------
# Fingerprint helpers / endpoints
# -------------------------------
def get_fingerprint_id(port='COM3', baud=9600, timeout=2):
    """
    Try to read a fingerprint id from a serial device.
    Returns int id or None. Defensive: catches serial errors.
    """
    if serial is None:
        return None

    try:
        ser = serial.Serial(port, baud, timeout=timeout)
    except Exception:
        return None

    # small delay to allow device to become ready
    _time.sleep(0.5)
    try:
        if ser.in_waiting:
            raw = ser.readline().decode(errors='ignore').strip()
            if raw and raw.isdigit():
                try:
                    return int(raw)
                except ValueError:
                    return None
    except Exception:
        return None
    finally:
        try:
            ser.close()
        except Exception:
            pass
    return None


def verify_fingerprint(request):
    """
    Attempt fingerprint login: read from serial and log in matching user.
    - On success, set session keys and redirect to dashboard/profile.
    - On failure show a friendly message.
    """
    fid = get_fingerprint_id()
    if not fid:
        return render(request, 'accounts/login_fail.html', {'error': 'No fingerprint detected.'})

    user = User.objects.filter(fingerprint_id=fid).first()
    if not user:
        return render(request, 'accounts/login_fail.html', {'error': 'Fingerprint not recognized.'})

    # create session keys (same shape your app expects)
    request.session['user_id'] = user.id
    request.session['username'] = user.username
    request.session['role'] = user.role
    request.session['is_verified'] = getattr(user, 'is_verified', False)

    # audit
    try:
        AuditLog.log(
            action_type='fingerprint_login',
            description=f'User {user.username} logged in by fingerprint',
            user=user,
            ip_address=get_client_ip(request)
        )
    except Exception:
        pass

    # redirect
    if getattr(user, 'role', '').lower() == 'admin':
        return redirect('pwd:dashboard')
    return redirect('accounts:profile')


# -------------------------------
# Authentication views
# -------------------------------
def login_view(request):
    """
    Login view that uses your custom session approach.
    GET: render form (safe: no exception when stale session id present)
    POST: validate credentials, set session data, audit, and redirect
    """
    # If already logged in (safe resolve), redirect accordingly
    current = get_current_user(request)
    if current:
        if getattr(current, 'role', '').lower() == 'admin':
            return redirect('pwd:dashboard')
        return redirect('accounts:profile')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = User.objects.filter(username=username).first()
            if not user:
                messages.error(request, 'Invalid username or password')
                return render(request, 'accounts/login.html', {'form': form})

            if not user.is_active:
                messages.error(request, 'Your account is inactive. Contact admin.')
                return render(request, 'accounts/login.html', {'form': form})

            if user.check_password(password):
                # create session
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                request.session['role'] = user.role
                request.session['is_verified'] = getattr(user, 'is_verified', False)

                # audit
                try:
                    AuditLog.log(
                        action_type='login',
                        description=f'User {username} logged in',
                        user=user,
                        ip_address=get_client_ip(request)
                    )
                except Exception:
                    pass

                messages.success(request, f'Welcome, {user.first_name or user.username}!')
                if user.is_admin():
                    return redirect('pwd:dashboard')
                return redirect('accounts:profile')
            else:
                messages.error(request, 'Invalid username or password')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """
    Clear session and log audit if possible.
    """
    user = get_current_user(request)
    username = request.session.get('username')

    if user:
        try:
            AuditLog.log(
                action_type='logout',
                description=f'User {username} logged out',
                user=user,
                ip_address=get_client_ip(request)
            )
        except Exception:
            pass

    request.session.flush()
    messages.success(request, 'You have been logged out successfully')
    return redirect('accounts:login')


# -------------------------------
# Profile and registration steps
# -------------------------------
def profile_view(request):
    """
    Show current user's profile information. Uses safe lookup and avoids raising.
    """
    user = get_current_user(request)
    if not user:
        return require_login_redirect(request)

    return render(request, 'accounts/profile.html', {'user': user})


def register_step1_view(request):
    """
    Registration step 1: account credentials
    """
    if request.method == 'POST':
        form = RegistrationStep1Form(request.POST)
        if form.is_valid():
            request.session['registration_step1'] = {
                'username': form.cleaned_data['username'],
                'password': form.cleaned_data['password'],
                'security_question': form.cleaned_data['security_question'],
                'security_answer': form.cleaned_data['security_answer'],
            }
            messages.success(request, 'Step 1 complete. Enter your personal information.')
            return redirect('accounts:register_step2')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        initial_data = request.session.get('registration_step1', {})
        form = RegistrationStep1Form(initial=initial_data)
    return render(request, 'accounts/register_step1.html', {'form': form, 'step': 1, 'total_steps': 5})


def register_step2_view(request):
    """
    Registration step 2: personal info
    """
    if 'registration_step1' not in request.session:
        messages.error(request, 'Please complete Step 1 first')
        return redirect('accounts:register_step1')

    if request.method == 'POST':
        form = RegistrationStep2Form(request.POST)
        if form.is_valid():
            request.session['registration_step2'] = {
                'first_name': form.cleaned_data['first_name'],
                'middle_name': form.cleaned_data.get('middle_name', ''),
                'last_name': form.cleaned_data['last_name'],
                'suffix': form.cleaned_data.get('suffix', ''),
                'birthdate': form.cleaned_data['birthdate'].strftime('%Y-%m-%d'),
                'sex': form.cleaned_data['sex'],
                'religion': form.cleaned_data['religion'],
                'nationality': form.cleaned_data['nationality'],
                'civil_status': form.cleaned_data['civil_status'],
                'home_address': form.cleaned_data['home_address'],
                'contact_number': form.cleaned_data['contact_number'],
            }
            messages.success(request, 'Step 2 complete. Enter household information.')
            return redirect('accounts:register_step3')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        initial_data = request.session.get('registration_step2', {})
        form = RegistrationStep2Form(initial=initial_data)
    return render(request, 'accounts/register_step2.html', {'form': form, 'step': 2, 'total_steps': 5})


def register_step3_view(request):
    if ('registration_step1' not in request.session or 'registration_step2' not in request.session):
        messages.error(request, 'Please complete previous steps first')
        return redirect('accounts:register_step1')

    if request.method == 'POST':
        form = RegistrationStep3Form(request.POST)
        if form.is_valid():
            request.session['registration_step3'] = {
                'educational_attainment': form.cleaned_data['educational_attainment'],
                'employment_status': form.cleaned_data['employment_status'],
                'occupation': form.cleaned_data['occupation'],
            }
            messages.success(request, 'Step 3 complete. Enter emergency contact.')
            return redirect('accounts:register_step4')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        initial_data = request.session.get('registration_step3', {})
        form = RegistrationStep3Form(initial=initial_data)
    return render(request, 'accounts/register_step3.html', {'form': form, 'step': 3, 'total_steps': 5})


def register_step4_view(request):
    if ('registration_step1' not in request.session or
        'registration_step2' not in request.session or
        'registration_step3' not in request.session):
        messages.error(request, 'Please complete previous steps first')
        return redirect('accounts:register_step1')

    if request.method == 'POST':
        form = RegistrationStep4Form(request.POST)
        if form.is_valid():
            request.session['registration_step4'] = {
                'emergency_contact_name': form.cleaned_data['emergency_contact_name'],
                'emergency_contact_number': form.cleaned_data['emergency_contact_number'],
                'emergency_contact_address': form.cleaned_data['emergency_contact_address'],
            }
            messages.success(request, 'Step 4 complete. Upload your valid ID.')
            return redirect('accounts:register_step5')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        initial_data = request.session.get('registration_step4', {})
        form = RegistrationStep4Form(initial=initial_data)
    return render(request, 'accounts/register_step4.html', {'form': form, 'step': 4, 'total_steps': 5})


def register_step5_view(request):
    if ('registration_step1' not in request.session or
        'registration_step2' not in request.session or
        'registration_step3' not in request.session or
        'registration_step4' not in request.session):
        messages.error(request, 'Please complete all previous steps first')
        return redirect('accounts:register_step1')

    if request.method == 'POST':
        form = RegistrationStep5Form(request.POST, request.FILES)
        if form.is_valid():
            registration_data = {}
            registration_data.update(request.session.get('registration_step1', {}))
            registration_data.update(request.session.get('registration_step2', {}))
            registration_data.update(request.session.get('registration_step3', {}))
            registration_data.update(request.session.get('registration_step4', {}))

            user = RegistrationService.create_user(
                registration_data=registration_data,
                valid_id_file=form.cleaned_data['valid_id'],
                ip_address=get_client_ip(request)
            )

            if user:
                # clear registration session data
                for key in ['registration_step1', 'registration_step2', 'registration_step3', 'registration_step4']:
                    request.session.pop(key, None)
                messages.success(request, 'Registration successful! Please wait for admin verification.')
                return redirect('accounts:register_success')
            else:
                messages.error(request, 'Registration failed. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = RegistrationStep5Form()
    return render(request, 'accounts/register_step5.html', {'form': form, 'step': 5, 'total_steps': 5})


def register_success_view(request):
    return render(request, 'accounts/register_success.html')


# -------------------------------
# Admin user management
# -------------------------------
def user_list_view(request):
    current_user = get_current_user(request)
    if not current_user:
        return require_login_redirect(request)

    if not current_user.is_admin():
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')

    users = User.objects.all().order_by('-created_at')

    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    verified_filter = request.GET.get('verified', '')
    if verified_filter == 'true':
        users = users.filter(is_verified=True)
    elif verified_filter == 'false':
        users = users.filter(is_verified=False)

    active_filter = request.GET.get('active', '')
    if active_filter == 'true':
        users = users.filter(is_active=True)
    elif active_filter == 'false':
        users = users.filter(is_active=False)

    paginator = Paginator(users, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'verified_filter': verified_filter,
        'active_filter': active_filter,
        'total_count': users.count(),
    }
    return render(request, 'accounts/user_list.html', context)


def user_detail_view(request, user_id):
    current_user = get_current_user(request)
    if not current_user:
        return require_login_redirect(request)

    if not current_user.is_admin():
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')

    target = User.objects.filter(id=user_id).first()
    if not target:
        messages.error(request, 'User not found')
        return redirect('accounts:user_list')

    recent_logs = AuditLog.objects.filter(Q(user=target) | Q(target_user=target)).order_by('-timestamp')[:10]
    return render(request, 'accounts/user_detail.html', {'user': target, 'recent_logs': recent_logs})


def verify_user_view(request, user_id):
    current_user = get_current_user(request)
    if not current_user:
        return require_login_redirect(request)
    if not current_user.is_admin():
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')

    if request.method == 'POST':
        target = User.objects.filter(id=user_id).first()
        if not target:
            messages.error(request, 'User not found')
            return redirect('accounts:user_list')
        admin = current_user
        target.is_verified = True
        target.verified_at = timezone.now()
        target.verified_by = admin
        target.save()
        try:
            AuditLog.log(
                action_type='user_verified',
                description=f'Admin {admin.username} verified user {target.username}',
                user=admin,
                target_user=target,
                ip_address=get_client_ip(request)
            )
        except Exception:
            pass
        messages.success(request, f'User {target.username} has been verified')
    return redirect('accounts:user_detail', user_id=user_id)


def toggle_user_status_view(request, user_id):
    current_user = get_current_user(request)
    if not current_user:
        return require_login_redirect(request)
    if not current_user.is_admin():
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')

    if request.method == 'POST':
        target = User.objects.filter(id=user_id).first()
        if not target:
            messages.error(request, 'User not found')
            return redirect('accounts:user_list')
        admin = current_user
        target.is_active = not target.is_active
        target.save()
        try:
            AuditLog.log(
                action_type='user_reactivated' if target.is_active else 'user_deactivated',
                description=f'Admin {admin.username} {"activated" if target.is_active else "deactivated"} user {target.username}',
                user=admin,
                target_user=target,
                ip_address=get_client_ip(request)
            )
        except Exception:
            pass
        status = 'activated' if target.is_active else 'deactivated'
        messages.success(request, f'User {target.username} has been {status}')
    return redirect('accounts:user_detail', user_id=user_id)


# -------------------------------
# Password / Forgot-password / Edit profile
# -------------------------------
def change_password_view(request):
    current_user = get_current_user(request)
    if not current_user:
        return require_login_redirect(request)

    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']
            security_answer = form.cleaned_data['security_answer']

            if not current_user.check_password(current_password):
                messages.error(request, 'Current password is incorrect')
                return render(request, 'accounts/change_password.html', {'form': form, 'security_question': current_user.security_question})

            if not check_password(security_answer, current_user.security_answer):
                messages.error(request, 'Security answer is incorrect')
                return render(request, 'accounts/change_password.html', {'form': form, 'security_question': current_user.security_question})

            current_user.set_password(new_password)
            current_user.save()
            try:
                AuditLog.log(
                    action_type='password_changed',
                    description=f'User {current_user.username} changed their password',
                    user=current_user,
                    ip_address=get_client_ip(request)
                )
            except Exception:
                pass
            messages.success(request, 'Password changed successfully')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ChangePasswordForm()
    return render(request, 'accounts/change_password.html', {'form': form, 'security_question': current_user.security_question})


def forgot_password_step1_view(request):
    if request.method == 'POST':
        form = ForgotPasswordStep1Form(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            user = User.objects.filter(username=username).first()
            if not user:
                messages.error(request, 'Username not found')
                return render(request, 'accounts/forgot_password_step1.html', {'form': form})
            request.session['forgot_password_user_id'] = user.id
            request.session['forgot_password_username'] = username
            return redirect('accounts:forgot_password_step2')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ForgotPasswordStep1Form()
    return render(request, 'accounts/forgot_password_step1.html', {'form': form})


def forgot_password_step2_view(request):
    user_id = request.session.get('forgot_password_user_id')
    if not user_id:
        messages.error(request, 'Please start from step 1')
        return redirect('accounts:forgot_password_step1')

    user = User.objects.filter(id=user_id).first()
    if not user:
        messages.error(request, 'User not found')
        return redirect('accounts:forgot_password_step1')

    if request.method == 'POST':
        form = ForgotPasswordStep2Form(request.POST)
        if form.is_valid():
            security_answer = form.cleaned_data['security_answer']
            if check_password(security_answer, user.security_answer):
                request.session['forgot_password_verified'] = True
                return redirect('accounts:forgot_password_step3')
            else:
                messages.error(request, 'Incorrect answer')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ForgotPasswordStep2Form()
    return render(request, 'accounts/forgot_password_step2.html', {'form': form, 'security_question': user.security_question, 'username': user.username})


def forgot_password_step3_view(request):
    user_id = request.session.get('forgot_password_user_id')
    verified = request.session.get('forgot_password_verified')
    if not user_id or not verified:
        messages.error(request, 'Please complete previous steps')
        return redirect('accounts:forgot_password_step1')

    user = User.objects.filter(id=user_id).first()
    if not user:
        messages.error(request, 'User not found')
        return redirect('accounts:forgot_password_step1')

    if request.method == 'POST':
        form = ForgotPasswordStep3Form(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save()
            try:
                AuditLog.log(
                    action_type='password_reset',
                    description=f'User {user.username} reset their password via security question',
                    user=user,
                    ip_address=get_client_ip(request)
                )
            except Exception:
                pass
            # clear session keys for forgot password
            request.session.pop('forgot_password_user_id', None)
            request.session.pop('forgot_password_username', None)
            request.session.pop('forgot_password_verified', None)
            messages.success(request, 'Password reset successfully. Please login with your new password.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ForgotPasswordStep3Form()
    return render(request, 'accounts/forgot_password_step3.html', {'form': form, 'username': user.username})


def edit_profile_view(request):
    current_user = get_current_user(request)
    if not current_user:
        return require_login_redirect(request)

    if request.method == 'POST':
        form = EditProfileForm(request.POST)
        if form.is_valid():
            # update allowed fields only
            current_user.first_name = form.cleaned_data['first_name']
            current_user.middle_name = form.cleaned_data.get('middle_name', '')
            current_user.last_name = form.cleaned_data['last_name']
            current_user.suffix = form.cleaned_data.get('suffix', '')
            current_user.birthdate = form.cleaned_data['birthdate']
            current_user.sex = form.cleaned_data['sex']
            current_user.religion = form.cleaned_data['religion']
            current_user.nationality = form.cleaned_data['nationality']
            current_user.civil_status = form.cleaned_data['civil_status']
            current_user.home_address = form.cleaned_data['home_address']
            current_user.contact_number = form.cleaned_data['contact_number']
            current_user.educational_attainment = form.cleaned_data['educational_attainment']
            current_user.employment_status = form.cleaned_data['employment_status']
            current_user.occupation = form.cleaned_data['occupation']
            current_user.emergency_contact_name = form.cleaned_data['emergency_contact_name']
            current_user.emergency_contact_number = form.cleaned_data['emergency_contact_number']
            current_user.emergency_contact_address = form.cleaned_data['emergency_contact_address']
            current_user.save()
            try:
                AuditLog.log(
                    action_type='profile_updated',
                    description=f'User {current_user.username} updated their profile',
                    user=current_user,
                    ip_address=get_client_ip(request)
                )
            except Exception:
                pass
            messages.success(request, 'Profile updated successfully')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        initial_data = {
            'first_name': current_user.first_name,
            'middle_name': current_user.middle_name,
            'last_name': current_user.last_name,
            'suffix': current_user.suffix,
            'birthdate': current_user.birthdate,
            'sex': current_user.sex,
            'religion': current_user.religion,
            'nationality': current_user.nationality,
            'civil_status': current_user.civil_status,
            'home_address': current_user.home_address,
            'contact_number': current_user.contact_number,
            'educational_attainment': current_user.educational_attainment,
            'employment_status': current_user.employment_status,
            'occupation': current_user.occupation,
            'emergency_contact_name': current_user.emergency_contact_name,
            'emergency_contact_number': current_user.emergency_contact_number,
            'emergency_contact_address': current_user.emergency_contact_address,
        }
        form = EditProfileForm(initial=initial_data)
    return render(request, 'accounts/edit_profile.html', {'form': form, 'user': current_user})


def admin_reset_password_view(request, user_id):
    current_user = get_current_user(request)
    if not current_user:
        return require_login_redirect(request)
    if not current_user.is_admin():
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')

    target = User.objects.filter(id=user_id).first()
    if not target:
        messages.error(request, 'User not found')
        return redirect('accounts:user_list')

    if request.method == 'POST':
        form = AdminResetPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            target.set_password(new_password)
            target.save()
            try:
                AuditLog.log(
                    action_type='password_reset',
                    description=f'Admin {current_user.username} reset password for user {target.username}',
                    user=current_user,
                    target_user=target,
                    ip_address=get_client_ip(request)
                )
            except Exception:
                pass
            messages.success(request, f'Password reset successfully for {target.username}')
            return redirect('accounts:user_detail', user_id=user_id)
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = AdminResetPasswordForm()
    return render(request, 'accounts/admin_reset_password.html', {'form': form, 'target_user': target})


def audit_log_view(request):
    current_user = get_current_user(request)
    if not current_user:
        return require_login_redirect(request)
    if not current_user.is_admin():
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')

    logs = AuditLog.objects.all().order_by('-timestamp')

    action_type = request.GET.get('action_type', '')
    if action_type:
        logs = logs.filter(action_type=action_type)

    date_from = request.GET.get('date_from', '')
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)

    date_to = request.GET.get('date_to', '')
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    search = request.GET.get('search', '')
    if search:
        logs = logs.filter(description__icontains=search)

    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    form = AuditLogFilterForm(initial={
        'action_type': action_type,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
    })

    context = {
        'page_obj': page_obj,
        'form': form,
        'total_count': logs.count(),
        'action_type': action_type,
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
    }
    return render(request, 'accounts/audit_log.html', context)