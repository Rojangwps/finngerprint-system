# [BACKEND] Request handlers (view functions)
# Handles: register, login, logout, profile, user management, audit log


from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect
from django.contrib import messages
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
    AuditLogFilterForm
)
from .services import RegistrationService
from datetime import datetime, timedelta



def get_client_ip(request):
    #get client IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def login_view(request):
    """Simple login view"""
    
    #if user already logged in redirect to approp page
    if request.session.get('user_id'):
        user = User.objects.get(id=request.session['user_id'])
        if user.is_admin():
            return redirect('pwd:dashboard')  # Will create this later
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            try:
                #find user
                user = User.objects.get(username=username)
                
                #check if active
                if not user.is_active:
                    messages.error(request, 'Your account is inactive. Contact admin.')
                    return render(request, 'accounts/login.html', {'form': form})
                
                #check pass
                if user.check_password(password):
                    #login success ==create session
                    request.session['user_id'] = user.id
                    request.session['username'] = user.username
                    request.session['role'] = user.role
                    request.session['is_verified'] = user.is_verified
                    
                    #log login
                    AuditLog.log(
                        action_type='login',
                        description=f'User {username} logged in',
                        user=user,
                        ip_address=get_client_ip(request)
                    )
                    
                    messages.success(request, f'Welcome, {user.first_name}!')
                    
                    if user.is_admin():
                        return redirect('pwd:dashboard')  
                    else:
                        return redirect('accounts:profile') 
                else:
                    messages.error(request, 'Invalid username or password')
            
            except User.DoesNotExist:
                messages.error(request, 'Invalid username or password')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = LoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    
    #get user before clearing session
    user_id = request.session.get('user_id')
    username = request.session.get('username')
    
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            
            #log the logout
            AuditLog.log(
                action_type='logout',
                description=f'User {username} logged out',
                user=user,
                ip_address=get_client_ip(request)
            )
        except User.DoesNotExist:
            pass
    
    #clear session
    request.session.flush()
    
    messages.success(request, 'You have been logged out successfully')
    return redirect('accounts:login')


def profile_view(request):
    """Simple profile view - shows current user info"""
    
    #check if logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    try:
        user = User.objects.get(id=user_id)
        return render(request, 'accounts/profile.html', {'user': user})
    except User.DoesNotExist:
        request.session.flush()
        messages.error(request, 'User not found')
        return redirect('accounts:login')



def register_step1_view(request):
    #step 1 acc credentials
    
    if request.method == 'POST':
        form = RegistrationStep1Form(request.POST)
        
        if form.is_valid():
            # store step 1 data ession
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
        #pre fill form if data == in session
        initial_data = request.session.get('registration_step1', {})
        form = RegistrationStep1Form(initial=initial_data)
    
    return render(request, 'accounts/register_step1.html', {
        'form': form,
        'step': 1,
        'total_steps': 5
    })


def register_step2_view(request):
    #step 2 personal info
    
    #check if step 1 completed
    if 'registration_step1' not in request.session:
        messages.error(request, 'Please complete Step 1 first')
        return redirect('accounts:register_step1')
    
    if request.method == 'POST':
        form = RegistrationStep2Form(request.POST)
        
        if form.is_valid():
            #store step 2 data session
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
    
    return render(request, 'accounts/register_step2.html', {
        'form': form,
        'step': 2,
        'total_steps': 5
    })


def register_step3_view(request):
    #step 3 household info
    
    #check if prev steps are completed
    if 'registration_step1' not in request.session or 'registration_step2' not in request.session:
        messages.error(request, 'Please complete previous steps first')
        return redirect('accounts:register_step1')
    
    if request.method == 'POST':
        form = RegistrationStep3Form(request.POST)
        
        if form.is_valid():
            #store step 3 data session
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
    
    return render(request, 'accounts/register_step3.html', {
        'form': form,
        'step': 3,
        'total_steps': 5
    })


def register_step4_view(request):
    #step 4 emergency contact
    
    #check if previous steps are completed
    if ('registration_step1' not in request.session or 
        'registration_step2' not in request.session or 
        'registration_step3' not in request.session):
        messages.error(request, 'Please complete previous steps first')
        return redirect('accounts:register_step1')
    
    if request.method == 'POST':
        form = RegistrationStep4Form(request.POST)
        
        if form.is_valid():
            #store step 4 data session
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
    
    return render(request, 'accounts/register_step4.html', {
        'form': form,
        'step': 4,
        'total_steps': 5
    })


def register_step5_view(request):
    #step 5 valid ID upload
    
    # Check if all previous steps are completed
    if ('registration_step1' not in request.session or 
        'registration_step2' not in request.session or 
        'registration_step3' not in request.session or
        'registration_step4' not in request.session):
        messages.error(request, 'Please complete all previous steps first')
        return redirect('accounts:register_step1')
    
    if request.method == 'POST':
        form = RegistrationStep5Form(request.POST, request.FILES)
        
        if form.is_valid():
            #combine all registration data
            registration_data = {}
            registration_data.update(request.session['registration_step1'])
            registration_data.update(request.session['registration_step2'])
            registration_data.update(request.session['registration_step3'])
            registration_data.update(request.session['registration_step4'])
            
            #create user
            user = RegistrationService.create_user(
                registration_data=registration_data,
                valid_id_file=form.cleaned_data['valid_id'],
                ip_address=get_client_ip(request)
            )
            
            if user:
                #clear registration session data
                for key in ['registration_step1', 'registration_step2', 'registration_step3', 'registration_step4']:
                    if key in request.session:
                        del request.session[key]
                
                messages.success(request, 'Registration successful! Please wait for admin verification.')
                return redirect('accounts:register_success')
            else:
                messages.error(request, 'Registration failed. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = RegistrationStep5Form()
    
    return render(request, 'accounts/register_step5.html', {
        'form': form,
        'step': 5,
        'total_steps': 5
    })


def register_success_view(request):
    return render(request, 'accounts/register_success.html')


def user_list_view(request):
    #admin view list all users with search, filter, pagination
    
    #check if logged in and admin
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    role = request.session.get('role')
    if role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')
    
    #get all users
    users = User.objects.all().order_by('-created_at')
    
    #search
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    #filter by verification stats
    verified_filter = request.GET.get('verified', '')
    if verified_filter == 'true':
        users = users.filter(is_verified=True)
    elif verified_filter == 'false':
        users = users.filter(is_verified=False)
    
    #filter by active stats
    active_filter = request.GET.get('active', '')
    if active_filter == 'true':
        users = users.filter(is_active=True)
    elif active_filter == 'false':
        users = users.filter(is_active=False)
    
    #pagination 
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
    #admin view user details
    
    #check if logged in and admin
    current_user_id = request.session.get('user_id')
    if not current_user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    role = request.session.get('role')
    if role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')
    
    try:
        user = User.objects.get(id=user_id)
        
        #get recent audit logs for this user
        recent_logs = AuditLog.objects.filter(
            Q(user=user) | Q(target_user=user)
        ).order_by('-timestamp')[:10]
        
        context = {
            'user': user,
            'recent_logs': recent_logs,
        }
        
        return render(request, 'accounts/user_detail.html', context)
    except User.DoesNotExist:
        messages.error(request, 'User not found')
        return redirect('accounts:user_list')


def verify_user_view(request, user_id):
    #admin action verify user acc
    
    #check if logged in and admin
    current_user_id = request.session.get('user_id')
    if not current_user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    role = request.session.get('role')
    if role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            admin = User.objects.get(id=current_user_id)
            
            #verify user
            from datetime import datetime
            user.is_verified = True
            user.verified_at = datetime.now()
            user.verified_by = admin
            user.save()
            
            #log action
            AuditLog.log(
                action_type='user_verified',
                description=f'Admin {admin.username} verified user {user.username}',
                user=admin,
                target_user=user,
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, f'User {user.username} has been verified')
            return redirect('accounts:user_detail', user_id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found')
    
    return redirect('accounts:user_list')


def toggle_user_status_view(request, user_id):
    #admin action act/deact user
    
    #check if logged in and admin
    current_user_id = request.session.get('user_id')
    if not current_user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    role = request.session.get('role')
    if role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            admin = User.objects.get(id=current_user_id)
            
            #toggle stats
            user.is_active = not user.is_active
            user.save()
            
            #log action
            action = 'user_reactivated' if user.is_active else 'user_deactivated'
            description = f'Admin {admin.username} {"activated" if user.is_active else "deactivated"} user {user.username}'
            
            AuditLog.log(
                action_type=action,
                description=description,
                user=admin,
                target_user=user,
                ip_address=get_client_ip(request)
            )
            
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User {user.username} has been {status}')
            return redirect('accounts:user_detail', user_id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found')
    
    return redirect('accounts:user_list')


def change_password_view(request):
    #user changes own pass
    
    #check if logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        
        if form.is_valid():
            current_password = form.cleaned_data['current_password']
            new_password = form.cleaned_data['new_password']
            security_answer = form.cleaned_data['security_answer']
            
            #verify current pass
            if not user.check_password(current_password):
                messages.error(request, 'Current password is incorrect')
                return render(request, 'accounts/change_password.html', {'form': form})
            
            #verify security ans
            from django.contrib.auth.hashers import check_password
            if not check_password(security_answer, user.security_answer):
                messages.error(request, 'Security answer is incorrect')
                return render(request, 'accounts/change_password.html', {'form': form})
            
            #change pass
            user.set_password(new_password)
            user.save()
            
            #log action
            AuditLog.log(
                action_type='password_changed',
                description=f'User {user.username} changed their password',
                user=user,
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, 'Password changed successfully')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ChangePasswordForm()
    
    return render(request, 'accounts/change_password.html', {
        'form': form,
        'security_question': user.security_question
    })


def forgot_password_step1_view(request):
    #forgot pass step 1 enter username
    
    if request.method == 'POST':
        form = ForgotPasswordStep1Form(request.POST)
        
        if form.is_valid():
            username = form.cleaned_data['username']
            
            try:
                user = User.objects.get(username=username)
                
                #store in session for next steps
                request.session['forgot_password_user_id'] = user.id
                request.session['forgot_password_username'] = username
                
                return redirect('accounts:forgot_password_step2')
            except User.DoesNotExist:
                messages.error(request, 'Username not found')
    else:
        form = ForgotPasswordStep1Form()
    
    return render(request, 'accounts/forgot_password_step1.html', {'form': form})


def forgot_password_step2_view(request):
    #forgot password step 2 ans security question
    
    #check if step 1 completed
    user_id = request.session.get('forgot_password_user_id')
    if not user_id:
        messages.error(request, 'Please start from step 1')
        return redirect('accounts:forgot_password_step1')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found')
        return redirect('accounts:forgot_password_step1')
    
    if request.method == 'POST':
        form = ForgotPasswordStep2Form(request.POST)
        
        if form.is_valid():
            security_answer = form.cleaned_data['security_answer']
            
            #verify security ans
            from django.contrib.auth.hashers import check_password
            if check_password(security_answer, user.security_answer):
                #mark verified
                request.session['forgot_password_verified'] = True
                return redirect('accounts:forgot_password_step3')
            else:
                messages.error(request, 'Incorrect answer')
    else:
        form = ForgotPasswordStep2Form()
    
    return render(request, 'accounts/forgot_password_step2.html', {
        'form': form,
        'security_question': user.security_question,
        'username': user.username
    })


def forgot_password_step3_view(request):
    #forgot password step 3 set new pass
    
    #check if previous steps completed
    user_id = request.session.get('forgot_password_user_id')
    verified = request.session.get('forgot_password_verified')
    
    if not user_id or not verified:
        messages.error(request, 'Please complete previous steps')
        return redirect('accounts:forgot_password_step1')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found')
        return redirect('accounts:forgot_password_step1')
    
    if request.method == 'POST':
        form = ForgotPasswordStep3Form(request.POST)
        
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            
            #set new password
            user.set_password(new_password)
            user.save()
            
            #log action
            AuditLog.log(
                action_type='password_reset',
                description=f'User {user.username} reset their password via security question',
                user=user,
                ip_address=get_client_ip(request)
            )
            
            #clear session
            del request.session['forgot_password_user_id']
            del request.session['forgot_password_username']
            del request.session['forgot_password_verified']
            
            messages.success(request, 'Password reset successfully. Please login with your new password.')
            return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = ForgotPasswordStep3Form()
    
    return render(request, 'accounts/forgot_password_step3.html', {
        'form': form,
        'username': user.username
    })


def edit_profile_view(request):
    #user edits own prof
    
    #check if logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = EditProfileForm(request.POST)
        
        if form.is_valid():
            #update user fields
            user.first_name = form.cleaned_data['first_name']
            user.middle_name = form.cleaned_data.get('middle_name', '')
            user.last_name = form.cleaned_data['last_name']
            user.suffix = form.cleaned_data.get('suffix', '')
            user.birthdate = form.cleaned_data['birthdate']
            user.sex = form.cleaned_data['sex']
            user.religion = form.cleaned_data['religion']
            user.nationality = form.cleaned_data['nationality']
            user.civil_status = form.cleaned_data['civil_status']
            user.home_address = form.cleaned_data['home_address']
            user.contact_number = form.cleaned_data['contact_number']
            user.educational_attainment = form.cleaned_data['educational_attainment']
            user.employment_status = form.cleaned_data['employment_status']
            user.occupation = form.cleaned_data['occupation']
            user.emergency_contact_name = form.cleaned_data['emergency_contact_name']
            user.emergency_contact_number = form.cleaned_data['emergency_contact_number']
            user.emergency_contact_address = form.cleaned_data['emergency_contact_address']
            user.save()
            
            #log action
            AuditLog.log(
                action_type='profile_updated',
                description=f'User {user.username} updated their profile',
                user=user,
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, 'Profile updated successfully')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        #pre fill form with current data
        initial_data = {
            'first_name': user.first_name,
            'middle_name': user.middle_name,
            'last_name': user.last_name,
            'suffix': user.suffix,
            'birthdate': user.birthdate,
            'sex': user.sex,
            'religion': user.religion,
            'nationality': user.nationality,
            'civil_status': user.civil_status,
            'home_address': user.home_address,
            'contact_number': user.contact_number,
            'educational_attainment': user.educational_attainment,
            'employment_status': user.employment_status,
            'occupation': user.occupation,
            'emergency_contact_name': user.emergency_contact_name,
            'emergency_contact_number': user.emergency_contact_number,
            'emergency_contact_address': user.emergency_contact_address,
        }
        form = EditProfileForm(initial=initial_data)
    
    return render(request, 'accounts/edit_profile.html', {'form': form, 'user': user})


def admin_reset_password_view(request, user_id):
    #admin resets user pass
    
    #check if logged in and admin
    current_user_id = request.session.get('user_id')
    if not current_user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    role = request.session.get('role')
    if role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')
    
    try:
        target_user = User.objects.get(id=user_id)
        admin = User.objects.get(id=current_user_id)
    except User.DoesNotExist:
        messages.error(request, 'User not found')
        return redirect('accounts:user_list')
    
    if request.method == 'POST':
        form = AdminResetPasswordForm(request.POST)
        
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            
            #set new password
            target_user.set_password(new_password)
            target_user.save()
            
            #log action
            AuditLog.log(
                action_type='password_reset',
                description=f'Admin {admin.username} reset password for user {target_user.username}',
                user=admin,
                target_user=target_user,
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, f'Password reset successfully for {target_user.username}')
            return redirect('accounts:user_detail', user_id=user_id)
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = AdminResetPasswordForm()
    
    return render(request, 'accounts/admin_reset_password.html', {
        'form': form,
        'target_user': target_user
    })


def audit_log_view(request):
    #admin view audit log viewer ++filters
    
    #check if logged in and admin
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    role = request.session.get('role')
    if role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')
    
    #get all logs
    logs = AuditLog.objects.all().order_by('-timestamp')
    
    #filter by action type
    action_type = request.GET.get('action_type', '')
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    #filter by date
    date_from = request.GET.get('date_from', '')
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    
    date_to = request.GET.get('date_to', '')
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)
    
    #search by descript
    search = request.GET.get('search', '')
    if search:
        logs = logs.filter(description__icontains=search)
    
    #pagination (50 per page)
    paginator = Paginator(logs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    #form for filters
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