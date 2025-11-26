# [BACKEND] Request handlers (view functions)
# Handles: PWD CRUD, search, dashboard, document management
# PWD Views - Registration, List, Dashboard

import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.conf import settings
from .models import PWDProfile, PWDDocument
from .forms import PWDRegistrationForm
from accounts.models import User, AuditLog
from datetime import date

def get_client_ip(request):
    #get client IP add
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def dashboard_view(request):
    #admin dashboard with stats
    
    #check if logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    #check if admin
    role = request.session.get('role')
    if role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('accounts:profile')
    
    #PWD stats ==========================================================================================
    
    #total counts
    total_pwd = PWDProfile.objects.count()
    active_pwd = PWDProfile.objects.filter(is_active=True).count()
    inactive_pwd = PWDProfile.objects.filter(is_active=False).count()
    
    #by sex
    male_pwd = PWDProfile.objects.filter(sex='M', is_active=True).count()
    female_pwd = PWDProfile.objects.filter(sex='F', is_active=True).count()
    
    #by degree of disability
    low_degree = PWDProfile.objects.filter(degree_of_disability='Low', is_active=True).count()
    moderate_degree = PWDProfile.objects.filter(degree_of_disability='Moderate', is_active=True).count()
    high_degree = PWDProfile.objects.filter(degree_of_disability='High', is_active=True).count()
    
    #by disability type
    disability_stats = PWDProfile.objects.filter(is_active=True).values('disability_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    #by emp stats
    employment_stats = PWDProfile.objects.filter(is_active=True).values('employment_status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    #by age group
    today = date.today()
    
    def get_age(birthdate):
        age = today.year - birthdate.year
        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age -= 1
        return age
    
    age_0_17 = 0
    age_18_30 = 0
    age_31_59 = 0
    age_60_plus = 0
    
    for pwd in PWDProfile.objects.filter(is_active=True):
        age = get_age(pwd.birthdate)
        if age <= 17:
            age_0_17 += 1
        elif age <= 30:
            age_18_30 += 1
        elif age <= 59:
            age_31_59 += 1
        else:
            age_60_plus += 1
    
    #user stats ==========================================================================================
    
    total_users = User.objects.count()
    verified_users = User.objects.filter(is_verified=True).count()
    unverified_users = User.objects.filter(is_verified=False).count()
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = User.objects.filter(is_active=False).count()
    admin_users = User.objects.filter(role='admin').count()
    basic_users = User.objects.filter(role='basic_user').count()
    
    #recent activity ==========================================================================================
    
    recent_logs = AuditLog.objects.all().order_by('-timestamp')[:10]
    
    context = {
        'username': request.session.get('username'),
        
        #PWD Stats
        'total_pwd': total_pwd,
        'active_pwd': active_pwd,
        'inactive_pwd': inactive_pwd,
        'male_pwd': male_pwd,
        'female_pwd': female_pwd,
        'low_degree': low_degree,
        'moderate_degree': moderate_degree,
        'high_degree': high_degree,
        'disability_stats': disability_stats,
        'employment_stats': employment_stats,
        'age_0_17': age_0_17,
        'age_18_30': age_18_30,
        'age_31_59': age_31_59,
        'age_60_plus': age_60_plus,
        
        #user Stats
        'total_users': total_users,
        'verified_users': verified_users,
        'unverified_users': unverified_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'admin_users': admin_users,
        'basic_users': basic_users,
        
        #recent activity
        'recent_logs': recent_logs,
    }
    
    return render(request, 'pwd/dashboard.html', context)


def pwd_create_view(request):
    #register new PWD
    
    #check if logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    #check if verified
    is_verified = request.session.get('is_verified')
    if not is_verified:
        messages.error(request, 'Your account must be verified to register PWDs')
        return redirect('accounts:profile')
    
    try:
        current_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return redirect('accounts:login')
    
    if request.method == 'POST':
        form = PWDRegistrationForm(request.POST, request.FILES)
        
        if form.is_valid():
            unique_id = PWDProfile.generate_unique_id()
            
            photo_path = None
            if form.cleaned_data.get('photo'):
                photo_path = save_pwd_photo(form.cleaned_data['photo'], unique_id)
            
            #create PWD profile
            pwd = PWDProfile.objects.create(
                unique_id=unique_id,
                
                #personal info
                first_name=form.cleaned_data['first_name'],
                middle_name=form.cleaned_data.get('middle_name', ''),
                last_name=form.cleaned_data['last_name'],
                suffix=form.cleaned_data.get('suffix', ''),
                birthdate=form.cleaned_data['birthdate'],
                sex=form.cleaned_data['sex'],
                civil_status=form.cleaned_data['civil_status'],
                barangay=form.cleaned_data['barangay'],
                address=form.cleaned_data['address'],
                contact_number=form.cleaned_data['contact_number'],
                religion=form.cleaned_data['religion'],
                nationality=form.cleaned_data.get('nationality', 'Filipino'),
                photo_path=photo_path,
                
                #household info
                educational_attainment=form.cleaned_data['educational_attainment'],
                employment_status=form.cleaned_data['employment_status'],
                occupation=form.cleaned_data.get('occupation', ''),
                type_of_employment=form.cleaned_data.get('type_of_employment', ''),
                
                #socio economic info
                household_income=form.cleaned_data.get('household_income'),
                household_size=form.cleaned_data.get('household_size'),
                living_situation=form.cleaned_data.get('living_situation', ''),
                housing_type=form.cleaned_data.get('housing_type', ''),
                guardian_name=form.cleaned_data['guardian_name'],
                guardian_contact=form.cleaned_data['guardian_contact'],
                
                #medical info
                disability_type=form.cleaned_data['disability_type'],
                degree_of_disability=form.cleaned_data['degree_of_disability'],
                cause_of_disability=form.cleaned_data.get('cause_of_disability', ''),
                date_diagnosed=form.cleaned_data.get('date_diagnosed'),
                assistive_devices=form.cleaned_data.get('assistive_devices', ''),
                medication=form.cleaned_data.get('medication', ''),
                
                #other info
                philhealth_number=form.cleaned_data.get('philhealth_number', ''),
                sss_gsis_number=form.cleaned_data.get('sss_gsis_number', ''),
                skills_hobbies=form.cleaned_data.get('skills_hobbies', ''),
                organization_membership=form.cleaned_data.get('organization_membership', ''),
                
                #emergency contact info
                emergency_contact_name=form.cleaned_data['emergency_contact_name'],
                emergency_contact_number=form.cleaned_data['emergency_contact_number'],
                emergency_contact_address=form.cleaned_data['emergency_contact_address'],
                
                #audit
                created_by=current_user,
                updated_by=current_user,
            )
            
            #save documents
            documents = request.FILES.getlist('documents')
            for doc in documents:
                save_pwd_document(doc, pwd, current_user)
            
            #log action
            AuditLog.log(
                action_type='user_registered',
                description=f'PWD registered: {pwd.unique_id} - {pwd.get_full_name()}',
                user=current_user,
                target_pwd=pwd,
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, f'PWD registered successfully! ID: {unique_id}')
            return redirect('pwd:pwd_detail', pwd_id=pwd.id)
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        form = PWDRegistrationForm()
    
    return render(request, 'pwd/pwd_create.html', {'form': form})


def pwd_list_view(request):
    #list all PWDs with search, filter, pagination
    
    #check if logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    #check if verified
    is_verified = request.session.get('is_verified')
    if not is_verified:
        messages.error(request, 'Your account must be verified to view PWDs')
        return redirect('accounts:profile')
    
    pwds = PWDProfile.objects.all().order_by('-created_at')
    
    #search
    search_query = request.GET.get('search', '')
    if search_query:
        pwds = pwds.filter(
            Q(unique_id__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    #filter by:::
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        pwds = pwds.filter(is_active=True)
    elif status_filter == 'inactive':
        pwds = pwds.filter(is_active=False)
    
    disability_filter = request.GET.get('disability', '')
    if disability_filter:
        pwds = pwds.filter(disability_type=disability_filter)
    
    degree_filter = request.GET.get('degree', '')
    if degree_filter:
        pwds = pwds.filter(degree_of_disability=degree_filter)
    
    paginator = Paginator(pwds, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'disability_filter': disability_filter,
        'degree_filter': degree_filter,
        'total_count': pwds.count(),
        'disability_types': [
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
    }
    
    return render(request, 'pwd/pwd_list.html', context)


def pwd_detail_view(request, pwd_id):
    #view PWD details
    
    #check if logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    #check if verified
    is_verified = request.session.get('is_verified')
    if not is_verified:
        messages.error(request, 'Your account must be verified to view PWDs')
        return redirect('accounts:profile')
    
    try:
        pwd = PWDProfile.objects.get(id=pwd_id)
        documents = pwd.documents.all()
        
        context = {
            'pwd': pwd,
            'documents': documents,
            'is_admin': request.session.get('role') == 'admin',
        }
        
        return render(request, 'pwd/pwd_detail.html', context)
    except PWDProfile.DoesNotExist:
        messages.error(request, 'PWD not found')
        return redirect('pwd:pwd_list')


#helper functions ==========================================================================================

def save_pwd_photo(file, unique_id):
    #save PWD photo to media/pwd_photos/
    
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'pwd_photos')
    os.makedirs(upload_dir, exist_ok=True)
    
    ext = os.path.splitext(file.name)[1]
    filename = f"{unique_id}_photo{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    with open(filepath, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    
    return f'pwd_photos/{filename}'


def save_pwd_document(file, pwd, uploaded_by):
    #save PWD document to media/pwd_documents/
    
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'pwd_documents')
    os.makedirs(upload_dir, exist_ok=True)
    
    #generate unique filename
    import time
    timestamp = int(time.time())
    ext = os.path.splitext(file.name)[1]
    filename = f"{pwd.unique_id}_{timestamp}{ext}"
    filepath = os.path.join(upload_dir, filename)
    
    with open(filepath, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    
    #create doc record
    PWDDocument.objects.create(
        pwd_profile=pwd,
        file_path=f'pwd_documents/{filename}',
        file_name=file.name,
        file_type=ext.replace('.', ''),
        file_size=file.size,
        uploaded_by=uploaded_by,
    )


def pwd_edit_view(request, pwd_id):
    #edit PWD profile
    
    #check if logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    #check if verified
    is_verified = request.session.get('is_verified')
    if not is_verified:
        messages.error(request, 'Your account must be verified to edit PWDs')
        return redirect('accounts:profile')
    
    try:
        current_user = User.objects.get(id=user_id)
        pwd = PWDProfile.objects.get(id=pwd_id)
    except (User.DoesNotExist, PWDProfile.DoesNotExist):
        messages.error(request, 'Record not found')
        return redirect('pwd:pwd_list')
    
    if request.method == 'POST':
        form = PWDRegistrationForm(request.POST, request.FILES)
        
        if form.is_valid():
            if form.cleaned_data.get('photo'):
                pwd.photo_path = save_pwd_photo(form.cleaned_data['photo'], pwd.unique_id)
            
            #update PWD prof
            pwd.first_name = form.cleaned_data['first_name']
            pwd.middle_name = form.cleaned_data.get('middle_name', '')
            pwd.last_name = form.cleaned_data['last_name']
            pwd.suffix = form.cleaned_data.get('suffix', '')
            pwd.birthdate = form.cleaned_data['birthdate']
            pwd.sex = form.cleaned_data['sex']
            pwd.civil_status = form.cleaned_data['civil_status']
            pwd.barangay = form.cleaned_data['barangay']
            pwd.address = form.cleaned_data['address']
            pwd.contact_number = form.cleaned_data['contact_number']
            pwd.religion = form.cleaned_data['religion']
            pwd.nationality = form.cleaned_data.get('nationality', 'Filipino')
            
            pwd.educational_attainment = form.cleaned_data['educational_attainment']
            pwd.employment_status = form.cleaned_data['employment_status']
            pwd.occupation = form.cleaned_data.get('occupation', '')
            pwd.type_of_employment = form.cleaned_data.get('type_of_employment', '')
            
            pwd.household_income = form.cleaned_data.get('household_income')
            pwd.household_size = form.cleaned_data.get('household_size')
            pwd.living_situation = form.cleaned_data.get('living_situation', '')
            pwd.housing_type = form.cleaned_data.get('housing_type', '')
            pwd.guardian_name = form.cleaned_data['guardian_name']
            pwd.guardian_contact = form.cleaned_data['guardian_contact']
            
            pwd.disability_type = form.cleaned_data['disability_type']
            pwd.degree_of_disability = form.cleaned_data['degree_of_disability']
            pwd.cause_of_disability = form.cleaned_data.get('cause_of_disability', '')
            pwd.date_diagnosed = form.cleaned_data.get('date_diagnosed')
            pwd.assistive_devices = form.cleaned_data.get('assistive_devices', '')
            pwd.medication = form.cleaned_data.get('medication', '')
            
            pwd.philhealth_number = form.cleaned_data.get('philhealth_number', '')
            pwd.sss_gsis_number = form.cleaned_data.get('sss_gsis_number', '')
            pwd.skills_hobbies = form.cleaned_data.get('skills_hobbies', '')
            pwd.organization_membership = form.cleaned_data.get('organization_membership', '')
            
            pwd.emergency_contact_name = form.cleaned_data['emergency_contact_name']
            pwd.emergency_contact_number = form.cleaned_data['emergency_contact_number']
            pwd.emergency_contact_address = form.cleaned_data['emergency_contact_address']
            
            pwd.updated_by = current_user
            pwd.save()
            
            #save new docs if provided
            documents = request.FILES.getlist('documents')
            for doc in documents:
                save_pwd_document(doc, pwd, current_user)
            
            #log action
            AuditLog.log(
                action_type='profile_updated',
                description=f'PWD updated: {pwd.unique_id} - {pwd.get_full_name()}',
                user=current_user,
                target_pwd=pwd,
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, 'PWD profile updated successfully')
            return redirect('pwd:pwd_detail', pwd_id=pwd.id)
        else:
            messages.error(request, 'Please correct the errors below')
    else:
        #pre fill form with current data
        initial_data = {
            'first_name': pwd.first_name,
            'middle_name': pwd.middle_name,
            'last_name': pwd.last_name,
            'suffix': pwd.suffix,
            'birthdate': pwd.birthdate,
            'sex': pwd.sex,
            'civil_status': pwd.civil_status,
            'barangay': pwd.barangay,
            'address': pwd.address,
            'contact_number': pwd.contact_number,
            'religion': pwd.religion,
            'nationality': pwd.nationality,
            'educational_attainment': pwd.educational_attainment,
            'employment_status': pwd.employment_status,
            'occupation': pwd.occupation,
            'type_of_employment': pwd.type_of_employment,
            'household_income': pwd.household_income,
            'household_size': pwd.household_size,
            'living_situation': pwd.living_situation,
            'housing_type': pwd.housing_type,
            'guardian_name': pwd.guardian_name,
            'guardian_contact': pwd.guardian_contact,
            'disability_type': pwd.disability_type,
            'degree_of_disability': pwd.degree_of_disability,
            'cause_of_disability': pwd.cause_of_disability,
            'date_diagnosed': pwd.date_diagnosed,
            'assistive_devices': pwd.assistive_devices,
            'medication': pwd.medication,
            'philhealth_number': pwd.philhealth_number,
            'sss_gsis_number': pwd.sss_gsis_number,
            'skills_hobbies': pwd.skills_hobbies,
            'organization_membership': pwd.organization_membership,
            'emergency_contact_name': pwd.emergency_contact_name,
            'emergency_contact_number': pwd.emergency_contact_number,
            'emergency_contact_address': pwd.emergency_contact_address,
        }
        form = PWDRegistrationForm(initial=initial_data)
    
    return render(request, 'pwd/pwd_edit.html', {'form': form, 'pwd': pwd})


def pwd_toggle_status_view(request, pwd_id):
    #archive or Reactivate PWD (Admin only)"""

    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    role = request.session.get('role')
    if role != 'admin':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('pwd:pwd_list')
    
    if request.method == 'POST':
        try:
            current_user = User.objects.get(id=user_id)
            pwd = PWDProfile.objects.get(id=pwd_id)
            
            #toggle stats
            pwd.is_active = not pwd.is_active
            pwd.updated_by = current_user
            pwd.save()
            
            #log action
            action = 'pwd_reactivated' if pwd.is_active else 'pwd_archived'
            status_text = 'reactivated' if pwd.is_active else 'archived'
            
            AuditLog.log(
                action_type=action,
                description=f'PWD {status_text}: {pwd.unique_id} - {pwd.get_full_name()}',
                user=current_user,
                target_pwd=pwd,
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, f'PWD {pwd.unique_id} has been {status_text}')
            return redirect('pwd:pwd_detail', pwd_id=pwd.id)
            
        except (User.DoesNotExist, PWDProfile.DoesNotExist):
            messages.error(request, 'Record not found')
    
    return redirect('pwd:pwd_list')


def pwd_delete_document_view(request, pwd_id, doc_id):
    #delete PWD docs
    
    #check if logged in
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first')
        return redirect('accounts:login')
    
    #check if verified
    is_verified = request.session.get('is_verified')
    if not is_verified:
        messages.error(request, 'Your account must be verified')
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        try:
            document = PWDDocument.objects.get(id=doc_id, pwd_profile_id=pwd_id)
            
            #delete files
            file_path = os.path.join(settings.MEDIA_ROOT, document.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            #delete record
            document.delete()
            
            messages.success(request, 'Document deleted successfully')
        except PWDDocument.DoesNotExist:
            messages.error(request, 'Document not found')
    
    return redirect('pwd:pwd_detail', pwd_id=pwd_id)