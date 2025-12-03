# [BACKEND] PWD Views
# Handles: PWD CRUD, Dashboard, Documents, Fingerprint registration

import os
import json
import time
from datetime import date

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import PWDProfile, PWDDocument
from .forms import PWDRegistrationForm
from accounts.models import User, AuditLog
from .utils.fingerprint_reader import register_fingerprint


# -------------------------------
# HELPER FUNCTIONS
# -------------------------------

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def save_pwd_photo(file, unique_id):
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'pwd_photos')
    os.makedirs(upload_dir, exist_ok=True)
    ext = os.path.splitext(file.name)[1]
    filename = f"{unique_id}_photo{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, 'wb+') as dest:
        for chunk in file.chunks():
            dest.write(chunk)
    return f'pwd_photos/{filename}'


def save_pwd_document(file, pwd, uploaded_by):
    upload_dir = os.path.join(settings.MEDIA_ROOT, 'pwd_documents')
    os.makedirs(upload_dir, exist_ok=True)
    timestamp = int(time.time())
    ext = os.path.splitext(file.name)[1]
    filename = f"{pwd.unique_id}_{timestamp}{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, 'wb+') as dest:
        for chunk in file.chunks():
            dest.write(chunk)
    PWDDocument.objects.create(
        pwd_profile=pwd,
        file_path=f'pwd_documents/{filename}',
        file_name=file.name,
        file_type=ext.replace('.', ''),
        file_size=file.size,
        uploaded_by=uploaded_by,
    )


# -------------------------------
# DASHBOARD
# -------------------------------

def dashboard_view(request):
    user_id = request.session.get('user_id')
    role = request.session.get('role')
    if not user_id or role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('accounts:login' if not user_id else 'accounts:profile')

    # PWD stats
    total_pwd = PWDProfile.objects.count()
    active_pwd = PWDProfile.objects.filter(is_active=True).count()
    inactive_pwd = total_pwd - active_pwd
    male_pwd = PWDProfile.objects.filter(sex='M', is_active=True).count()
    female_pwd = PWDProfile.objects.filter(sex='F', is_active=True).count()

    low_degree = PWDProfile.objects.filter(degree_of_disability='Low', is_active=True).count()
    moderate_degree = PWDProfile.objects.filter(degree_of_disability='Moderate', is_active=True).count()
    high_degree = PWDProfile.objects.filter(degree_of_disability='High', is_active=True).count()

    disability_stats = PWDProfile.objects.filter(is_active=True).values('disability_type').annotate(
        count=Count('id')).order_by('-count')

    employment_stats = PWDProfile.objects.filter(is_active=True).values('employment_status').annotate(
        count=Count('id')).order_by('-count')

    today = date.today()
    def get_age(birthdate):
        age = today.year - birthdate.year
        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age -= 1
        return age

    age_groups = {'0_17': 0, '18_30': 0, '31_59': 0, '60_plus': 0}
    for pwd in PWDProfile.objects.filter(is_active=True):
        age = get_age(pwd.birthdate)
        if age <= 17:
            age_groups['0_17'] += 1
        elif age <= 30:
            age_groups['18_30'] += 1
        elif age <= 59:
            age_groups['31_59'] += 1
        else:
            age_groups['60_plus'] += 1

    # User stats
    total_users = User.objects.count()
    verified_users = User.objects.filter(is_verified=True).count()
    unverified_users = total_users - verified_users
    active_users = User.objects.filter(is_active=True).count()
    inactive_users = total_users - active_users
    admin_users = User.objects.filter(role='admin').count()
    basic_users = User.objects.filter(role='basic_user').count()

    recent_logs = AuditLog.objects.all().order_by('-timestamp')[:10]

    context = {
        'username': request.session.get('username'),
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
        **age_groups,
        'total_users': total_users,
        'verified_users': verified_users,
        'unverified_users': unverified_users,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'admin_users': admin_users,
        'basic_users': basic_users,
        'recent_logs': recent_logs,
    }
    return render(request, 'pwd/dashboard.html', context)


# -------------------------------
# CREATE PWD
# -------------------------------

def pwd_create_view(request):
    user_id = request.session.get('user_id')
    is_verified = request.session.get('is_verified')
    if not user_id:
        messages.error(request, 'Please login first.')
        return redirect('accounts:login')
    if not is_verified:
        messages.error(request, 'Account must be verified to register PWDs.')
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
            photo_path = save_pwd_photo(form.cleaned_data['photo'], unique_id) if form.cleaned_data.get('photo') else None

            pwd = PWDProfile.objects.create(
                unique_id=unique_id,
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
                educational_attainment=form.cleaned_data['educational_attainment'],
                employment_status=form.cleaned_data['employment_status'],
                occupation=form.cleaned_data.get('occupation', ''),
                type_of_employment=form.cleaned_data.get('type_of_employment', ''),
                household_income=form.cleaned_data.get('household_income'),
                household_size=form.cleaned_data.get('household_size'),
                living_situation=form.cleaned_data.get('living_situation', ''),
                housing_type=form.cleaned_data.get('housing_type', ''),
                guardian_name=form.cleaned_data['guardian_name'],
                guardian_contact=form.cleaned_data['guardian_contact'],
                disability_type=form.cleaned_data['disability_type'],
                degree_of_disability=form.cleaned_data['degree_of_disability'],
                cause_of_disability=form.cleaned_data.get('cause_of_disability', ''),
                date_diagnosed=form.cleaned_data.get('date_diagnosed'),
                assistive_devices=form.cleaned_data.get('assistive_devices', ''),
                medication=form.cleaned_data.get('medication', ''),
                philhealth_number=form.cleaned_data.get('philhealth_number', ''),
                sss_gsis_number=form.cleaned_data.get('sss_gsis_number', ''),
                skills_hobbies=form.cleaned_data.get('skills_hobbies', ''),
                organization_membership=form.cleaned_data.get('organization_membership', ''),
                emergency_contact_name=form.cleaned_data['emergency_contact_name'],
                emergency_contact_number=form.cleaned_data['emergency_contact_number'],
                emergency_contact_address=form.cleaned_data['emergency_contact_address'],
                created_by=current_user,
                updated_by=current_user,
            )

            for doc in request.FILES.getlist('documents'):
                save_pwd_document(doc, pwd, current_user)

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
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PWDRegistrationForm()

    return render(request, 'pwd/pwd_create.html', {'form': form})


# -------------------------------
# FINGERPRINT REGISTRATION
# -------------------------------

@csrf_exempt
def register_fingerprint_view(request):
    if request.method == 'POST':
        try:
            success = register_fingerprint()
            return JsonResponse({"success": success})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request"})


# -------------------------------
# LIST, DETAIL, EDIT, TOGGLE STATUS, DELETE DOC
# -------------------------------

def pwd_list_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first.')
        return redirect('accounts:login')

    is_verified = request.session.get('is_verified')
    if not is_verified:
        messages.error(request, 'Account must be verified to view PWDs.')
        return redirect('accounts:profile')

    pwds = PWDProfile.objects.all().order_by('-created_at')

    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        pwds = pwds.filter(
            Q(unique_id__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    # Filters
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
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'disability_filter': disability_filter,
        'degree_filter': degree_filter,
        'total_count': pwds.count(),
    }

    return render(request, 'pwd/pwd_list.html', context)


def pwd_detail_view(request, pwd_id):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first.')
        return redirect('accounts:login')

    is_verified = request.session.get('is_verified')
    if not is_verified:
        messages.error(request, 'Account must be verified.')
        return redirect('accounts:profile')

    try:
        pwd = PWDProfile.objects.get(id=pwd_id)
        documents = pwd.documents.all()
        return render(request, 'pwd/pwd_detail.html', {'pwd': pwd, 'documents': documents})
    except PWDProfile.DoesNotExist:
        messages.error(request, 'PWD not found.')
        return redirect('pwd:pwd_list')


def pwd_edit_view(request, pwd_id):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first.')
        return redirect('accounts:login')

    is_verified = request.session.get('is_verified')
    if not is_verified:
        messages.error(request, 'Account must be verified.')
        return redirect('accounts:profile')

    try:
        current_user = User.objects.get(id=user_id)
        pwd = PWDProfile.objects.get(id=pwd_id)
    except (User.DoesNotExist, PWDProfile.DoesNotExist):
        messages.error(request, 'Record not found.')
        return redirect('pwd:pwd_list')

    if request.method == 'POST':
        form = PWDRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data.get('photo'):
                pwd.photo_path = save_pwd_photo(form.cleaned_data['photo'], pwd.unique_id)

            # update fields
            for field in form.cleaned_data:
                if hasattr(pwd, field):
                    setattr(pwd, field, form.cleaned_data[field])

            pwd.updated_by = current_user
            pwd.save()

            for doc in request.FILES.getlist('documents'):
                save_pwd_document(doc, pwd, current_user)

            AuditLog.log(
                action_type='profile_updated',
                description=f'PWD updated: {pwd.unique_id}',
                user=current_user,
                target_pwd=pwd,
                ip_address=get_client_ip(request)
            )

            messages.success(request, 'PWD profile updated successfully.')
            return redirect('pwd:pwd_detail', pwd_id=pwd.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PWDRegistrationForm(instance=pwd)

    return render(request, 'pwd/pwd_edit.html', {'form': form, 'pwd': pwd})


def pwd_toggle_status_view(request, pwd_id):
    user_id = request.session.get('user_id')
    role = request.session.get('role')
    if not user_id or role != 'admin':
        messages.error(request, 'Access denied.')
        return redirect('accounts:login' if not user_id else 'pwd:pwd_list')

    if request.method == 'POST':
        try:
            current_user = User.objects.get(id=user_id)
            pwd = PWDProfile.objects.get(id=pwd_id)
            pwd.is_active = not pwd.is_active
            pwd.updated_by = current_user
            pwd.save()

            action = 'pwd_reactivated' if pwd.is_active else 'pwd_archived'
            AuditLog.log(
                action_type=action,
                description=f'PWD {"reactivated" if pwd.is_active else "archived"}: {pwd.unique_id}',
                user=current_user,
                target_pwd=pwd,
                ip_address=get_client_ip(request)
            )
            messages.success(request, f'PWD {pwd.unique_id} status updated.')
        except (User.DoesNotExist, PWDProfile.DoesNotExist):
            messages.error(request, 'Record not found.')

    return redirect('pwd:pwd_detail', pwd_id=pwd_id)


def pwd_delete_document_view(request, pwd_id, doc_id):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please login first.')
        return redirect('accounts:login')

    is_verified = request.session.get('is_verified')
    if not is_verified:
        messages.error(request, 'Account must be verified.')
        return redirect('accounts:profile')

    if request.method == 'POST':
        try:
            document = PWDDocument.objects.get(id=doc_id, pwd_profile_id=pwd_id)
            file_path = os.path.join(settings.MEDIA_ROOT, document.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
            document.delete()
            messages.success(request, 'Document deleted successfully.')
        except PWDDocument.DoesNotExist:
            messages.error(request, 'Document not found.')

    return redirect('pwd:pwd_detail', pwd_id=pwd_id)
