from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User, Group
from django.forms import inlineformset_factory
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
import json
import logging

from .forms import PaleoTemporalCoverageForm
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST as require_post_method
from .models import DatasetSubmission, ScientistDetail, InstrumentMetadata, State
from .ai_helpers import (
    classify_dataset,
    suggest_keywords,
    check_abstract_quality,
    extract_spatial_data,
    prefill_form,
    generate_review_notes,
    generate_title,
    generate_purpose,
    suggest_resolution,
)
from .forms import (
    DatasetSubmissionForm,
    DatasetCitationForm,
    ScientistDetailForm,
    InstrumentMetadataForm,
    PlatformMetadataForm,
    GPSMetadataForm,
    LocationMetadataForm,
    DataResolutionMetadataForm,
    DatasetFilesForm,
)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# =====================================================
# ROLE CHECK HELPERS (RBAC)
# =====================================================

def is_reviewer(user):
    return user.groups.filter(name="Reviewer").exists()

def is_submitter(user):
    # Allow any authenticated user to submit datasets
    return user.is_authenticated

def is_admin(user):
    return user.is_staff or user.is_superuser

# =====================================================
# FORMSETS
# =====================================================

ScientistFormSet = inlineformset_factory(
    DatasetSubmission,
    ScientistDetail,
    form=ScientistDetailForm,
    extra=1,
    can_delete=True
)

InstrumentFormSet = inlineformset_factory(
    DatasetSubmission,
    InstrumentMetadata,
    form=InstrumentMetadataForm,
    extra=1,
    can_delete=True
)

# =====================================================
# SUBMISSION VIEW
# =====================================================

# =====================================================
# SUBMISSION VIEW (FIXED VERSION)
# =====================================================

@login_required
def submission_instructions(request):
    """View to show instructions before submission"""
    return render(request, "data_submission/instructions.html")

@login_required
@user_passes_test(is_submitter)
@require_http_methods(["GET", "POST"])
def submit_dataset(request):
    
    # Check if editing an existing submission
    submission_id = request.GET.get('edit')
    dataset = None
    is_edit_mode = False
    
    if submission_id:
        dataset = get_object_or_404(DatasetSubmission, pk=submission_id, submitter=request.user)
        is_edit_mode = True
        
        # 🚨 ALLOW EDITING FOR ALL STATUSES PER USER REQUEST
        # Previously locked published datasets, now allowed.

    
    if request.method == "POST":
        # 🚀 REUSE EXISTING INSTANCES FOR UPDATES, NOT CREATE NEW
        if dataset:
            dataset_form = DatasetSubmissionForm(request.POST, request.FILES, instance=dataset)
            # Get or create related instances for updating
            citation_instance = getattr(dataset, 'citation', None)
            platform_instance = getattr(dataset, 'platform', None)
            gps_instance = getattr(dataset, 'gps', None)
            location_instance = getattr(dataset, 'location', None)
            resolution_instance = getattr(dataset, 'resolution', None)
            paleo_instance = getattr(dataset, 'paleo_temporal', None)
            
            citation_form = DatasetCitationForm(request.POST, instance=citation_instance)
            platform_form = PlatformMetadataForm(request.POST, instance=platform_instance)
            gps_form = GPSMetadataForm(request.POST, instance=gps_instance)
            location_form = LocationMetadataForm(request.POST, instance=location_instance)
            resolution_form = DataResolutionMetadataForm(request.POST, instance=resolution_instance)
            
            if gps_instance and gps_instance.gps_used:
                paleo_form = PaleoTemporalCoverageForm(request.POST, instance=paleo_instance)
            else:
                paleo_form = PaleoTemporalCoverageForm(request.POST)
                
            scientist_formset = ScientistFormSet(request.POST, instance=dataset)
            instrument_formset = InstrumentFormSet(request.POST, instance=dataset)
        else:
            dataset_form = DatasetSubmissionForm(request.POST, request.FILES)
            citation_form = DatasetCitationForm(request.POST)
            platform_form = PlatformMetadataForm(request.POST)
            gps_form = GPSMetadataForm(request.POST)
            location_form = LocationMetadataForm(request.POST)
            resolution_form = DataResolutionMetadataForm(request.POST)
            paleo_form = PaleoTemporalCoverageForm(request.POST)
            scientist_formset = ScientistFormSet(request.POST)
            instrument_formset = InstrumentFormSet(request.POST)

        # Validate forms
        dataset_valid = dataset_form.is_valid()
        citation_valid = citation_form.is_valid()
        platform_valid = platform_form.is_valid()
        location_valid = location_form.is_valid()
        resolution_valid = resolution_form.is_valid()
        scientist_valid = scientist_formset.is_valid()
        instrument_valid = instrument_formset.is_valid()

        gps_valid = gps_form.is_valid()
        paleo_valid = paleo_form.is_valid()


        forms_valid = all([
            dataset_valid,
            citation_valid,
            platform_valid,
            gps_valid,
            location_valid,
            resolution_valid,
            scientist_valid,
            instrument_valid,
            paleo_valid,
        ])

        if not forms_valid:
            print("❌ VALIDATION FAILED")
            if not dataset_valid: print(f"Dataset Errors: {dataset_form.errors}")
            if not citation_valid: print(f"Citation Errors: {citation_form.errors}")
            if not platform_valid: print(f"Platform Errors: {platform_form.errors}")
            if not gps_valid: print(f"GPS Errors: {gps_form.errors}")
            if not location_valid: print(f"Location Errors: {location_form.errors}")
            if not resolution_valid: print(f"Resolution Errors: {resolution_form.errors}")
            if not scientist_valid: print(f"Scientist Errors: {scientist_formset.errors}")
            if not instrument_valid: print(f"Instrument Errors: {instrument_formset.errors}")
            if not paleo_valid: print(f"Paleo Errors: {paleo_form.errors}")

        if forms_valid:
            with transaction.atomic():

                if dataset:
                    dataset = dataset_form.save(commit=False)
                else:
                    dataset = dataset_form.save(commit=False)
                    dataset.submitter = request.user
                
                # Auto-populate contact details (Removed from UI)
                if not dataset.contact_person:
                    dataset.contact_person = request.user.get_full_name() or request.user.username
                if not dataset.contact_email:
                    dataset.contact_email = request.user.email
                # Phone is optional in model but let's blank it if not set
                if not dataset.contact_phone: 
                     dataset.contact_phone = ""

                previous_status = dataset.status
                action = request.POST.get("save")

                if action == "SAVE":
                    dataset.status = "draft"
                elif action == "SUBMIT":
                    # Allow re-submission from draft, submitted, revision_requested, AND published
                    if previous_status not in ["draft", "submitted", "revision_requested", "published"]:
                        messages.error(request, "Invalid status transition.")
                        return redirect("data_submission:submit_dataset")
                    
                    dataset.status = 'submitted'
                    dataset.save()
                    
                    messages.success(request, "Dataset submitted successfully!")
                    return redirect("data_submission:my_submissions")
                    dataset.status = "submitted"
                elif action == "PREVIEW":
                    dataset.status = "draft" # Save as draft for preview
                else:
                    dataset.status = "draft"

                if previous_status != dataset.status:
                    dataset.status_updated_at = timezone.now()

                dataset.save()

                # Save related models
                citation = citation_form.save(commit=False)
                citation.dataset = dataset
                citation.save()

                platform = platform_form.save(commit=False)
                platform.dataset = dataset
                platform.save()

                gps = gps_form.save(commit=False)
                gps.dataset = dataset
                gps.save()

                location = location_form.save(commit=False)

                expedition_map = {
                    "antarctic": ("region", "Antarctica"),
                    "arctic": ("region", "Arctic"),
                    "southern_ocean": ("ocean", "Southern Ocean"),
                    "himalaya": ("region", "Himalaya"),
                }

                if dataset.expedition_type in expedition_map:
                    category, loc_type = expedition_map[dataset.expedition_type]
                    location.location_category = category
                    location.location_type = loc_type

                location.dataset = dataset
                location.save()

                resolution = resolution_form.save(commit=False)
                resolution.dataset = dataset
                resolution.save()

                # ✅ Paleo (correct & inside transaction)
                if paleo_form.is_valid() and any(paleo_form.cleaned_data.values()):
                    paleo = paleo_form.save(commit=False)
                    paleo.dataset = dataset
                    paleo.save()
                elif hasattr(dataset, 'paleo_temporal'):
                    dataset.paleo_temporal.delete()

                # ✅ Formsets
                scientist_formset.instance = dataset
                scientist_formset.save()

                instrument_formset.instance = dataset
                instrument_formset.save()

            # 🚀 PREVIEW REDIRECT
            if action == "PREVIEW":
                return render(request, 'data_submission/preview_dataset.html', {'dataset': dataset})

            # 📧 EMAIL NOTIFICATION SYSTEM
            # 📧 EMAIL NOTIFICATION SYSTEM moved to upload_dataset_files view to verify file upload completion before notifying.
            # Only trigger here if we decide metadata-only submission triggers email (currently file upload is required for 'submitted' status in Step 2)
            pass

            # Success message
            if dataset.status == "draft":
                if action != "PREVIEW":
                     messages.success(request, "Metadata saved. Please upload dataset files.")
            else:
                messages.success(
                    request,
                    "Metadata submitted. Please upload dataset files."
                )
                


            logger.info(f"Dataset {dataset.id} {'submitted' if dataset.status == 'submitted' else 'saved'} by user {request.user.id}")

            # 🚀 REDIRECT TO FILE UPLOAD STEP
            return redirect("data_submission:upload_dataset_files", submission_id=dataset.id)

        messages.error(request, "Please correct the errors below.")

    else:
        # 🚀 COMPLETE EDIT MODE IMPLEMENTATION
        if dataset:
            # Pre-load all related instances
            dataset_form = DatasetSubmissionForm(instance=dataset)
            
            # Get related instances or create empty forms
            try:
                citation_instance = dataset.citation
            except:
                citation_instance = None
                
            try:
                platform_instance = dataset.platform
            except:
                platform_instance = None
                
            try:
                gps_instance = dataset.gps
            except:
                gps_instance = None
                
            try:
                location_instance = dataset.location
            except:
                location_instance = None
                
            try:
                resolution_instance = dataset.resolution
            except:
                resolution_instance = None
                
            try:
                paleo_instance = dataset.paleo_temporal
            except:
                paleo_instance = None
            
            citation_form = DatasetCitationForm(instance=citation_instance)
            platform_form = PlatformMetadataForm(instance=platform_instance)
            gps_form = GPSMetadataForm(instance=gps_instance)
            location_form = LocationMetadataForm(instance=location_instance)
            resolution_form = DataResolutionMetadataForm(instance=resolution_instance)
            
            if gps_instance and gps_instance.gps_used:
                paleo_form = PaleoTemporalCoverageForm(instance=paleo_instance)
            else:
                paleo_form = PaleoTemporalCoverageForm()
                
            scientist_formset = ScientistFormSet(instance=dataset)
            instrument_formset = InstrumentFormSet(instance=dataset)
        else:
            dataset_form = DatasetSubmissionForm()
            citation_form = DatasetCitationForm()
            platform_form = PlatformMetadataForm()
            gps_form = GPSMetadataForm()
            location_form = LocationMetadataForm()
            resolution_form = DataResolutionMetadataForm()
            paleo_form = PaleoTemporalCoverageForm()
            scientist_formset = ScientistFormSet()
            instrument_formset = InstrumentFormSet()

    return render(
        request,
        "data_submission/submit_dataset.html",
        {
            "dataset_form": dataset_form,
            "citation_form": citation_form,
            "platform_form": platform_form,
            "gps_form": gps_form,
            "location_form": location_form,
            "resolution_form": resolution_form,
            "scientist_formset": scientist_formset,
            "instrument_formset": instrument_formset,
            "paleo_form": paleo_form,
            "is_edit_mode": is_edit_mode,
            "dataset_id": dataset.id if dataset else None,
        },
    )

def view_submission(request, submission_id):
    """Read-only view for users to see submission details.
    Published datasets are visible to any logged-in user.
    Draft/submitted/under_review/revision only visible to owner or staff."""
    submission = get_object_or_404(DatasetSubmission, pk=submission_id)
    
    # Published datasets are visible to everyone
    # Draft/submitted/under_review/revision only visible to owner or staff
    if submission.status != 'published':
        if not (request.user == submission.submitter or request.user.is_staff):
            raise Http404("No DatasetSubmission matches the given query.")
    
    return render(
        request,
        'data_submission/view_submission.html',
        {
            'submission': submission,
        }
    )


@login_required
def submission_success(request, submission_id):
    submission = get_object_or_404(DatasetSubmission, pk=submission_id, submitter=request.user)
    return render(request, 'data_submission/submission_success.html', {'submission': submission})


@login_required
def my_submissions(request):
    # Incomplete (Draft) Submissions
    incomplete_submissions = DatasetSubmission.objects.filter(
        submitter=request.user,
        status='draft'
    ).order_by('-submission_date')

    # Submitted & Published Submissions
    submitted_published_submissions = DatasetSubmission.objects.filter(
        submitter=request.user,
        status__in=['submitted', 'under_review', 'published', 'revision_requested']
    ).order_by('-submission_date')

    context = {
        'incomplete_submissions': incomplete_submissions,
        'submitted_published_submissions': submitted_published_submissions,
    }

    return render(request, 'data_submission/my_submissions.html', context)


@login_required
@user_passes_test(lambda u: is_admin(u) or is_expedition_admin(u))
def admin_dashboard(request):
    submissions = DatasetSubmission.objects.all()
    
    # Filter for Child Admins
    if not request.user.is_superuser:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.expedition_admin_type:
            submissions = submissions.filter(expedition_type=profile.expedition_admin_type)
            
    context = {
        'total_submissions': submissions.count(),
        'submitted': submissions.filter(status='submitted').count(),
        'published': submissions.filter(status='published').count(),
        'pending_submissions': submissions.filter(status='submitted').count(),
        'user_count': User.objects.count(),
        'recent_submissions': submissions.order_by('-submission_date')[:10],
    }

    # Render separate dashboard for Child Admins (Non-Superusers)
    if not request.user.is_superuser:
        return render(request, 'admin/child_admin_dashboard.html', context)

    return render(request, 'admin/dashboard.html', context)

def is_expedition_admin(user):
    return hasattr(user, 'profile') and bool(user.profile.expedition_admin_type)

@login_required
@user_passes_test(lambda u: is_reviewer(u) or is_admin(u) or is_expedition_admin(u))
def review_submissions(request):
    submissions = DatasetSubmission.objects.filter(
        status__in=['submitted', 'under_review']
    ).order_by('submission_date')

    # Filter for Child Admins
    if not request.user.is_superuser:
        profile = getattr(request.user, 'profile', None)
        # If user is ONLY an expedition admin (not superuser), filter:
        if profile and profile.expedition_admin_type:
            submissions = submissions.filter(expedition_type=profile.expedition_admin_type)
    
    return render(
        request,
        'admin/review_submissions.html',
        {'submissions': submissions}
    )


@login_required
@user_passes_test(lambda u: is_reviewer(u) or is_admin(u) or is_expedition_admin(u))
@require_http_methods(["GET", "POST"])
def review_submission_detail(request, submission_id):
    submission = get_object_or_404(DatasetSubmission, pk=submission_id)
    
    # 🚨 PERMISSION CHECK: Child Admins can only review their type
    if not request.user.is_superuser:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.expedition_admin_type:
            if submission.expedition_type != profile.expedition_admin_type:
                messages.error(request, "You are not authorized to review this submission.")
                return redirect('data_submission:review_submissions')
    
    # 🚨 STATUS TRANSITION VALIDATION
    STATUS_TRANSITIONS = {
        "draft": ["submitted"],
        "submitted": ["published"],
        "published": [],
    }

    if request.method == 'POST':
        status = request.POST.get('status')
        reviewer_notes = request.POST.get('reviewer_notes', '').strip()

        # 🚀 ENTERPRISE WORKFLOW VALIDATION
        if status not in STATUS_TRANSITIONS.get(submission.status, []):
            messages.error(request, f"Invalid status transition from {submission.status} to {status}.")
            return redirect(
                'data_submission:review_submission_detail',
                submission_id=submission.id
            )

        previous_status = submission.status
        
        submission.status = status
        submission.reviewer_notes = reviewer_notes
        
        # 🚀 AUDIT TRAIL: Track reviewer actions
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        submission.status_updated_at = timezone.now()
        
        submission.save()
        
        # 📧 EMAIL NOTIFICATION TO SUBMITTER
        try:
            if status == "published":
                send_mail(
                    f"[NPDC Portal] Database Published: {submission.title}",
                    f"""
Dear {submission.submitter.first_name},

We are pleased to inform you that your dataset submission has been reviewed and APPROVED. It is now published and publicly available in the National Polar Data Center repository.

Dataset Details:
----------------
Dataset ID: {submission.id}
Title: {submission.title}
Status: PUBLISHED
Publication Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

You can view your published dataset here:
{request.build_absolute_uri('/data/my-submissions/')}

Thank you for your contribution to the NPDC.

Best Regards,
NPDC Data Team
National Polar Data Center
                    """,
                    settings.DEFAULT_FROM_EMAIL,
                    [submission.submitter.email],
                    fail_silently=True,
                )
                
                logger.info(f"Publication notification sent for dataset {submission.id}")
                
        except Exception as e:
            logger.error(f"Failed to send status notification: {str(e)}")

        messages.success(request, "Submission reviewed successfully.")
        
        # Log the review action
        logger.info(f"User {request.user.id} changed dataset {submission.id} from {previous_status} to {status}")
        

        
        return redirect('data_submission:review_submissions')

    return render(
        request,
        'admin/review_submission_detail.html',
        {
            'submission': submission,
            'status_transitions': STATUS_TRANSITIONS.get(submission.status, [])
        }
    )


# =====================================================
# EDIT/DELETE VIEWS WITH ENTERPRISE RULES
# =====================================================

@login_required
@require_http_methods(["GET", "POST"])
def edit_dataset(request, submission_id):
    dataset = get_object_or_404(DatasetSubmission, pk=submission_id, submitter=request.user)
    
    # 🚨 LOCK EDITING BASED ON STATUS
    if dataset.status == "published":
        messages.error(request, "Cannot edit a published dataset.")
        return redirect("data_submission:my_submissions")
    
    return submit_dataset(request)


@login_required
@require_http_methods(["POST"])
def delete_dataset(request, submission_id):
    dataset = get_object_or_404(DatasetSubmission, pk=submission_id, submitter=request.user)
    
    # 🚨 PREVENT DELETION OF SUBMITTED/REVIEWED DATASETS
    if dataset.status not in ["draft"]:
        messages.error(request, "Cannot delete a dataset that has been submitted for review.")
        return redirect("data_submission:my_submissions")
    
    dataset.delete()
    messages.success(request, "Dataset deleted successfully.")
    
    # Log deletion
    logger.info(f"Dataset {submission_id} deleted by user {request.user.id}")


    
    return redirect("data_submission:my_submissions")


# =====================================================
# LOGGER SETUP
# =====================================================
logger = logging.getLogger(__name__)


# =====================================================
# AJAX VIEWS
# =====================================================

def load_states(request):
    """AJAX view to load states based on country code.
    First checks local database, then falls back to external API.
    """
    import requests
    from django_countries import countries
    
    country_code = request.GET.get('country', '').upper()
    
    if not country_code:
        return JsonResponse([], safe=False)
    
    # First, try local database
    states = State.objects.filter(country_code=country_code).order_by('name')
    if states.exists():
        return JsonResponse(list(states.values('id', 'name')), safe=False)
    
    # If not in database, fetch from external API
    try:
        # Get country name from code
        country_name = dict(countries).get(country_code, '')
        
        # Name mapping for CountriesNow API compatibility
        NAME_MAPPING = {
            "United States of America": "United States",
            "Korea, Republic of": "South Korea",
            "Taiwan, Province of China": "Taiwan",
            "Viet Nam": "Vietnam",
            "Bolivia, Plurinational State of": "Bolivia",
            "Venezuela, Bolivarian Republic of": "Venezuela",
            "Iran, Islamic Republic of": "Iran",
            "Tanzania, United Republic of": "Tanzania",
            "Moldova, Republic of": "Moldova",
            "Congo, The Democratic Republic of the": "Democratic Republic of the Congo",
            "Syrian Arab Republic": "Syria",
        }
        
        country_name = NAME_MAPPING.get(country_name, country_name)
        
        if country_name:
            # Use CountriesNow API to get states
            api_url = "https://countriesnow.space/api/v0.1/countries/states"
            response = requests.post(api_url, json={"country": country_name}, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('error') == False and data.get('data', {}).get('states'):
                    states_list = [
                        {'id': idx, 'name': state['name']} 
                        for idx, state in enumerate(data['data']['states'])
                    ]
                    return JsonResponse(states_list, safe=False)
    except Exception as e:
        logger.error(f"Error fetching states from API: {str(e)}")
    
    # Return empty list if nothing found
    return JsonResponse([], safe=False)


@login_required
def upload_dataset_files(request, submission_id):
    """
    Step 2: Upload files for the dataset submission.
    """
    dataset = get_object_or_404(DatasetSubmission, id=submission_id)
    
    # RBAC: Only submitter or admin can upload files
    if not (request.user == dataset.submitter or is_admin(request)):
        messages.error(request, "You do not have permission to edit this dataset.")
        return redirect('data_submission:my_submissions')
        
    if request.method == 'POST':
        from .forms import DatasetUploadForm
        form = DatasetUploadForm(request.POST, request.FILES, instance=dataset)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.status = 'submitted' # Finalize submission
            dataset.save()
            
            # 📧 EMAIL NOTIFICATION SYSTEM
            
            # 1. To ADMINS & REVIEWERS
            try:
                reviewers = User.objects.filter(groups__name="Reviewer")
                admins = User.objects.filter(is_superuser=True)
                
                reviewer_emails = list(reviewers.values_list("email", flat=True))
                admin_emails = list(admins.values_list("email", flat=True))
                all_emails = list(set(reviewer_emails + admin_emails))
                all_emails = [email for email in all_emails if email]
                
                if all_emails:
                    send_mail(
                        f"[NPDC Admin] New Dataset Submitted: {dataset.title}",
                        f"""
Dear Admin/Reviewer,

A new dataset has been submitted / resubmitted for review on the NPDC Portal.

Submission Details:
-------------------
Dataset ID: {dataset.id}
Title: {dataset.title}
Expedition: {dataset.get_expedition_type_display()}
Submitter: {request.user.get_full_name()} ({request.user.email})
Submission Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Please log in to the admin panel to review this submission:
{request.build_absolute_uri('/admin/review/')}

Best Regards,
NPDC Portal System
                        """,
                        settings.DEFAULT_FROM_EMAIL,
                        all_emails,
                        fail_silently=True,
                    )
                logger.info(f"Submission notification sent to admins for dataset {dataset.id}")
            except Exception as e:
                logger.error(f"Failed to send admin submission notification: {str(e)}")

            # 2. To USER (Confirmation)
            try:
                if request.user.email:
                    send_mail(
                        f"[NPDC Portal] Submission Received: {dataset.title}",
                        f"""
Dear {request.user.first_name},

This email verifies that your dataset submission has been successfully received by the National Polar Data Center (NPDC).

Submission Summary:
-------------------
Dataset ID: {dataset.id}
Title: {dataset.title}
Status: Submitted (Use 'My Submissions' to track status)
Date: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Our team will review your submission. You will receive further notifications regarding the approval or revision status of your dataset.

You can view your submission status here:
{request.build_absolute_uri('/data/my-submissions/')}

Best Regards,
NPDC Data Team
National Polar Data Center
                        """,
                        settings.DEFAULT_FROM_EMAIL,
                        [request.user.email],
                        fail_silently=True,
                    )
                logger.info(f"Submission confirmation sent to user {request.user.id}")
            except Exception as e:
                logger.error(f"Failed to send user submission confirmation: {str(e)}")
            

            
            messages.success(request, "Dataset submitted successfully with files!")
            return redirect('data_submission:submission_success', submission_id=dataset.id)
    else:
        from .forms import DatasetUploadForm
        form = DatasetUploadForm(instance=dataset)
        
    return render(request, 'data_submission/upload_files.html', {
        'form': form,
        'dataset': dataset
    })


# =====================================================
# AI-POWERED API ENDPOINTS
# =====================================================

@login_required
@require_post_method
def ai_classify_view(request):
    """API: AI auto-classify dataset into category, topic, ISO topic."""
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        abstract = data.get('abstract', '').strip()
        expedition_type = data.get('expedition_type', '').strip()

        if not title and not abstract:
            return JsonResponse({'error': 'Title or abstract is required.'}, status=400)

        result = classify_dataset(title, abstract, expedition_type)
        return JsonResponse({'status': 'ok', 'data': result})
    except Exception as e:
        logger.error(f"AI classify error: {e}")
        return JsonResponse({'error': 'AI classification failed.'}, status=500)


@login_required
@require_post_method
def ai_keywords_view(request):
    """API: AI suggest scientific keywords."""
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        abstract = data.get('abstract', '').strip()
        category = data.get('category', '').strip()

        if not title and not abstract:
            return JsonResponse({'error': 'Title or abstract is required.'}, status=400)

        keywords = suggest_keywords(title, abstract, category)
        return JsonResponse({'status': 'ok', 'keywords': keywords})
    except Exception as e:
        logger.error(f"AI keywords error: {e}")
        return JsonResponse({'error': 'AI keyword generation failed.'}, status=500)


@login_required
@require_post_method
def ai_check_abstract_view(request):
    """API: AI abstract quality checker."""
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        abstract = data.get('abstract', '').strip()
        expedition_type = data.get('expedition_type', '').strip()

        if not abstract:
            return JsonResponse({'error': 'Abstract is required.'}, status=400)

        result = check_abstract_quality(title, abstract, expedition_type)
        return JsonResponse({'status': 'ok', 'data': result})
    except Exception as e:
        logger.error(f"AI abstract check error: {e}")
        return JsonResponse({'error': 'AI quality check failed.'}, status=500)


@login_required
@require_post_method
def ai_extract_spatial_view(request):
    """API: AI extract/suggest spatial coordinates."""
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        abstract = data.get('abstract', '').strip()
        expedition_type = data.get('expedition_type', '').strip()

        if not title and not abstract:
            return JsonResponse({'error': 'Title or abstract is required.'}, status=400)

        result = extract_spatial_data(title, abstract, expedition_type)
        return JsonResponse({'status': 'ok', 'data': result})
    except Exception as e:
        logger.error(f"AI spatial extract error: {e}")
        return JsonResponse({'error': 'AI spatial extraction failed.'}, status=500)


@login_required
@require_post_method
def ai_prefill_view(request):
    """API: AI smart form pre-fill (combines classify + keywords + abstract check + spatial)."""
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        abstract = data.get('abstract', '').strip()
        expedition_type = data.get('expedition_type', '').strip()

        if not title and not abstract:
            return JsonResponse({'error': 'Title or abstract is required.'}, status=400)

        result = prefill_form(title, abstract, expedition_type)
        return JsonResponse({'status': 'ok', 'data': result})
    except Exception as e:
        logger.error(f"AI prefill error: {e}")
        return JsonResponse({'error': 'AI pre-fill failed.'}, status=500)


@login_required
@require_post_method
def ai_generate_title_view(request):
    """API: AI-powered dataset title generator from abstract."""
    try:
        data = json.loads(request.body)
        abstract = data.get('abstract', '').strip()
        expedition_type = data.get('expedition_type', '').strip()

        if not abstract:
            return JsonResponse({'error': 'Abstract is required to generate a title.'}, status=400)

        result = generate_title(abstract, expedition_type)
        return JsonResponse({'status': 'ok', 'data': result})
    except Exception as e:
        logger.error(f"AI generate title error: {e}")
        return JsonResponse({'error': 'AI title generation failed.'}, status=500)


@login_required
@require_post_method
def ai_generate_purpose_view(request):
    """API: AI-powered purpose statement generator from title + abstract."""
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        abstract = data.get('abstract', '').strip()
        expedition_type = data.get('expedition_type', '').strip()

        if not abstract:
            return JsonResponse({'error': 'Abstract is required to generate a purpose.'}, status=400)

        result = generate_purpose(title, abstract, expedition_type)
        return JsonResponse({'status': 'ok', 'data': result})
    except Exception as e:
        logger.error(f"AI generate purpose error: {e}")
        return JsonResponse({'error': 'AI purpose generation failed.'}, status=500)


@login_required
@require_post_method
def ai_suggest_resolution_view(request):
    """API: AI-powered data resolution suggester."""
    try:
        data = json.loads(request.body)
        title = data.get('title', '').strip()
        abstract = data.get('abstract', '').strip()
        expedition_type = data.get('expedition_type', '').strip()

        if not abstract:
            return JsonResponse({'error': 'Abstract is required to suggest resolution.'}, status=400)

        result = suggest_resolution(title, abstract, expedition_type)
        if 'error' in result:
            return JsonResponse({'error': result['error']}, status=400)
        return JsonResponse({'status': 'ok', 'data': result})
    except Exception as e:
        logger.error(f"AI suggest resolution error: {e}")
        return JsonResponse({'error': 'AI resolution suggestion failed.'}, status=500)


@login_required
@require_post_method
def ai_review_assist_view(request):
    """API: AI reviewer assistant for submission review."""
    try:
        data = json.loads(request.body)
        submission_id = data.get('submission_id')

        if not submission_id:
            return JsonResponse({'error': 'Submission ID is required.'}, status=400)

        submission = DatasetSubmission.objects.get(id=submission_id)

        # Build submission data dict for AI analysis
        submission_data = {
            'id': submission.id,
            'title': submission.title,
            'abstract': submission.abstract,
            'purpose': submission.purpose,
            'expedition_type': submission.get_expedition_type_display(),
            'category': submission.get_category_display(),
            'iso_topic': submission.get_iso_topic_display(),
            'keywords': submission.keywords,
            'temporal_start': str(submission.temporal_start_date) if submission.temporal_start_date else '',
            'temporal_end': str(submission.temporal_end_date) if submission.temporal_end_date else '',
            'north_lat': submission.north_latitude,
            'south_lat': submission.south_latitude,
            'east_lon': submission.east_longitude,
            'west_lon': submission.west_longitude,
            'progress': submission.get_data_set_progress_display(),
            'has_file': bool(submission.data_file),
        }

        result = generate_review_notes(submission_data)
        return JsonResponse({'status': 'ok', 'data': result})
    except DatasetSubmission.DoesNotExist:
        return JsonResponse({'error': 'Submission not found.'}, status=404)
    except Exception as e:
        logger.error(f"AI review assist error: {e}")
        return JsonResponse({'error': 'AI review failed.'}, status=500)


@login_required
@user_passes_test(lambda u: is_admin(u) or is_expedition_admin(u))
def admin_edit_submission(request, submission_id):
    """
    View for Admins (Super & Child) to edit a submission.
    """
    submission = get_object_or_404(DatasetSubmission, pk=submission_id)

    # 🚨 PERMISSION CHECK: Child Admins can only edit their type
    if not request.user.is_superuser:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.expedition_admin_type:
            if submission.expedition_type != profile.expedition_admin_type:
                messages.error(request, "You are not authorized to edit this submission.")
                return redirect('data_submission:review_submissions')

    if request.method == "POST":
        dataset_form = DatasetSubmissionForm(request.POST, request.FILES, instance=submission)
        
        # Related forms
        citation_instance = getattr(submission, 'citation', None)
        platform_instance = getattr(submission, 'platform', None)
        gps_instance = getattr(submission, 'gps', None)
        location_instance = getattr(submission, 'location', None)
        resolution_instance = getattr(submission, 'resolution', None)
        paleo_instance = getattr(submission, 'paleo_temporal', None)
        
        citation_form = DatasetCitationForm(request.POST, instance=citation_instance)
        platform_form = PlatformMetadataForm(request.POST, instance=platform_instance)
        gps_form = GPSMetadataForm(request.POST, instance=gps_instance)
        location_form = LocationMetadataForm(request.POST, instance=location_instance)
        resolution_form = DataResolutionMetadataForm(request.POST, instance=resolution_instance)
        
        if gps_instance and gps_instance.gps_used:
            paleo_form = PaleoTemporalCoverageForm(request.POST, instance=paleo_instance)
        else:
            paleo_form = PaleoTemporalCoverageForm(request.POST, instance=paleo_instance)
            
        scientist_formset = ScientistFormSet(request.POST, instance=submission)
        instrument_formset = InstrumentFormSet(request.POST, instance=submission)

        if all([dataset_form.is_valid(), citation_form.is_valid(), platform_form.is_valid(), 
                location_form.is_valid(), resolution_form.is_valid(), scientist_formset.is_valid(), 
                instrument_formset.is_valid(), gps_form.is_valid(), paleo_form.is_valid()]):
            
            with transaction.atomic():
                submission = dataset_form.save()
                
                # Logic to keep status or update? 
                # Ideally, admin editing shouldn't reset to draft unless specified.
                # We keep the status as is.
                submission.status_updated_at = timezone.now()
                submission.save()
                
                citation_form.save()
                platform_form.save()
                gps_form.save()
                location_form.save()
                resolution_form.save()
                if paleo_form.is_bound: # Only save if we bounded it
                     paleo_form.save()
                
                scientist_formset.save()
                instrument_formset.save()
                
                messages.success(request, f"Submission {submission.id} updated successfully.")
                return redirect("data_submission:review_submission_detail", submission_id=submission.id)
        else:
             messages.error(request, "Please correct the errors below.")
    else:
        # GET - Populate forms with instance data
        dataset_form = DatasetSubmissionForm(instance=submission)
        citation_form = DatasetCitationForm(instance=getattr(submission, 'citation', None))
        platform_form = PlatformMetadataForm(instance=getattr(submission, 'platform', None))
        gps_form = GPSMetadataForm(instance=getattr(submission, 'gps', None))
        location_form = LocationMetadataForm(instance=getattr(submission, 'location', None))
        resolution_form = DataResolutionMetadataForm(instance=getattr(submission, 'resolution', None))
        paleo_form = PaleoTemporalCoverageForm(instance=getattr(submission, 'paleo_temporal', None))
        
        scientist_formset = ScientistFormSet(instance=submission)
        instrument_formset = InstrumentFormSet(instance=submission)

    return render(
        request,
        "data_submission/submit_dataset.html",
        {
            "dataset_form": dataset_form,
            "citation_form": citation_form,
            "platform_form": platform_form,
            "gps_form": gps_form,
            "location_form": location_form,
            "resolution_form": resolution_form,
            "scientist_formset": scientist_formset,
            "instrument_formset": instrument_formset,
            "paleo_form": paleo_form,
            "is_edit_mode": True,
            "is_admin_edit": True, # Flag for template to adjust UI (e.g. hide 'Save Draft' if needed)
            "dataset_id": submission.id,
        },
    )