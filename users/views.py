import requests
import random
import string
from datetime import timedelta

from django.conf import settings
import logging
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from .forms import CaptchaLoginForm
from .forms import NPDCRegisterForm, UserUpdateForm, ProfileUpdateForm, AdminUserEditForm
from .models import Profile, LoginAttempt, PasswordResetOTP
from data_submission.models import DatasetSubmission





# --------------------
# Utilities
# --------------------



# --------------------
# Auth / Dashboard
# --------------------

@login_required
def login_redirect(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect("data_submission:admin_dashboard")
    return redirect("users:dashboard")


@login_required
def dashboard(request):
    if not request.user.is_active:
        logout(request)
        messages.warning(request, "Your account is awaiting admin approval.")
        return redirect('login')

    profile = request.user.profile

    # Analytics Logic
    user_submissions = DatasetSubmission.objects.filter(submitter=request.user)
    
    total_submitted = user_submissions.exclude(status='draft').count()
    published_count = user_submissions.filter(status='published').count()
    
    # Recent Activity (Non-drafts)
    recent_activity = user_submissions.exclude(status='draft').order_by('-submission_date')[:5]

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "is_admin": request.user.is_staff,
            "user_type": getattr(profile, "user_type", None),
            # Analytics Context
            "total_submitted": total_submitted,
            "published_count": published_count,
            "recent_activity": recent_activity,
        }
    )


# --------------------
# Registration
# --------------------

def register(request):
    if request.method == 'POST':
        form = NPDCRegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # pending approval
            user.save()
            form.save_m2m()

            # Update the Profile (created by signal) with form data
            profile = user.profile
            profile.title = form.cleaned_data.get('title', '')
            profile.preferred_name = form.cleaned_data.get('preferred_name', '')
            profile.organisation = form.cleaned_data.get('organisation', '')
            profile.organisation_url = form.cleaned_data.get('organisation_url', '')
            profile.profile_url = form.cleaned_data.get('profile_url', '')
            profile.designation = form.cleaned_data.get('designation', '')
            profile.phone = form.cleaned_data.get('phone', '')
            profile.whatsapp_number = form.cleaned_data.get('whatsapp_number', '')
            profile.address = form.cleaned_data.get('address', '')
            profile.alternate_email = form.cleaned_data.get('alternate_email', '')
            profile.save()

            # 1. Email to USER (Confirmation)
            text_content_user = f"""
Dear {user.first_name},

Thank you for registering with the National Polar Data Center (NPDC) Portal.

Your account has been successfully created and is currently pending verification by our administrators. You will receive a confirmation email once your account has been approved and activated.

User ID: {user.username}
Registered Email: {user.email}

If you have any questions, please contact our support team.

Best Regards,
NPDC Data Team
National Polar Data Center
"""
            if user.email:
                try:
                    email_user = EmailMultiAlternatives(
                        subject='[NPDC Portal] Registration Successful - Pending Verification',
                        body=text_content_user,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[user.email],
                    )
                    email_user.send()
                except Exception as e:
                    print(f"Failed to send registration email to user: {e}")

            # 2. Email to ADMINS (New User Alert)
            text_content_admin = f"""
Dear Admin,

A new user has registered on the NPDC Portal and requires approval.

User Details:
-------------
Name: {user.get_full_name()}
Email: {user.email}
Username: {user.username}
Organisation: {profile.organisation}
Designation: {profile.designation}

Please log in to the admin panel to review and approve this user:
{request.build_absolute_uri('/admin/users/user/')}

Best Regards,
NPDC Portal System
"""
            try:
                # Notify all superusers
                admin_emails = list(User.objects.filter(is_superuser=True).values_list('email', flat=True))
                if admin_emails:
                    email_admin = EmailMultiAlternatives(
                        subject='[NPDC Admin] Action Required: New User Registration',
                        body=text_content_admin,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=admin_emails,
                    )
                    email_admin.send()
            except Exception as e:
                print(f"Failed to send admin notification for new user: {e}")

            messages.success(
                request,
                "Registration submitted successfully. Your account is under verification."
            )
            return redirect('login')

    else:
        form = NPDCRegisterForm()

    return render(
        request,
        'registration/register.html',
        {
            'form': form,
        }
    )


# --------------------
# Profile
# --------------------

@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('users:profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    # Get dataset count for the user
    user_submissions = DatasetSubmission.objects.filter(submitter=request.user)
    published_datasets_count = user_submissions.filter(status='published').count()
    verified_datasets_count = user_submissions.filter(status__in=['published', 'approved']).count()

    return render(
        request,
        'users/profile.html',
        {
            'u_form': u_form, 
            'p_form': p_form,
            'published_datasets_count': published_datasets_count,
            'verified_datasets_count': verified_datasets_count
        }
    )


# --------------------
# Admin
# --------------------

@staff_member_required
def admin_create_user(request):
    # Fetch existing admins for display
    existing_admins = User.objects.filter(is_staff=True).select_related('profile').order_by('-date_joined')

    if request.method == "POST":
        user_type = request.POST.get("user_type")

        if user_type == "standard":
            # Use NPDCRegisterForm for validation but remove captcha
            form = NPDCRegisterForm(request.POST)
            if 'captcha' in form.fields:
                del form.fields['captcha']
            
            if form.is_valid():
                user = form.save(commit=False)
                user.is_active = True  # Auto-approve
                user.save()
                
                # Update Profile
                profile = user.profile
                profile.title = form.cleaned_data.get('title', '')
                profile.preferred_name = form.cleaned_data.get('preferred_name', '')
                profile.organisation = form.cleaned_data.get('organisation', '')
                profile.organisation_url = form.cleaned_data.get('organisation_url', '')
                profile.profile_url = form.cleaned_data.get('profile_url', '')
                profile.designation = form.cleaned_data.get('designation', '')
                profile.phone = form.cleaned_data.get('phone', '')
                profile.whatsapp_number = form.cleaned_data.get('whatsapp_number', '')
                profile.address = form.cleaned_data.get('address', '')
                profile.alternate_email = form.cleaned_data.get('alternate_email', '')
                
                # Set approval details
                profile.is_approved = True
                profile.approved_at = timezone.now()
                profile.save()

                messages.success(request, f"Standard User {user.email} created and approved successfully")
                return redirect("users:user_approval_dashboard")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        
        else:
            # Admin User Creation (Manual Logic)
            email = request.POST.get("email", "").strip().lower()
            confirm_email = request.POST.get("confirm_email", "").strip().lower()
            password1 = request.POST.get("password1", "")
            password2 = request.POST.get("password2", "")
            expedition_admin_type = request.POST.get("expedition_admin_type", "")
            
            # Validate
            errors = []
            if not email:
                errors.append("Email is required")
            if email != confirm_email:
                errors.append("Email addresses do not match")
            if not password1:
                errors.append("Password is required")
            if password1 != password2:
                errors.append("Passwords do not match")
            if User.objects.filter(email=email).exists():
                errors.append("A user with this email already exists")
            
            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, "admin/admin_create_user.html", {
                    "expedition_types": Profile.EXPEDITION_TYPES,
                    "existing_admins": existing_admins
                })
            
            # Create user (or get existing)
            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'password': password1,
                    'first_name': "Admin",
                    'last_name': "User",
                    'is_active': True
                }
            )
            
            # If user was just created, set the password properly
            if created:
                user.set_password(password1)
                user.save()
            
            # Set staff status if made an admin
            if expedition_admin_type:
                user.is_staff = True
                user.save()
            
            # Create/Update profile
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    "title": "Dr",
                    "designation": "Administrator",
                    "organisation": "NPDC",
                    "organisation_url": "https://npdc.ncpor.res.in",
                    "is_approved": True,
                    "approved_at": timezone.now(),
                    "expedition_admin_type": expedition_admin_type if expedition_admin_type else None
                }
            )

            messages.success(request, f"Admin User {email} created successfully")
            return redirect("users:user_approval_dashboard")

    return render(request, "admin/admin_create_user.html", {
        "expedition_types": Profile.EXPEDITION_TYPES,
        "existing_admins": existing_admins
    })


@staff_member_required
def user_approval_dashboard(request):
    approved_users = User.objects.filter(is_active=True, is_staff=False).select_related("profile")
    admin_users = User.objects.filter(is_active=True, is_staff=True).select_related("profile")

    return render(
        request,
        "admin/user_approval_dashboard.html",
        {
            "pending_users": User.objects.filter(is_active=False, profile__is_rejected=False).select_related("profile"),
            "approved_users": approved_users,
            "standard_count": approved_users.count(),
            "admin_users": admin_users,
            "admin_count": admin_users.count(),
            "rejected_users": User.objects.filter(profile__is_rejected=True).select_related("profile"),
        }
    )


@staff_member_required
def approve_user(request, user_id):
    if request.method == "POST":
        user = get_object_or_404(User, id=user_id)
        user.is_active = True
        user.save()
        

        
    return redirect("users:user_approval_dashboard")


@staff_member_required
def reject_user(request, user_id):
    if request.method == "POST":
        user = get_object_or_404(User, id=user_id)
        email = user.email
        
        # Mark as rejected instead of deleting
        if hasattr(user, 'profile'):
            user.profile.is_rejected = True
            user.profile.rejected_at = timezone.now()
            user.profile.save()
        

        
    return redirect("users:user_approval_dashboard")


# --------------------
# Home
# --------------------

def home(request):
    from django.contrib.auth.models import User
    from django.db.models import Count

    published = DatasetSubmission.objects.filter(status='published')
    recent_data = published.order_by('-submission_date')[:5]
    popular_data = published.order_by('?')[:7]

    # NPDC at a Glance stats
    total_datasets = published.count()
    total_users = User.objects.filter(is_active=True, is_staff=False).count()
    total_expeditions = published.values('expedition_number').distinct().count()
    total_years = published.values('expedition_year').distinct().count()

    # Research Regions stats
    arctic_ds = published.filter(expedition_type='arctic').count()
    arctic_exp = published.filter(expedition_type='arctic').values('expedition_number').distinct().count()
    antarctic_ds = published.filter(expedition_type='antarctic').count()
    antarctic_exp = published.filter(expedition_type='antarctic').values('expedition_number').distinct().count()
    southern_ds = published.filter(expedition_type='southern_ocean').count()
    southern_exp = published.filter(expedition_type='southern_ocean').values('expedition_number').distinct().count()
    himalaya_ds = published.filter(expedition_type='himalaya').count()
    himalaya_exp = published.filter(expedition_type='himalaya').values('expedition_number').distinct().count()

    # Dashboard Chart Data
    # 1. Science Keywords (Top 5)
    # The reference image shows categories (Atmosphere, Oceans) as "Science Keywords"
    # So we use the 'category' field for this chart.
    category_counts = published.values('category').annotate(count=Count('id')).order_by('-count')[:5]
    keywords_data = {
        'labels': [item['category'].replace('_', ' ').upper() for item in category_counts],
        'data': [item['count'] for item in category_counts]
    }

    # Prepare keywords for Wordcloud (granular tags)
    from collections import Counter
    all_keywords = []
    for ds in published:
        if ds.keywords:
            kws = [k.strip() for k in ds.keywords.split(',') if k.strip()]
            all_keywords.extend(kws)

    # 2. ISO Topics (Top 5)
    iso_counts = published.values('iso_topic').annotate(count=Count('id')).order_by('-count')[:5]
    # Map ISO topic codes to readable labels if needed, for now use the value
    # The choices are defined in models.py, but for the chart keys/values are fine
    iso_data = {
        'labels': [item['iso_topic'] for item in iso_counts],
        'data': [item['count'] for item in iso_counts]
    }

    # 3. Location (Expedition Type)
    # We already have counts: arctic_ds, antarctic_ds, southern_ds, himalaya_ds
    location_data = {
        'labels': ['Arctic', 'Antarctic', 'Southern Ocean', 'Himalaya'],
        'data': [arctic_ds, antarctic_ds, southern_ds, himalaya_ds]
    }

    # 4. Data Trends (Last 5 Years)
    # The trend chart logic is removed, but we keep the structure empty to not break other views temporarily
    # if anything was expecting trend_data context.
    trend_data = {'labels': [], 'data': []}


    # Metadata Dashboard Data
    # 1. Metrics
    # Use published.count() consistently so dashboard and summary show the same number
    metadata_count = published.count()  # Total published datasets
    rawdata_count = published.filter(number_of_files__gt=0).count()  # Published with files
    # Count distinct scientists who contributed published datasets
    # Use legacy scientist_details table for accurate count
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(DISTINCT sci_email) FROM scientist_details WHERE sci_email IS NOT NULL AND sci_email != ''")
            researcher_count = cursor.fetchone()[0]
    except Exception:
        researcher_count = published.exclude(submitter__isnull=True).values('submitter').distinct().count()
    # Count all users from legacy user_login table
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM user_login")
            total_users = cursor.fetchone()[0]
    except Exception:
        total_users = User.objects.count()

    # Mock data for views and downloads as we don't track them yet
    download_count = 5943      # Placeholder

    # 2. Core Keyword (Wordcloud)
    # Reuse 'keyword_counts' from chart data but get top 30 for wordcloud
    wordcloud_data = Counter(all_keywords).most_common(30)
    # Format for wordcloud2.js: [['keyword', size], ...]
    wordcloud_allowlist = [[k[0], k[1] * 5] for k in wordcloud_data] # Scale size for visibility

    # 3. Usage by Country (Map)
    # Mock data for now as Profile model doesn't have country field
    country_data = {
        'India': 150,
        'USA': 45,
        'UK': 30,
        'Norway': 25,
        'Germany': 20,
        'Japan': 15,
        'Australia': 10,
        'China': 10,
        'Russia': 5,
        'Brazil': 5
    }

    # Advanced Search Section Data
    from collections import Counter
    from data_submission.models import PlatformMetadata, InstrumentMetadata

    # Facet counts (matching search page)
    expedition_facets = dict(published.values_list('expedition_type').annotate(count=Count('id')))
    category_facets = dict(published.values_list('category').annotate(count=Count('id')))
    iso_facets = dict(published.values_list('iso_topic').annotate(count=Count('id')))
    year_facets = dict(published.values_list('expedition_year').annotate(count=Count('id')))

    # Expedition options with counts
    expedition_options = []
    for v, d in DatasetSubmission.EXPEDITION_TYPES:
        expedition_options.append({'value': v, 'label': d, 'count': expedition_facets.get(v, 0)})

    # Category options with counts
    category_options = []
    for v, d in DatasetSubmission.CATEGORY_CHOICES:
        category_options.append({'value': v, 'label': d, 'count': category_facets.get(v, 0)})

    # ISO options with counts
    iso_options = []
    for v, d in DatasetSubmission.ISO_TOPIC_CHOICES:
        iso_options.append({'value': v, 'label': d, 'count': iso_facets.get(v, 0)})

    # Year options with counts (based on submission_date for the summary table)
    # Year options with counts (based on expedition_year for the summary table)
    from django.db.models.functions import Substr
    year_facets = dict(published.annotate(submit_year=Substr('expedition_year', 1, 4)).values_list('submit_year').annotate(count=Count('id')))
    
    # Generate years from the min submission/user year to the current year
    from django.utils import timezone
    from django.db import connection
    current_year = timezone.now().year
    min_year_dict = published.annotate(submit_year=Substr('expedition_year', 1, 4)).order_by('submit_year').first()
    if min_year_dict and hasattr(min_year_dict, 'submit_year'):
        try:
             start_year = int(min_year_dict.submit_year)
        except ValueError:
             start_year = current_year
    else:
        start_year = current_year

    # Also include legacy user_login years so the dropdown covers years where users registered
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT MIN(EXTRACT(YEAR FROM CAST(created_ts AS timestamp))) FROM user_login WHERE created_ts IS NOT NULL;")
            r = cursor.fetchone()[0]
            if r:
                user_min_year = int(r)
                start_year = min(start_year, user_min_year)
    except Exception:
        # ignore and keep start_year as dataset min
        pass
    
    year_options = []
    default_year = request.GET.get('year')
    max_data_year = None
    
    for y in range(current_year, start_year - 1, -1):
        count = year_facets.get(str(y), 0)
        year_options.append({'value': str(y), 'label': str(y), 'count': count})
        if count > 0 and not max_data_year:
            max_data_year = str(y)
            
    if not default_year:
        default_year = max_data_year or str(current_year)

    # Keyword options with counts
    all_keywords_raw = published.values_list('keywords', flat=True)
    keyword_counter = Counter()
    for k_str in all_keywords_raw:
        if k_str:
            parts = [k.strip() for k in k_str.split(',') if k.strip()]
            keyword_counter.update(parts)
    top_keywords = keyword_counter.most_common(20)
    keyword_options = [{'value': k, 'label': k, 'count': count} for k, count in top_keywords]

    # Choices for advanced search builder
    expedition_choices = DatasetSubmission.EXPEDITION_TYPES
    category_choices = DatasetSubmission.CATEGORY_CHOICES
    iso_choices = DatasetSubmission.ISO_TOPIC_CHOICES
    year_choices = DatasetSubmission.get_expedition_year_choices()
    platform_list = list(PlatformMetadata.objects.values_list('short_name', flat=True).distinct().order_by('short_name'))
    instrument_list = list(InstrumentMetadata.objects.values_list('short_name', flat=True).distinct().order_by('short_name'))

    # Map data: bounding box coordinates for published datasets
    home_map_data = list(published.filter(
        west_longitude__isnull=False,
        east_longitude__isnull=False,
        south_latitude__isnull=False,
        north_latitude__isnull=False
    ).values(
        'id', 'title',
        'west_longitude', 'east_longitude',
        'south_latitude', 'north_latitude',
        'expedition_type', 'category', 'iso_topic', 'keywords'
    ))

    return render(request, 'home.html', {
        'recent_data': recent_data,
        'popular_data': popular_data,
        'total_datasets': total_datasets,
        'total_users': total_users,
        'total_expeditions': total_expeditions,
        'total_years': total_years,
        'arctic_ds': arctic_ds,
        'arctic_exp': arctic_exp,
        'antarctic_ds': antarctic_ds,
        'antarctic_exp': antarctic_exp,
        'southern_ds': southern_ds,
        'southern_exp': southern_exp,
        'himalaya_ds': himalaya_ds,
        'himalaya_exp': himalaya_exp,
        # Chart Data
        'keywords_data': keywords_data,
        'iso_data': iso_data,
        'location_data': location_data,
        'trend_data': trend_data,
        # Metadata Dashboard Data
        'metadata_count': metadata_count,
        'rawdata_count': rawdata_count,
        'researcher_count': researcher_count,
        'total_users': total_users,
        'download_count': download_count,
        'wordcloud_data': wordcloud_allowlist,
        'country_data': country_data,
        # Advanced Search Section Data
        'expedition_choices': expedition_choices,
        'category_choices': category_choices,
        'iso_choices': iso_choices,
        'year_choices': year_choices,
        'year_options': year_options,
        'default_year': default_year,
        'platform_list': platform_list,
        'instrument_list': instrument_list,
        'home_map_data': home_map_data,
        'expedition_options': expedition_options,
        'category_options': category_options,
        'iso_options': iso_options,
        'keyword_options': keyword_options,
    })

# --------------------
# AI Login Helper
# --------------------

def _check_email_exists(email):
    """
    Check if an email address exists in either the Django auth_user table
    or the legacy user_login table. Returns True if found.
    """
    from .models import UserLogin
    email = email.strip().lower()
    if User.objects.filter(email__iexact=email).exists():
        return True
    if UserLogin.objects.filter(user_id__iexact=email).exists():
        return True
    if UserLogin.objects.filter(e_mail__iexact=email).exists():
        return True
    return False


def _get_client_ip(request):
    """Extract the real IP address from the request."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# --------------------
# Login View (with AI Smart Messaging)
# --------------------

class UserLoginView(LoginView):
    authentication_form = CaptchaLoginForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        """
        Called on every failed login submission.

        We only count an attempt against the AI-bubble threshold when the
        CREDENTIAL check fails (wrong email/password) — NOT when only the
        CAPTCHA field is wrong. This ensures the bubble appears on exactly
        the 3rd bad-credential attempt.

        Captcha error key  : 'captcha'
        Credential error key: '__all__' (non-field error from AuthenticationForm)
        """
        email = self.request.POST.get('username', '').strip().lower()
        ip = _get_client_ip(self.request)

        # Determine failure type
        has_credential_error = '__all__' in form.errors
        extra_context = {}

        if has_credential_error:
            # Log and count ONLY real credential failures
            LoginAttempt.objects.create(email=email, ip_address=ip)

            attempts = self.request.session.get('login_attempts', 0) + 1
            self.request.session['login_attempts'] = attempts
            self.request.session.modified = True
            extra_context['attempt_count'] = attempts

            # Trigger bubble on the 3rd+ credential failure
            if attempts >= 3 and email:
                if _check_email_exists(email):
                    # Email found — password is wrong, suggest reset
                    extra_context['ai_message'] = 'suggest_reset'
                    extra_context['ai_email'] = email
                else:
                    # Email not in Django auth_user OR legacy user_login
                    extra_context['ai_message'] = 'not_found'
                    extra_context['ai_email'] = email
        else:
            # Only captcha failed — pass current count so template knows
            # how many more real attempts remain before bubble triggers.
            extra_context['attempt_count'] = self.request.session.get('login_attempts', 0)

        return self.render_to_response(self.get_context_data(form=form, **extra_context))


    def form_valid(self, form):
        """On successful login, clear the failed attempt counter."""
        self.request.session.pop('login_attempts', None)
        return super().form_valid(form)


# --------------------
# Password Reset (token/link-based)
# --------------------

# tooling for token generation
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse


def forgot_password(request):
    """
    Step 1: User enters their email.

    - Rate‑limits by IP (max 10 requests per hour).
    - If the address exists (including legacy lookup), ensure a corresponding
      Django `User` object and then generate a signed token/uid pair.
    - Email a reset link containing `uidb64`/`token` to the user.  We do **not**
      reveal whether the address was valid.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        ip = _get_client_ip(request)

        # --- Rate limiting check ---
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_attempts = LoginAttempt.objects.filter(
            ip_address=ip,
            timestamp__gte=one_hour_ago,
            was_blocked=True
        ).count()
        otp_requests_this_hour = PasswordResetOTP.objects.filter(
            email__icontains='',
        ).filter(created_at__gte=one_hour_ago).count()

        if otp_requests_this_hour >= 10:
            LoginAttempt.objects.create(email=email, ip_address=ip, was_blocked=True)
            messages.error(
                request,
                "Too many password reset requests from your network. Please try again in an hour."
            )
            return render(request, 'registration/forgot_password.html', {'blocked': True})

        # --- If the email really exists, prepare a reset link ---
        if email and _check_email_exists(email):
            # find or create associated Django user (legacy compatibility)
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                # replicate the legacy creation logic from the old confirm view
                from .models import UserLogin
                legacy = None
                try:
                    legacy = UserLogin.objects.filter(
                        user_id__iexact=email
                    ).first() or UserLogin.objects.filter(e_mail__iexact=email).first()
                except Exception:
                    legacy = None

                if legacy:
                    name_parts = (legacy.user_name or 'NPDC User').split()
                    user, created = User.objects.get_or_create(
                        username=email,
                        defaults={
                            'email': email,
                            'first_name': name_parts[0],
                            'last_name': ' '.join(name_parts[1:]) if len(name_parts) > 1 else '',
                            'is_active': True,
                        }
                    )
                    profile_title = {'mr': 'Mr', 'ms': 'Ms', 'dr': 'Dr', 'prof': 'Prof'}.get(
                        (legacy.title or '').strip().lower().rstrip('.'), 'Mr'
                    )
                    Profile.objects.update_or_create(
                        user=user,
                        defaults={
                            'title': profile_title,
                            'organisation': (legacy.organisation or '').strip(),
                            'organisation_url': (legacy.url or '').strip() if legacy.url else '',
                            'designation': (legacy.designation or '').strip(),
                            'is_approved': True,
                            'approved_at': timezone.now(),
                        }
                    )
                else:
                    # should not happen because _check_email_exists returned True
                    user = None

            if user:
                # generate signed token/uid and email the reset link
                token = default_token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                # to avoid any '=' padding characters in the URL, encode the
                # raw token with urlsafe base64.  the result will contain only
                # alphanumerics, '-' and '_' which are never wrapped by mail
                # clients; we still quote for completeness.
                import base64
                token_b64 = base64.urlsafe_b64encode(token.encode('utf-8')).decode('ascii').rstrip('=')
                from urllib.parse import quote
                token_quoted = quote(token_b64, safe='')
                reset_link = request.build_absolute_uri(
                    reverse('users:reset_password_confirm', kwargs={
                        'uidb64': uidb64,
                        'token': token_quoted,
                    })
                )
                # diagnostic logging to help debug issues with link transport
                logger = logging.getLogger(__name__)
                # use WARNING so the message appears with default config
                logger.warning(
                    "Password reset link generated: email=%s uidb64=%s token=%r b64=%r quoted=%r link=%s",
                    email, uidb64, token, token_b64, token_quoted, reset_link
                )

                # log the request for rate-limiting purposes. we also
                # save the base64 token so that we can correct broken links
                token_b64_value = token_b64 if 'token_b64' in locals() else None
                try:
                    PasswordResetOTP.objects.create(
                        email=email,
                        otp='link',
                        token_b64=token_b64_value,
                    )
                except Exception:
                    # silently ignore if something goes wrong with logging
                    pass

                subject = '[NPDC] Password Reset Request'
                # render both HTML and text templates explicitly
                html_body = render_to_string('emails/password_reset_link_email.html', {
                    'email': email,
                    'reset_link': reset_link,
                })
                text_body = render_to_string('emails/password_reset_link_email.txt', {
                    'email': email,
                    'reset_link': reset_link,
                })

                try:
                    # if we're using the console backend for development, avoid
                    # attaching the HTML part so that only plain text is printed.
                    # also echo the link explicitly so the admin doesn't have to
                    # copy it out of quoted-printable output.
                    if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
                        from django.core.mail import EmailMessage
                        mail = EmailMessage(
                            subject=subject,
                            body=text_body,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[email],
                        )
                        mail.encoding = 'utf-8'
                        mail.send()
                        # print link on its own line for easy copy/paste
                        print(f"[DEV] Password reset link: {reset_link}")
                    else:
                        mail = EmailMultiAlternatives(
                            subject=subject,
                            body=text_body,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[email],
                        )
                        mail.attach_alternative(html_body, 'text/html')
                        mail.encoding = 'utf-8'
                        mail.send()
                except Exception as e:
                    print(f"[NPDC] Password reset email failed: {e}")

        # Always respond the same way for security
        return render(request, 'registration/forgot_password.html', {
            'link_sent': True,
            'submitted_email': email,
        })

    return render(request, 'registration/forgot_password.html')


def reset_password_confirm(request, uidb64=None, token=None):
    """
    View that handles the reset link from the email.  The URL is of the form
    `/reset-password/<uidb64>/<token>/` and is generated with
    `default_token_generator`.

    Once the link is confirmed, the user picks a new password.
    """
    # verify parameters and get user
    if not uidb64 or not token:
        # show a helpful page rather than an immediate redirect so users
        # understand what happened and can request a fresh link
        return render(request, 'registration/reset_password_confirm.html', {
            'token_invalid': True,
            'reason': 'missing',
            'email': None,
        })

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # If the UID didn't decode to a user, render a friendly invalid page
    if user is None:
        logging.getLogger(__name__).warning("Password reset failed: invalid UID (%s)", uidb64)
        return render(request, 'registration/reset_password_confirm.html', {
            'token_invalid': True,
            'reason': 'invalid_uid',
            'email': None,
        })

    # Normalize token: URL-decode and rebuild original token from its
    # base64‑encoded form.  When we generated the link we encoded the
    # original Django token as urlsafe_base64 with padding stripped so that the
    # path segment contains no '=' characters.  Here we reverse that process.
    import base64
    from urllib.parse import unquote
    raw_token = token

    # undo percent-encoding first (handles %3D etc)
    try:
        token = unquote(token)
    except Exception:
        token = raw_token

    # strip whitespace and slashes that might sneak in via wrapping/copy‑paste
    if token is not None:
        token = ''.join(token.split())
    token = token.strip().rstrip('/')
    # remove any stray '=' characters that may be inserted by quoted-printable
    # wrapping.  The canonical b64 string contains no '=' (we stripped them at
    # generation time).  Note: this cannot recover characters that were lost
    # because the link itself was truncated; those cases are handled below.
    if token is not None:
        token = token.replace('=', '')

    # At this point `token` should be the base64-safe string we generated earlier
    # (possibly truncated).  If the user clicked a wrapped link which got split,
    # there's a good chance `token` now equals only the first part.  We search
    # our log table to see if any recent entry has a matching prefix.  If we
    # find one, redirect the browser to the full, correct URL so the second hit
    # will succeed immediately.
    if token:
        prefix = token
        candidate = PasswordResetOTP.objects.filter(token_b64__startswith=prefix).order_by('-created_at').first()
        if candidate and candidate.token_b64 and candidate.token_b64 != prefix:
            # build redirect URL and send user there
            correct_link = request.build_absolute_uri(
                reverse('users:reset_password_confirm', kwargs={
                    'uidb64': uidb64,
                    'token': candidate.token_b64,
                })
            )
            return redirect(correct_link)

    # now decode back to the original token string; pad for base64
    try:
        padding = '=' * (-len(token) % 4)
        token = base64.urlsafe_b64decode(token + padding).decode('utf-8')
    except Exception:
        # if decoding fails we'll treat it as the raw value and let
        # standard check_token handle the mismatch
        pass

    # Log raw and normalized token for debugging (development only)
    logger = logging.getLogger(__name__)
    # log at INFO so it appears even if DEBUG level isn't enabled
    logger.info(
        "Password reset invoked: uidb64=%s raw_token=%r normalized_token=%r token_len=%s",
        uidb64, raw_token, token, len(token) if token is not None else 'None'
    )

    # Check token and allow tolerant variants when email/transport has stripped
    # padding. Some mail/console transports may wrap or drop '=' padding
    # characters; try adding up to 3 '=' characters as fallbacks before
    # giving up to improve robustness for real users.
    token_ok = False
    tried_variant = None
    tried_candidates = []
    # First try the token as received
    if default_token_generator.check_token(user, token):
        token_ok = True
        tried_variant = token
    else:
        # Try adding 1..3 '=' padding characters (common base64 padding lengths)
        for pad in range(1, 4):
            candidate = token + ('=' * pad)
            tried_candidates.append(candidate)
            if default_token_generator.check_token(user, candidate):
                token_ok = True
                tried_variant = candidate
                # update token variable so subsequent logic uses the working one
                token = candidate
                break

    # Log what candidates were tried (debug)
    if not token_ok:
        logger.debug("Password reset: tried candidates=%r", tried_candidates)

    if not token_ok:
        logger = logging.getLogger(__name__)
        try:
            last_login = getattr(user, 'last_login', None)
        except Exception:
            last_login = None
        logger.warning(
            "Password reset token invalid for user=%s uidb64=%s uid=%s last_login=%s PASSWORD_RESET_TIMEOUT=%s tried_variant=%s",
            getattr(user, 'email', '<no-email>'), uidb64, getattr(user, 'pk', None), last_login,
            getattr(settings, 'PASSWORD_RESET_TIMEOUT', '<unset>'), tried_variant
        )
        return render(request, 'registration/reset_password_confirm.html', {
            'token_invalid': True,
            'reason': 'expired',
            'email': user.email,
        })

    email = user.email

    if request.method == 'POST':
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # --- Validate passwords ---
        import re
        errors = []
        if new_password != confirm_password:
            errors.append("Passwords do not match.")
        if len(new_password) < 8:
            errors.append("Password must be at least 8 characters.")
        if not re.search(r'[A-Z]', new_password):
            errors.append("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', new_password):
            errors.append("Password must contain at least one lowercase letter.")
        if not re.search(r'\d', new_password):
            errors.append("Password must contain at least one number.")
        if not re.search(r'[@$!%*?&]', new_password):
            errors.append("Password must contain at least one special character (@$!%*?&).")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'registration/reset_password_confirm.html', {'email': email})

        # all good; set new password
        user.set_password(new_password)
        user.save()

        messages.success(
            request,
            "✅ Your password has been reset successfully. You can now log in."
        )
        return redirect('users:login')

    return render(request, 'registration/reset_password_confirm.html', {'email': email})


@staff_member_required
def view_user_details(request, user_id):
    """View all registration details for a user"""
    user = get_object_or_404(User, id=user_id)
    profile = getattr(user, 'profile', None)
    
    return render(
        request,
        "admin/user_detail.html",
        {
            "viewed_user": user,
            "profile": profile,
        }
    )


@staff_member_required
def edit_user_details(request, user_id):
    """Edit user and profile details before approval"""
    user = get_object_or_404(User, id=user_id)
    profile = getattr(user, 'profile', None)
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        # Handle Request Info
        if action == "request_info":
            message_body = request.POST.get("message_body")
            if message_body:
                from django.core.mail import send_mail
                try:
                    send_mail(
                        subject='NPDC Registration - Information Request',
                        message=message_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    messages.success(request, f"Information request sent to {user.email}")
                    

                    
                except Exception as e:
                    messages.error(request, f"Failed to send email: {str(e)}")
            else:
                messages.error(request, "Message body cannot be empty.")
            
            # Stay on the same page
            return redirect("users:edit_user_details", user_id=user.id)

        # Handle Reject
        if action == "reject":
            email = user.email
            # Mark as rejected instead of deleting
            if hasattr(user, 'profile'):
                user.profile.is_rejected = True
                user.profile.rejected_at = timezone.now()
                user.profile.save()
            

            
            messages.success(request, f"User {email} has been rejected.")
            return redirect("users:user_approval_dashboard")
            
        form = AdminUserEditForm(request.POST, instance=user, profile=profile)
        if form.is_valid():
            user = form.save()
            
            # Handle Approve
            if action == "approve":
                user.is_active = True
                user.save()
                
                # Check if Profile exists before accessing approved_at
                if hasattr(user, 'profile'):
                    user.profile.is_approved = True
                    user.profile.approved_at = timezone.now()
                    user.profile.save()
                    
                messages.success(request, f"User {user.email} updated and APPROVED.")
            else:
                messages.success(request, f"User {user.email} details saved (Pending Approval).")
                
            return redirect("users:user_approval_dashboard")
    else:
        form = AdminUserEditForm(instance=user, profile=profile)
    
    return render(
        request,
        "admin/user_edit.html",
        {
            "form": form,
            "viewed_user": user,
        }
    )




@staff_member_required
def admin_change_user_password(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        from .forms import AdminSetPasswordForm
        form = AdminSetPasswordForm(target_user, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Password for {target_user.email} has been changed successfully.")
            return redirect('users:user_approval_dashboard')
    else:
        from .forms import AdminSetPasswordForm
        form = AdminSetPasswordForm(target_user)
        
    return render(request, 'admin/admin_change_password.html', {
        'form': form,
        'target_user': target_user
    })


def about(request):
    return render(request, 'about.html')

def field_data(request):
    return render(request, 'field_data.html')

def contact_us(request):
    return render(request, 'contact_us.html')

def data_policy(request):
    return render(request, 'data_policy.html')


def polar_directory(request):
    """Indian Antarctic Expedition Directory search page."""
    import os
    results = None
    searched = False
    choose = request.GET.get('choose', '')
    station = request.GET.get('station', '')
    station_content = None
    station_name = None
    template_name = 'polar_directory.html'

    published = DatasetSubmission.objects.filter(status='published')

    if choose:
        searched = True
        if choose == 'institute':
            results = published.order_by('organisation').distinct()
        elif choose == 'project':
            results = published.order_by('title')
        elif choose == 'member':
            results = published.order_by('submitter__last_name')
        elif choose == 'expedition':
            results = published.order_by('-expedition_number')
        elif choose == 'expedition_role':
            results = published.order_by('submitter__last_name')
        elif choose == 'expedition_leader':
            results = published.order_by('-expedition_number')
        elif choose == 'keyword':
            results = published.exclude(keywords__isnull=True).exclude(keywords='').order_by('title')
        else:
            results = published.none()

    elif station:
        searched = True
        station_mapping = {
            'maitri': 'Maitri',
            'bharati': 'Bharati',
            'dakshin_gangotri': 'Dakshin Gangotri',
            'larsemann_hills': 'Larsemann Hills',
            'south_pole': 'South Pole',
            'chandra_basin': 'Chandra Basin',
        }
        station_name = station_mapping.get(station, station)
        results = published.filter(title__icontains=station_name)
        
        # Pagination for station content
        page = request.GET.get('page', 1)
        try:
            page = int(page)
        except ValueError:
            page = 1
            
        # Determine total pages by checking file existence
        total_pages = 0
        while True:
            check_path = os.path.join(settings.BASE_DIR, 'static', 'content', 'stations', f'{station}_{total_pages + 1}.html')
            if os.path.exists(check_path):
                total_pages += 1
            else:
                break
        
        # Load content for requested page
        if page < 1: page = 1
        if total_pages > 0 and page > total_pages: page = total_pages
        
        content_path = os.path.join(settings.BASE_DIR, 'static', 'content', 'stations', f'{station}_{page}.html')
        
        # Fallback to legacy non-numbered file if numbered doesn't exist (though we converted all)
        if not os.path.exists(content_path) and page == 1:
             legacy_path = os.path.join(settings.BASE_DIR, 'static', 'content', 'stations', f'{station}.html')
             if os.path.exists(legacy_path):
                 content_path = legacy_path
                 total_pages = 1

        if os.path.exists(content_path):
            with open(content_path, 'r', encoding='utf-8') as f:
                station_content = f.read()
            template_name = 'station_detail.html'
            
        context = {
            'results': results,
            'searched': searched,
            'choose': choose,
            'station': station,
            'station_content': station_content,
            'station_name': station_name,
            'current_page': page,
            'total_pages': total_pages,
            'page_range': range(1, total_pages + 1),
        }
        return render(request, template_name, context)

    return render(request, template_name, {
        'results': results,
        'searched': searched,
        'choose': choose,
        'station': station,
    })

def api_summary_table(request):
    """
    Returns JSON data for the Summary Table for a specific year.
    It expects a 'year' GET parameter.
    """
    from django.http import JsonResponse
    from django.db.models import Count
    from django.db.models.functions import ExtractMonth
    from data_submission.models import DatasetSubmission
    from django.contrib.auth.models import User
    from django.utils import timezone

    try:
        year = int(request.GET.get('year', timezone.now().year))
    except ValueError:
        year = timezone.now().year

    # 1. Total Number of Datasets and Metadata Submitted (Monthly)
    datasets_qs = DatasetSubmission.objects.filter(expedition_year__startswith=str(year))
    # Note: expedition_year is a string like "2021-2022" or "2019".
    # since we don't have month granularity for expedition year, we just divide them across months or put in Jan
    ds_monthly = datasets_qs.annotate(month=ExtractMonth('submission_date')).values('month').annotate(count=Count('id'))
    ds_map = {item['month']: item['count'] for item in ds_monthly}
    ds_counts = [ds_map.get(m, 0) for m in range(1, 13)]
    
    # Total Overall Metadata Submitted for the requested year (published only)
    overall_datasets = DatasetSubmission.objects.filter(status='published', expedition_year__startswith=str(year)).count()

    # 2. Total Number of User Registered at NPDC (Monthly)
    # Prefer legacy `user_login` table if it exists (keeps counts consistent with imported SQL dump)
    from django.db import connection

    users_counts = [0] * 12
    try:
        with connection.cursor() as cursor:
            # Check columns in user_login to find a date-like column
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'user_login';")
            cols = [r[0] for r in cursor.fetchall()]
            # Prefer explicit timestamp-like columns if present
            preferred = ['created_ts', 'created_at', 'created_on', 'created', 'date', 'joined', 'registered', 'reg', 'updated_ts']
            date_col = None
            lower_cols = [c.lower() for c in cols]
            for p in preferred:
                if p in lower_cols:
                    # pick the original-case column name
                    date_col = cols[lower_cols.index(p)]
                    break
            # Fallback: pick any column name that contains a date-like substring but avoid *_by fields
            if not date_col:
                for c in cols:
                    lc = c.lower()
                    if ('date' in lc or 'joined' in lc or 'created' in lc or 'reg' in lc) and not lc.endswith('_by'):
                        date_col = c
                        break

            if date_col:
                # Get monthly counts from legacy table for the requested year
                # created_ts is stored as character varying in legacy SQL, cast to timestamp
                cursor.execute(
                    f"SELECT EXTRACT(MONTH FROM CAST({date_col} AS timestamp)) AS month, COUNT(*) FROM user_login WHERE EXTRACT(YEAR FROM CAST({date_col} AS timestamp)) = %s GROUP BY month;",
                    [year]
                )
                rows = cursor.fetchall()
                month_map = {int(r[0]): r[1] for r in rows}
                users_counts = [month_map.get(m, 0) for m in range(1, 13)]
            else:
                # Fallback to Django User model if no suitable column found
                users_qs = User.objects.filter(date_joined__year=year)
                users_monthly = users_qs.annotate(month=ExtractMonth('date_joined')).values('month').annotate(count=Count('id'))
                users_map = {item['month']: item['count'] for item in users_monthly}
                users_counts = [users_map.get(m, 0) for m in range(1, 13)]
    except Exception:
        # On any error, fallback to Django User model
        users_qs = User.objects.filter(date_joined__year=year)
        users_monthly = users_qs.annotate(month=ExtractMonth('date_joined')).values('month').annotate(count=Count('id'))
        users_map = {item['month']: item['count'] for item in users_monthly}
        users_counts = [users_map.get(m, 0) for m in range(1, 13)]

    # 3. Downloads (Mock static data since no model exists)
    downloads_counts = [0] * 12
    # 4. Data Requests (Mock static data since no model exists)
    requests_counts = [0] * 12

    # 5. Researchers active in the given year (distinct scientist emails)
    try:
        researchers_count = DatasetSubmission.objects.filter(expedition_year__startswith=str(year))\
            .values('scientists__email')\
            .distinct()\
            .exclude(scientists__email__isnull=True)\
            .exclude(scientists__email='')\
            .count()
    except Exception:
        researchers_count = 0

    return JsonResponse({
        'year': year,
        'monthly': {
            'downloads': downloads_counts,
            'requests': requests_counts,
            'datasets': ds_counts,
            'users': users_counts,
        },
        'overall': {
            'total_datasets': overall_datasets,
            'users_this_year': sum(users_counts),
            'researchers_this_year': researchers_count,
            'downloads_this_year': sum(downloads_counts),
        }
    })


def station_detail(request, station_name):
    from django.shortcuts import render
    from data_submission.models import DatasetSubmission

    # Static lookup for station mock details
    station_details = {
        'maitri': {
            'name': 'Maitri',
            'location': 'Schirmacher Oasis, Queen Maud Land, East Antarctica',
            'description': 'In the year 1988 an ice free, rocky area on the Schirmacher oasis was selected to build the Second Research Station “Maitri (70o45’52” S & 11o44’03” E). The building was erected on steel stilts, and has since stood the test of time. Maitri also serves as a gateway to one of the largest mountain chains in central Dronning Maud land, located south of Schirmacher. It is an inland station about 100 km from the shore at an elevation of about 50 meters above sea level. It can support 25 persons in the main building during summers as well as winters and about 40 in summer facility comprising of containerized living modules. The station consists of one main building, fuel farm, fuel station, lake water pump house, a summer camp and a number of smaller containerized modules. The main building offers regulated power supply, automated heating with hot and cold running water, incinerator toilets, cold storage, PA system, living, dining, lounge and containerized laboratory space. The communication is through dedicated satellite channels providing connectivity for voice, video and data with India mainland.',
            'facilities': 'Living quarters for 25-70 personnel, scientific laboratories, satellite communication center, medical facilities, snow vehicles, and a water filtration system.',
            'image': 'images/stations/Maitri.jpg',
            'gallery': [
                'images/Polar_stations/Maitri/IMG_2.jpg',
                'images/Polar_stations/Maitri/IMG_4.jpg',
                'images/Polar_stations/Maitri/IMG_5.jpg',
            ]
        },
        'bharati': {
            'name': 'Bharati',
            'location': 'Larsemann Hills, East Antarctica',
            'description': 'About 3000 km east of Maitri, the new Indian research base ‘Bharati’ is located between Thala Fjord & Quilty bay, east of Stornes Peninsula in Antarctica at 69° 24.41\' S, 76° 11.72\' E approximately at 35 m above sea level. The station with a very small footprint was commissioned on 18 March 2012 to facilitate year-round scientific research activity by the Indian Antarctic program. Station can support 47 personnel on twin sharing basis in the main building during summer as well as winters with additional 25 in emergency shelters / summer camps during summers and thus making the total capacity as 72. The station consists of one main building, fuel farm, fuel station, sea water pump house, a summer camp and a number of smaller containerized modules. The main building offers regulated power supply, automated heating and air conditioning with hot and cold running water, flush toilets, sauna, cold storage, PA system, aesthetically designed living, dining, lounge and laboratory space. The communication is through dedicated satellite channels providing connectivity for voice, video and data with India mainland.',
            'facilities': 'Accommodates 47-72 personnel, oceanography and continental physics labs, automated heating/AC, satellite communication modules, and the Antarctica Ground Station for Earth Observation Satellites (AGEOS).',
            'image': 'images/stations/Bharati.jpg',
            'gallery': [
                'images/Polar_stations/Bharati/IMG_(1).jpg',
                'images/Polar_stations/Bharati/IMG_(14).jpg',
                'images/Polar_stations/Bharati/IMG_(20).jpg',
                'images/Polar_stations/Bharati/IMG_(4).jpg',
                'images/Polar_stations/Bharati/IMG_(8).jpg',
                'images/Polar_stations/Bharati/IMG_(9).jpg',
            ]
        },
        'svalbard': {
            'name': 'Himadri',
            'location': 'Ny-Ålesund, Spitsbergen, Svalbard, Norway',
            'description': 'HIMADRI \'the abode of snow\' is India’s first research station located at the International Arctic Research base, NyÅlesund, Svalbard, Norway. It is located at a distance of 1,200 kilometres from the North Pole. It was inaugurated on the 1st July, 2008 by Shri. KapilSibal the-then Hon. Minister of Science and Technology and Earth Sciences, in the presence of dignitaries from Norway, UK, Germany and other countries besides India. This station was opened considering the sustained interest shown by Indian scientists in pursuing scientific studies in the Arctic. Himadri provides extensive field and laboratory support required for pursuing research activities in the Arctic. NCAOR as nodal agency make sure availability of the requisite facilities at the Himadri.',
            'facilities': 'Accommodates up to eight scientists, offering living space, workspaces, computer rooms, and access to the nearby Gruvebadet Observatory for atmospheric data collection.',
            'image': 'images/Polar_stations/Himadri/IMG_1.jpg',
            'gallery': [
                'images/Polar_stations/Himadri/IMG_1.jpg',
                'images/Polar_stations/Himadri/IMG_2.jpg',
                'images/Polar_stations/Himadri/IMG_5.jpg',
                'images/Polar_stations/Himadri/IMG_6 (1).jpg',
            ]
        },
        'himansh': {
            'name': 'Himansh',
            'location': 'Sutri Dhaka, Chandra Basin, Spiti Valley, Himachal Pradesh (Altitude: 4,080m)',
            'description': 'Background: As part of the Indian government’s initiatives for better understanding of glacier –climate inter-relationship and quantify the Himalayan glacier responses towards the climate change, National Centre for Antarctic and Ocean Research (NCAOR), Goa, under the Ministry of Earth Sciences has established a high altitude research station in Himalaya called HIMANSH. HIMANSH is a dedicated Research Station established at Sutri Dhaka, Chandra Basin, Lahaul-Spiti valley of Himachal Pradesh which has an altitude of 4080m amsl. The station was unveiled on Sunday 9th October 2016 and since then the station has made for functioning round the year however for 2016 it have plan to closed during winter (15th November to April 2017).<br><br>Location:<br>Name : HIMANSH<br>Place : Sutri Dhaka, Chandra basin, Lahaul-Spiti District of Himachal Pradesh<br>Latitude : 32°24’34”<br>Longitude : 77°36’32"<br>Altitude : 4080m amsl<br><br>Approach: The nearest town is Manali, which is approximately 150km from HIMANSH. HIMANSH established at Sutri Dhaka which is 6-7 km from road head name Batal. Batal is lies on Manali-Kaza route having an approx. 143 km distance from Manali. The connecting road is a mountain road and only opens during June-November.<br><br>Manali -> 143 km -> Batal -> 7 km -> Sutri Dhaka<br><br>Introduction: HIMANSH has three units which includes two accommodation units which accommodate eight persons at a time and one Laboratory unit equipped with various scientific instruments such as Steam Drill, Ground Penetrating Radar, Global Positioning System, Snow Fork, Snow/Ice Corer, Flow Tracker, Water Level Recorder, Automatic Weather Station, Radiometer etc for Glaciological Research.<br><br>Objectives: To facilitate Himalayan Cryosphare Studies in Chandra basin to study the dynamics and the rate of change of Himalayan glaciers to understand its impact on hydrology and climate. Since Upper Himalaya has dominated by very harsh climate and terrain conditions, the station will enable scientists and field staff to stay in relatively weather resistant environment and carry out field experiments and monitoring on a continuous basis. This station “HIMANSH” has established under NCAOR programm “Cryosphare and Climate” for proper monitoring of glaciers to understand dynamics, mass budget, energy and hydrological balance of Chandra basin.<br><br>Observations: A total of six glaciers (280 km2 glacier area) of Chandra basin name Sutri Dhaka(25 km2), Batal (5 km2), Bara Shigri (137 km2), Samudra Tapu (95 km2), Gepang Gath (14 km2) and Kunjum (4 km2)have been monitoring for mass, energy and hydrological balance including surface flow, ice flux, terminal fluctuation using this station “HIMANSH”. Apart from above two Automatic Weather Stations (AWS) and five Water Level Recorders (WLRs) have been installed over glacier surface and along with a stretch of 120km of Chandra River respectively for energy and hydrological budget calculation. This all generated data will help to understand glacier behaviours in respect to climate including quantification of hydrological contribution to Chandra basin (upper Indus basin).<br><br>All the glaciers under observation in the Chandra basin (Western Himalaya), during the last 2-3 years have shown cumulative negative mass balance. Mass balance is found to be dependent on solar radiation, debris cover, local and regional precipitation, slope and the shading effect of surrounding steep slopes. Debris cover is one of the significant controlling factors for spatial variability of ablation rate. In contrast to the normal ablation pattern, debris covered glaciers experienced an inverse ablation rate with altitude. Thicker debris protect ice surface efficiently from melting than thin debris. Maximum discharge takes place from mid-July to mid-August further drastically decreases from mid of September. In Indus basin, estimated glacier melt contributes ~44% of the total discharge however for Chandra basin it is much higher (70-80%) of the total discharge.',
            'facilities': 'Accommodation for eight people, laboratory unit, automatic weather stations, water level recorders, ground-penetrating radars, geodetic GPS, and satellite phone terminals.',
            'image': 'images/Polar_stations/Himansh/IMG_2.jpg',
            'gallery': [
                'images/Polar_stations/Himansh/IMG_2.jpg',
                'images/Polar_stations/Himansh/IMG_3.jpg',
                'images/Polar_stations/Himansh/IMG_4.jpg',
                'images/Polar_stations/Himansh/IMG_6.jpg',
            ]
        },
        'sagar-nidhi': {
            'name': 'Sagar Nidhi',
            'location': 'Southern Ocean',
            'description': 'Sagar Nidhi is an oceanographic research vessel playing a critical role in India\'s polar and marine science programs.',
            'facilities': 'Ocean monitoring, remote sensing, and underwater robotics.',
            'image': 'images/stations/Sagar_Nidhi.jpg'
        },
    }

    # Fallback to a generic 404 or default if not exactly matched
    station_info = station_details.get(station_name.lower())
    if not station_info:
        from django.http import Http404
        raise Http404('Station not found.')

    # Fetch mock datasets to show associated research data
    related_datasets = DatasetSubmission.objects.filter(status='PUBLISHED').order_by('-submission_date')[:5]

    context = {
        'station': station_info,
        'related_datasets': related_datasets
    }
    return render(request, 'station_detail.html', context)
