"""
Complete pwd/views.py (standalone, full implementation)

Replace your existing pwd/views.py with this file (overwrite) and restart the server.

Features:
- login_view
- profile_view (supports ?unique_id=ID and auto-linking)
- claim_profile_view (POST to link by unique_id)
- fingerprint_poll, next_fingerprint_slot_view, register_fingerprint_view
- dashboard_view
- pwd_create_view (admin create; links profile to creator or a created user)
- pwd_register_and_login_view (self-register)
- pwd_list_view, pwd_detail_view, pwd_edit_view, pwd_toggle_status_view, pwd_delete_document_view

Notes:
- Keep CSRF tokens in templates for POST forms.
- If your project uses a custom User model, this uses get_user_model().
- The file tries to import AuditLog from accounts.models if available (optional).
"""
import json
import os
import time
from datetime import date, datetime
from pathlib import Path

import requests
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import connection, transaction, IntegrityError
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse, NoReverseMatch
from django.utils.crypto import get_random_string
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth import get_user_model, authenticate, login as auth_login
from django.contrib.auth.decorators import login_required

from .models import PWDProfile, PWDDocument
from .forms import PWDRegistrationForm

UserModel = get_user_model()
try:
    from accounts.models import AuditLog
except Exception:
    AuditLog = None

DAEMON_URL = getattr(settings, "FINGERPRINT_DEVICE_URL", "http://127.0.0.1:5001")


# -------------------------------
# Helpers
# -------------------------------
def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _resolve_user(request):
    """
    Return a UserModel instance if possible, or None.
    Resolves from request.user or session keys 'user_id' / '_auth_user_id'.
    """
    u = getattr(request, "user", None)
    try:
        if u and isinstance(u, UserModel):
            return u
    except Exception:
        pass

    uid = request.session.get("user_id") or request.session.get("_auth_user_id")
    if uid:
        try:
            if isinstance(uid, str) and uid.isdigit():
                uid = int(uid)
            return UserModel.objects.filter(pk=uid).first()
        except Exception:
            return None

    # fallback if request.user contains id/username
    if isinstance(u, int):
        return UserModel.objects.filter(pk=u).first()
    if isinstance(u, str):
        if u.isdigit():
            return UserModel.objects.filter(pk=int(u)).first()
        return UserModel.objects.filter(username=u).first()
    return None


def find_next_free_slot(max_slot=200):
    used = set(PWDProfile.objects.exclude(fingerprint_slot__isnull=True).values_list("fingerprint_slot", flat=True))
    for i in range(1, max_slot + 1):
        if i not in used:
            return i
    return None


def save_pwd_photo(file, unique_id):
    if not file:
        return None
    media_root = getattr(settings, "MEDIA_ROOT", None) or (Path(settings.BASE_DIR) / "media")
    photos_dir = Path(media_root) / "pwd_photos"
    photos_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{unique_id}_{get_random_string(6)}_{file.name}"
    dest = photos_dir / safe_name
    with open(dest, "wb") as out:
        for chunk in file.chunks():
            out.write(chunk)
    return os.path.join("pwd_photos", safe_name)


def save_pwd_document(file, pwd, uploaded_by):
    upload_dir = os.path.join(settings.MEDIA_ROOT, "pwd_documents")
    os.makedirs(upload_dir, exist_ok=True)
    timestamp = int(time.time())
    ext = os.path.splitext(file.name)[1]
    filename = f"{pwd.unique_id}_{timestamp}{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb+") as dest:
        for chunk in file.chunks():
            dest.write(chunk)
    PWDDocument.objects.create(
        pwd_profile=pwd,
        file_path=f"pwd_documents/{filename}",
        file_name=file.name,
        file_type=ext.replace(".", ""),
        file_size=file.size,
        uploaded_by=uploaded_by,
    )


def _debug(*args, **kwargs):
    if getattr(settings, "DEBUG", False):
        print("[PWD DEBUG]", *args, **kwargs)


# -------------------------------
# Authentication
# -------------------------------
def login_view(request):
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)
            try:
                request.session["user_id"] = user.id
                request.session["username"] = getattr(user, "username", "")
                request.session["is_verified"] = getattr(user, "is_verified", True)
            except Exception:
                pass
            nxt = request.POST.get("next") or request.GET.get("next")
            if nxt:
                return redirect(nxt)
            try:
                return redirect(reverse("pwd:profile"))
            except NoReverseMatch:
                return redirect(getattr(settings, "LOGIN_REDIRECT_URL", "/"))
        else:
            error = "Invalid username or password."
    return render(request, "pwd/login.html", {"error": error})


# -------------------------------
# Profile and Claim
# -------------------------------
@login_required
def profile_view(request):
    """
    Show a PWD profile. If GET contains unique_id, prefer that profile and auto-link
    to logged-in user when safe. Otherwise show profile linked to current user.
    """
    user = _resolve_user(request)
    unique_id = request.GET.get("unique_id", "").strip() or None

    profile = None
    legacy_profile = None
    documents = []

    # Prefer explicit unique_id when provided
    if unique_id:
        profile = PWDProfile.objects.filter(unique_id=unique_id).first()
        if profile and user and profile.account_id is None:
            try:
                profile.account = user
                if getattr(profile, "created_by_id", None) is None:
                    profile.created_by = user
                profile.updated_by = user
                profile.save()
            except Exception:
                _debug("Auto-link on unique_id failed")

    # Fallback: resolve by user relations/heuristics
    if not profile and user:
        try:
            rel = getattr(user, "pwd_account", None)
            if rel is not None:
                profile = rel.first() if hasattr(rel, "all") else rel
        except Exception:
            profile = None

        if not profile:
            profile = PWDProfile.objects.filter(account_id=user.id).first() or \
                      PWDProfile.objects.filter(created_by_id=user.id).order_by("-created_at").first()

        if not profile:
            try:
                fid = getattr(user, "fingerprint_id", None)
                if fid:
                    profile = PWDProfile.objects.filter(fingerprint_id=fid).first()
            except Exception:
                pass

        if not profile:
            try:
                contact = getattr(user, "contact_number", None)
                if contact:
                    profile = PWDProfile.objects.filter(contact_number=contact).order_by("-created_at").first()
            except Exception:
                pass

        # auto-link if found and not linked
        if profile and getattr(profile, "account_id", None) is None:
            try:
                profile.account = user
                if getattr(profile, "created_by_id", None) is None:
                    profile.created_by = user
                profile.updated_by = user
                profile.save()
            except Exception:
                _debug("Auto-link failed in fallback")

        # legacy fallback: show fields from user model if present
        if not profile:
            possible = [
                "unique_id", "fingerprint_id", "fingerprint_slot", "first_name", "middle_name",
                "last_name", "suffix", "birthdate", "sex", "civil_status", "barangay", "address",
                "contact_number", "religion", "nationality",
            ]
            data = {f: getattr(user, f) for f in possible if hasattr(user, f)}
            if data.get("first_name") or data.get("unique_id") or data.get("fingerprint_id"):
                legacy_profile = data

    if profile:
        documents = list(profile.documents.all())

    # safe urls
    try:
        logout_url = reverse("logout")
    except NoReverseMatch:
        try:
            logout_url = reverse("accounts:logout")
        except NoReverseMatch:
            logout_url = "/accounts/logout/"

    try:
        accounts_login = reverse("accounts:login")
    except NoReverseMatch:
        accounts_login = "/accounts/login/"

    return render(request, "pwd/profile.html", {
        "user": user or request.user,
        "profile": profile,
        "legacy_profile": legacy_profile,
        "documents": documents,
        "logout_url": logout_url,
        "accounts_login_url": accounts_login,
    })


@login_required
@require_POST
def claim_profile_view(request):
    """
    POST -> claim/link a PWDProfile to the logged-in account by unique_id.
    """
    unique_id = request.POST.get("unique_id", "").strip()
    if not unique_id:
        messages.error(request, "Please provide the Unique ID.")
        return redirect("pwd:profile")

    profile = PWDProfile.objects.filter(unique_id=unique_id).first()
    if not profile:
        messages.error(request, "Profile not found.")
        return redirect("pwd:profile")

    user = _resolve_user(request)
    if not user:
        messages.error(request, "Could not resolve your account.")
        return redirect("accounts:login")

    if profile.account_id and profile.account_id != user.id:
        messages.error(request, "This profile is already linked to another account.")
        return redirect("pwd:profile")

    try:
        profile.account = user
        if getattr(profile, "created_by_id", None) is None:
            profile.created_by = user
        profile.updated_by = user
        profile.save()
        messages.success(request, "Profile successfully linked to your account.")
    except Exception as exc:
        messages.error(request, f"Failed to link profile: {exc}")

    return redirect("pwd:profile")


# -------------------------------
# Fingerprint endpoints
# -------------------------------
@require_GET
def fingerprint_poll(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, user_id, fingerprint_id
            FROM fingerprint_events
            WHERE processed = FALSE
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        if not row:
            return JsonResponse({"status": "waiting"})

        event_id, user_id, fingerprint_id = row
        cursor.execute("UPDATE fingerprint_events SET processed = TRUE WHERE id = %s", [event_id])

    if user_id:
        try:
            user = UserModel.objects.get(pk=user_id)
            auth_login(request, user)
            try:
                request.session["user_id"] = user.id
                request.session["username"] = getattr(user, "username", "")
                request.session["is_verified"] = getattr(user, "is_verified", True)
            except Exception:
                pass
            next_url = request.GET.get("next") or getattr(settings, "LOGIN_REDIRECT_URL", "/") or "/pwd/profile/"
            return JsonResponse({"status": "found", "user_redirect": next_url})
        except UserModel.DoesNotExist:
            return JsonResponse({"status": "found", "message": "User linked to fingerprint not found."})
    return JsonResponse({"status": "found", "fingerprint_id": fingerprint_id})


@require_POST
def next_fingerprint_slot_view(request):
    used = set(PWDProfile.objects.exclude(fingerprint_slot__isnull=True).values_list("fingerprint_slot", flat=True))
    for i in range(1, 201):
        if i not in used:
            return JsonResponse({"slot": i})
    return JsonResponse({"error": "no_free_slots"}, status=400)


@require_POST
def register_fingerprint_view(request):
    try:
        body = {}
        try:
            body = json.loads(request.body.decode() or "{}")
        except Exception:
            body = {}
        resp = requests.post(f"{DAEMON_URL.rstrip('/')}/enroll_start", json=body, timeout=10)
        try:
            return JsonResponse(resp.json(), status=resp.status_code)
        except ValueError:
            return JsonResponse({"error": "invalid_daemon_response", "raw": resp.text}, status=502)
    except requests.exceptions.RequestException as e:
        return JsonResponse({"error": f"daemon_unreachable:{e}"}, status=502)


# -------------------------------
# Dashboard & CRUD views
# -------------------------------
def dashboard_view(request):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or str(role).lower() != "admin":
        messages.error(request, "Access denied.")
        return redirect("accounts:login" if not user_id else "accounts:profile")

    total_pwd = PWDProfile.objects.count()
    active_pwd = PWDProfile.objects.filter(is_active=True).count()
    inactive_pwd = total_pwd - active_pwd
    male_pwd = PWDProfile.objects.filter(sex="M", is_active=True).count()
    female_pwd = PWDProfile.objects.filter(sex="F", is_active=True).count()

    low_degree = PWDProfile.objects.filter(degree_of_disability="Low", is_active=True).count()
    moderate_degree = PWDProfile.objects.filter(degree_of_disability="Moderate", is_active=True).count()
    high_degree = PWDProfile.objects.filter(degree_of_disability="High", is_active=True).count()

    disability_stats = PWDProfile.objects.filter(is_active=True).values("disability_type").annotate(
        count=Count("id")
    ).order_by("-count")
    employment_stats = PWDProfile.objects.filter(is_active=True).values("employment_status").annotate(
        count=Count("id")
    ).order_by("-count")

    today = date.today()

    def _get_age(birthdate):
        age = today.year - birthdate.year
        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age -= 1
        return age

    age_groups = {"0_17": 0, "18_30": 0, "31_59": 0, "60_plus": 0}
    for pwd in PWDProfile.objects.filter(is_active=True):
        try:
            age = _get_age(pwd.birthdate)
        except Exception:
            continue
        if age <= 17:
            age_groups["0_17"] += 1
        elif age <= 30:
            age_groups["18_30"] += 1
        elif age <= 59:
            age_groups["31_59"] += 1
        else:
            age_groups["60_plus"] += 1

    total_users = UserModel.objects.count()
    verified_users = UserModel.objects.filter(is_verified=True).count() if hasattr(UserModel, "is_verified") else 0
    active_users = UserModel.objects.filter(is_active=True).count()
    admin_users = UserModel.objects.filter(role="admin").count() if hasattr(UserModel, "role") else 0
    basic_users = UserModel.objects.filter(role="basic_user").count() if hasattr(UserModel, "role") else 0

    recent_logs = AuditLog.objects.all().order_by("-timestamp")[:10] if AuditLog else []

    context = {
        "username": request.session.get("username"),
        "total_pwd": total_pwd,
        "active_pwd": active_pwd,
        "inactive_pwd": inactive_pwd,
        "male_pwd": male_pwd,
        "female_pwd": female_pwd,
        "low_degree": low_degree,
        "moderate_degree": moderate_degree,
        "high_degree": high_degree,
        "disability_stats": disability_stats,
        "employment_stats": employment_stats,
        **age_groups,
        "total_users": total_users,
        "verified_users": verified_users,
        "active_users": active_users,
        "admin_users": admin_users,
        "basic_users": basic_users,
        "recent_logs": recent_logs,
    }
    return render(request, "pwd/dashboard.html", context)


def pwd_create_view(request):
    user = _resolve_user(request)
    if not user:
        messages.error(request, "Please login first.")
        return redirect("accounts:login")
    if not request.session.get("is_verified"):
        messages.error(request, "Account must be verified to register PWDs.")
        return redirect("accounts:profile")

    if request.method == "POST":
        form = PWDRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            slot_val = form.cleaned_data.get("fingerprint_slot")
            requested_slot = None
            try:
                requested_slot = int(slot_val) if slot_val else None
            except Exception:
                requested_slot = None
            if requested_slot is not None and PWDProfile.objects.filter(fingerprint_slot=requested_slot).exists():
                next_slot = find_next_free_slot()
                form.add_error("fingerprint_slot", f"Slot {requested_slot} is already used. Next free: {next_slot or 'none'}")
                messages.error(request, "Fingerprint slot already used. Choose another.")
                return render(request, "pwd/pwd_create.html", {"form": form})

            slot_to_use = requested_slot if requested_slot is not None else find_next_free_slot()
            unique_id = PWDProfile.generate_unique_id()
            photo_path = save_pwd_photo(form.cleaned_data.get("photo"), unique_id) if form.cleaned_data.get("photo") else None

            try:
                with transaction.atomic():
                    pwd = PWDProfile.objects.create(
                        unique_id=unique_id,
                        first_name=form.cleaned_data.get("first_name"),
                        middle_name=form.cleaned_data.get("middle_name", ""),
                        last_name=form.cleaned_data.get("last_name"),
                        suffix=form.cleaned_data.get("suffix", ""),
                        birthdate=form.cleaned_data.get("birthdate"),
                        sex=form.cleaned_data.get("sex"),
                        civil_status=form.cleaned_data.get("civil_status"),
                        barangay=form.cleaned_data.get("barangay"),
                        address=form.cleaned_data.get("address"),
                        contact_number=form.cleaned_data.get("contact_number"),
                        religion=form.cleaned_data.get("religion"),
                        nationality=form.cleaned_data.get("nationality", "Filipino"),
                        photo_path=photo_path,
                        educational_attainment=form.cleaned_data.get("educational_attainment"),
                        employment_status=form.cleaned_data.get("employment_status"),
                        occupation=form.cleaned_data.get("occupation", ""),
                        type_of_employment=form.cleaned_data.get("type_of_employment", ""),
                        household_income=form.cleaned_data.get("household_income"),
                        household_size=form.cleaned_data.get("household_size"),
                        living_situation=form.cleaned_data.get("living_situation", ""),
                        housing_type=form.cleaned_data.get("housing_type", ""),
                        guardian_name=form.cleaned_data.get("guardian_name"),
                        guardian_contact=form.cleaned_data.get("guardian_contact"),
                        disability_type=form.cleaned_data.get("disability_type"),
                        degree_of_disability=form.cleaned_data.get("degree_of_disability"),
                        cause_of_disability=form.cleaned_data.get("cause_of_disability", ""),
                        date_diagnosed=form.cleaned_data.get("date_diagnosed"),
                        assistive_devices=form.cleaned_data.get("assistive_devices", ""),
                        medication=form.cleaned_data.get("medication", ""),
                        philhealth_number=form.cleaned_data.get("philhealth_number", ""),
                        sss_gsis_number=form.cleaned_data.get("sss_gsis_number", ""),
                        skills_hobbies=form.cleaned_data.get("skills_hobbies", ""),
                        organization_membership=form.cleaned_data.get("organization_membership", ""),
                        emergency_contact_name=form.cleaned_data.get("emergency_contact_name"),
                        emergency_contact_number=form.cleaned_data.get("emergency_contact_number"),
                        emergency_contact_address=form.cleaned_data.get("emergency_contact_address"),
                        created_by=user,
                        updated_by=user,
                        fingerprint_slot=slot_to_use,
                    )

                    for doc in request.FILES.getlist("documents"):
                        save_pwd_document(doc, pwd, user)

                    if form.cleaned_data.get("create_account"):
                        username = form.cleaned_data.get("account_username")
                        password = form.cleaned_data.get("account_password1")
                        if username and not UserModel.objects.filter(username=username).exists():
                            if hasattr(UserModel.objects, "create_user"):
                                created_user = UserModel.objects.create_user(username=username, password=password)
                            else:
                                created_user = UserModel(username=username)
                                created_user.set_password(password)
                                created_user.save()
                            try:
                                if hasattr(created_user, "first_name"):
                                    created_user.first_name = pwd.first_name[:30]
                                    created_user.last_name = pwd.last_name[:30]
                                    if hasattr(created_user, "contact_number"):
                                        created_user.contact_number = pwd.contact_number or ""
                                    if hasattr(created_user, "is_verified"):
                                        created_user.is_verified = True
                                    created_user.save()
                            except Exception:
                                pass
                            if hasattr(pwd, "account"):
                                pwd.account = created_user
                                pwd.save()
                        else:
                            try:
                                if hasattr(pwd, "account"):
                                    pwd.account = user
                                    pwd.save()
                            except Exception:
                                _debug("Could not link to creator")
                    else:
                        try:
                            if hasattr(pwd, "account"):
                                pwd.account = user
                                pwd.save()
                        except Exception:
                            _debug("Could not link to creator")

                    if AuditLog:
                        try:
                            AuditLog.log(
                                action_type="user_registered",
                                description=f"PWD registered: {pwd.unique_id} - {pwd.get_full_name()}",
                                user=user,
                                target_pwd=pwd,
                                ip_address=get_client_ip(request),
                            )
                        except Exception:
                            pass

                    messages.success(request, f"PWD registered successfully! ID: {unique_id} (slot: {slot_to_use})")
                    return redirect("pwd:pwd_detail", pwd_id=pwd.id)

            except IntegrityError:
                transaction.set_rollback(True)
                messages.error(request, "Failed to save PWD: fingerprint slot conflict or DB error.")
                form.add_error("fingerprint_slot", "Slot conflict — choose another.")
                return render(request, "pwd/pwd_create.html", {"form": form})
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PWDRegistrationForm()
    return render(request, "pwd/pwd_create.html", {"form": form})


def pwd_register_and_login_view(request):
    if request.user.is_authenticated:
        return redirect("pwd:profile")

    if request.method == "POST":
        form = PWDRegistrationForm(request.POST, request.FILES)
        account_username = request.POST.get("account_username", "").strip()
        account_password = request.POST.get("account_password1", "")
        if not account_username or not account_password:
            messages.error(request, "Please supply account username and password to register.")
            return render(request, "pwd/pwd_create.html", {"form": form})

        if form.is_valid():
            try:
                with transaction.atomic():
                    unique_id = PWDProfile.generate_unique_id()
                    photo_path = save_pwd_photo(form.cleaned_data.get("photo"), unique_id) if form.cleaned_data.get("photo") else None

                    requested_slot = None
                    slot_val = form.cleaned_data.get("fingerprint_slot")
                    try:
                        requested_slot = int(slot_val) if slot_val else None
                    except Exception:
                        requested_slot = None
                    if requested_slot and PWDProfile.objects.filter(fingerprint_slot=requested_slot).exists():
                        slot_to_use = find_next_free_slot()
                    else:
                        slot_to_use = requested_slot if requested_slot is not None else find_next_free_slot()

                    if UserModel.objects.filter(username=account_username).exists():
                        messages.error(request, "Username already exists. Choose another username.")
                        return render(request, "pwd/pwd_create.html", {"form": form})

                    if hasattr(UserModel.objects, "create_user"):
                        new_user = UserModel.objects.create_user(username=account_username, password=account_password)
                    else:
                        new_user = UserModel(username=account_username)
                        new_user.set_password(account_password)
                        new_user.save()

                    try:
                        if hasattr(new_user, "first_name"):
                            new_user.first_name = form.cleaned_data.get("first_name", "")[:30]
                            new_user.last_name = form.cleaned_data.get("last_name", "")[:30]
                        if hasattr(new_user, "contact_number"):
                            new_user.contact_number = form.cleaned_data.get("contact_number", "")[:20]
                        if hasattr(new_user, "is_verified"):
                            new_user.is_verified = True
                        new_user.save()
                    except Exception:
                        pass

                    try:
                        pwd = PWDProfile.objects.create(
                            unique_id=unique_id,
                            first_name=form.cleaned_data.get("first_name"),
                            middle_name=form.cleaned_data.get("middle_name", ""),
                            last_name=form.cleaned_data.get("last_name"),
                            suffix=form.cleaned_data.get("suffix", ""),
                            birthdate=form.cleaned_data.get("birthdate"),
                            sex=form.cleaned_data.get("sex"),
                            civil_status=form.cleaned_data.get("civil_status"),
                            barangay=form.cleaned_data.get("barangay"),
                            address=form.cleaned_data.get("address"),
                            contact_number=form.cleaned_data.get("contact_number"),
                            religion=form.cleaned_data.get("religion"),
                            nationality=form.cleaned_data.get("nationality", "Filipino"),
                            photo_path=photo_path,
                            created_by=new_user,
                            updated_by=new_user,
                            fingerprint_slot=slot_to_use,
                        )
                    except IntegrityError:
                        retry_slot = find_next_free_slot()
                        if retry_slot is None:
                            raise
                        pwd = PWDProfile.objects.create(
                            unique_id=unique_id,
                            first_name=form.cleaned_data.get("first_name"),
                            middle_name=form.cleaned_data.get("middle_name", ""),
                            last_name=form.cleaned_data.get("last_name"),
                            suffix=form.cleaned_data.get("suffix", ""),
                            birthdate=form.cleaned_data.get("birthdate"),
                            sex=form.cleaned_data.get("sex"),
                            civil_status=form.cleaned_data.get("civil_status"),
                            barangay=form.cleaned_data.get("barangay"),
                            address=form.cleaned_data.get("address"),
                            contact_number=form.cleaned_data.get("contact_number"),
                            religion=form.cleaned_data.get("religion"),
                            nationality=form.cleaned_data.get("nationality", "Filipino"),
                            photo_path=photo_path,
                            created_by=new_user,
                            updated_by=new_user,
                            fingerprint_slot=retry_slot,
                        )

                    if hasattr(pwd, "account"):
                        pwd.account = new_user
                        pwd.save()

                    for doc in request.FILES.getlist("documents"):
                        save_pwd_document(doc, pwd, new_user)

                    if AuditLog:
                        try:
                            AuditLog.log(
                                action_type="user_self_registered",
                                description=f"PWD self-registered: {pwd.unique_id} - {pwd.get_full_name()}",
                                user=new_user,
                                target_pwd=pwd,
                                ip_address=get_client_ip(request),
                            )
                        except Exception:
                            pass

                    user = authenticate(request, username=account_username, password=account_password)
                    if user:
                        auth_login(request, user)
                    else:
                        try:
                            auth_login(request, new_user)
                        except Exception:
                            pass

                    try:
                        request.session["user_id"] = new_user.id
                        request.session["username"] = getattr(new_user, "username", "")
                        request.session["is_verified"] = getattr(new_user, "is_verified", True)
                    except Exception:
                        pass

                    messages.success(request, "Registration successful. You are now logged in.")
                    return redirect("pwd:profile")

            except Exception as exc:
                transaction.set_rollback(True)
                messages.error(request, f"Registration failed: {exc}")
                return render(request, "pwd/pwd_create.html", {"form": form})
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PWDRegistrationForm()
    return render(request, "pwd/pwd_create.html", {"form": form})


def pwd_list_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please login first.")
        return redirect("accounts:login")
    if not request.session.get("is_verified"):
        messages.error(request, "Account must be verified to view PWDs.")
        return redirect("accounts:profile")

    pwds = PWDProfile.objects.all().order_by("-created_at")
    search_query = request.GET.get("search", "")
    if search_query:
        pwds = pwds.filter(
            Q(unique_id__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    status_filter = request.GET.get("status", "")
    if status_filter == "active":
        pwds = pwds.filter(is_active=True)
    elif status_filter == "inactive":
        pwds = pwds.filter(is_active=False)

    disability_filter = request.GET.get("disability", "")
    if disability_filter:
        pwds = pwds.filter(disability_type=disability_filter)

    degree_filter = request.GET.get("degree", "")
    if degree_filter:
        pwds = pwds.filter(degree_of_disability=degree_filter)

    paginator = Paginator(pwds, 20)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "disability_filter": disability_filter,
        "degree_filter": degree_filter,
        "total_count": pwds.count(),
    }

    return render(request, "pwd/pwd_list.html", context)


def pwd_detail_view(request, pwd_id):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please login first.")
        return redirect("accounts:login")
    if not request.session.get("is_verified"):
        messages.error(request, "Account must be verified.")
        return redirect("accounts:profile")

    try:
        pwd = PWDProfile.objects.get(id=pwd_id)
        documents = pwd.documents.all()
        return render(request, "pwd/pwd_detail.html", {"pwd": pwd, "documents": documents})
    except PWDProfile.DoesNotExist:
        messages.error(request, "PWD not found.")
        return redirect("pwd:pwd_list")


def pwd_edit_view(request, pwd_id):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please login first.")
        return redirect("accounts:login")
    if not request.session.get("is_verified"):
        messages.error(request, "Account must be verified.")
        return redirect("accounts:profile")

    try:
        current_user = UserModel.objects.get(id=user_id)
        pwd = PWDProfile.objects.get(id=pwd_id)
    except (UserModel.DoesNotExist, PWDProfile.DoesNotExist):
        messages.error(request, "Record not found.")
        return redirect("pwd:pwd_list")

    if request.method == "POST":
        form = PWDRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            if form.cleaned_data.get("photo"):
                pwd.photo_path = save_pwd_photo(form.cleaned_data["photo"], pwd.unique_id)
            for key, value in form.cleaned_data.items():
                if hasattr(pwd, key) and key not in ("unique_id", "created_by", "created_at", "updated_at"):
                    setattr(pwd, key, value)
            pwd.updated_by = current_user
            pwd.save()
            for doc in request.FILES.getlist("documents"):
                save_pwd_document(doc, pwd, current_user)
            if AuditLog:
                try:
                    AuditLog.log(
                        action_type="profile_updated",
                        description=f"PWD updated: {pwd.unique_id}",
                        user=current_user,
                        target_pwd=pwd,
                        ip_address=get_client_ip(request),
                    )
                except Exception:
                    pass
            messages.success(request, "PWD profile updated successfully.")
            return redirect("pwd:pwd_detail", pwd_id=pwd.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        initial = {
            "first_name": pwd.first_name,
            "middle_name": pwd.middle_name,
            "last_name": pwd.last_name,
            "suffix": pwd.suffix,
            "birthdate": pwd.birthdate,
            "sex": pwd.sex,
            "civil_status": pwd.civil_status,
            "barangay": pwd.barangay,
            "address": pwd.address,
            "contact_number": pwd.contact_number,
            "religion": pwd.religion,
            "nationality": pwd.nationality,
            "educational_attainment": pwd.educational_attainment,
            "employment_status": pwd.employment_status,
            "occupation": pwd.occupation,
            "type_of_employment": pwd.type_of_employment,
            "household_income": pwd.household_income,
            "household_size": pwd.household_size,
            "living_situation": pwd.living_situation,
            "housing_type": pwd.housing_type,
            "guardian_name": pwd.guardian_name,
            "guardian_contact": pwd.guardian_contact,
            "disability_type": pwd.disability_type,
            "degree_of_disability": pwd.degree_of_disability,
            "cause_of_disability": pwd.cause_of_disability,
            "date_diagnosed": pwd.date_diagnosed,
            "assistive_devices": pwd.assistive_devices,
            "medication": pwd.medication,
            "philhealth_number": pwd.philhealth_number,
            "sss_gsis_number": pwd.sss_gsis_number,
            "skills_hobbies": pwd.skills_hobbies,
            "organization_membership": pwd.organization_membership,
            "emergency_contact_name": pwd.emergency_contact_name,
            "emergency_contact_number": pwd.emergency_contact_number,
            "emergency_contact_address": pwd.emergency_contact_address,
            "fingerprint_slot": pwd.fingerprint_slot,
        }
        form = PWDRegistrationForm(initial=initial)
    return render(request, "pwd/pwd_edit.html", {"form": form, "pwd": pwd})


def pwd_toggle_status_view(request, pwd_id):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "admin":
        messages.error(request, "Access denied.")
        return redirect("accounts:login" if not user_id else "pwd:pwd_list")

    if request.method == "POST":
        try:
            current_user = UserModel.objects.get(id=user_id)
            pwd = PWDProfile.objects.get(id=pwd_id)
            pwd.is_active = not pwd.is_active
            pwd.updated_by = current_user
            pwd.save()
            if AuditLog:
                try:
                    AuditLog.log(
                        action_type="pwd_reactivated" if pwd.is_active else "pwd_archived",
                        description=f"PWD {'reactivated' if pwd.is_active else 'archived'}: {pwd.unique_id}",
                        user=current_user,
                        target_pwd=pwd,
                        ip_address=get_client_ip(request),
                    )
                except Exception:
                    pass
            messages.success(request, f"PWD {pwd.unique_id} status updated.")
        except (UserModel.DoesNotExist, PWDProfile.DoesNotExist):
            messages.error(request, "Record not found.")
    return redirect("pwd:pwd_detail", pwd_id=pwd_id)


def pwd_delete_document_view(request, pwd_id, doc_id):
    user_id = request.session.get("user_id")
    if not user_id:
        messages.error(request, "Please login first.")
        return redirect("accounts:login")
    if not request.session.get("is_verified"):
        messages.error(request, "Account must be verified to perform this action.")
        return redirect("accounts:profile")

    if request.method == "POST":
        try:
            document = PWDDocument.objects.get(id=doc_id, pwd_profile_id=pwd_id)
            file_path = os.path.join(settings.MEDIA_ROOT, document.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)
            document.delete()
            messages.success(request, "Document deleted successfully.")
        except PWDDocument.DoesNotExist:
            messages.error(request, "Document not found.")
    return redirect("pwd:pwd_detail", pwd_id=pwd_id)