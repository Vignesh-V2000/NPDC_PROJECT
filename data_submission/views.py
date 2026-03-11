from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User, Group
from django.forms import inlineformset_factory
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.http import Http404, FileResponse, HttpResponse
from django.utils import timezone
from datetime import timedelta, datetime
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.core.cache import cache
from django.db.models import Q, Count
import hashlib
import json
import logging
import mimetypes
import os
import threading

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
    check_ai_rate_limit,
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

def get_location_from_ip(ip_address):
    """
    Get location information from IP address using ip-api.com
    Returns: "City, Country" or full location string or empty if lookup fails
    """
    if not ip_address or ip_address == '127.0.0.1':
        return "Local/Unknown"
    
    try:
        import requests
        import json
        
        url = f'http://ip-api.com/json/{ip_address}'
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                city = data.get('city', '')
                region = data.get('regionName', '')
                country = data.get('country', '')
                
                # Build location string
                parts = []
                if city:
                    parts.append(city)
                if region and region != city:
                    parts.append(region)
                if country:
                    parts.append(country)
                
                location = ', '.join(parts) if parts else 'Unknown Location'
                return location
    except Exception as e:
        # Log the exception but don't fail the request
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error getting location for IP {ip_address}: {str(e)}")
    
    return "Unknown Location"

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

ScientistFormSetEdit = inlineformset_factory(
    DatasetSubmission,
    ScientistDetail,
    form=ScientistDetailForm,
    extra=0,
    can_delete=True
)

InstrumentFormSetEdit = inlineformset_factory(
    DatasetSubmission,
    InstrumentMetadata,
    form=InstrumentMetadataForm,
    extra=0,
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

    # Dynamically define formsets to prevent empty "extra" forms when editing
    scientist_extra = 0 if (dataset and dataset.scientists.exists()) else 1
    instrument_extra = 0 if (dataset and dataset.instruments.exists()) else 1

    LocalScientistFormSet = inlineformset_factory(
        DatasetSubmission, ScientistDetail, form=ScientistDetailForm, extra=scientist_extra, can_delete=True
    )
    LocalInstrumentFormSet = inlineformset_factory(
        DatasetSubmission, InstrumentMetadata, form=InstrumentMetadataForm, extra=instrument_extra, can_delete=True
    )

    
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
                
            scientist_formset = LocalScientistFormSet(request.POST, instance=dataset)
            instrument_formset = LocalInstrumentFormSet(request.POST, instance=dataset)
        else:
            dataset_form = DatasetSubmissionForm(request.POST, request.FILES)
            citation_form = DatasetCitationForm(request.POST)
            platform_form = PlatformMetadataForm(request.POST)
            gps_form = GPSMetadataForm(request.POST)
            location_form = LocationMetadataForm(request.POST)
            resolution_form = DataResolutionMetadataForm(request.POST)
            paleo_form = PaleoTemporalCoverageForm(request.POST)
            scientist_formset = LocalScientistFormSet(request.POST)
            instrument_formset = LocalInstrumentFormSet(request.POST)

        # Determine the action early
        action = request.POST.get("save")

        # ═══ SAVE AS DRAFT — Relaxed Validation ═══
        if action == "DRAFT":
            # For drafts, require at least a title
            title_value = request.POST.get("title", "").strip()
            if not title_value:
                messages.error(request, "Please enter at least a Title before saving as draft.")
                # Re-render the form with the error
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
                        "dataset_id": dataset.metadata_id if dataset else None,
                    },
                )

            with transaction.atomic():
                if dataset:
                    # Update existing dataset
                    for field in dataset_form.fields:
                        if field in request.POST:
                            val = request.POST.get(field, "").strip()
                            if val == "" and field in ['temporal_start_date', 'temporal_end_date', 'dif_creation_date', 'last_dif_revision_date', 'future_dif_review_date']:
                                val = None
                            try:
                                setattr(dataset, field, val)
                            except Exception:
                                pass
                    dataset.title = title_value
                    dataset.status = "draft"
                else:
                    # Create new draft dataset
                    dataset = DatasetSubmission()
                    dataset.submitter = request.user
                    dataset.title = title_value
                    dataset.status = "draft"
                    
                    # Save simple text fields from POST data
                    simple_fields = [
                        'expedition_type', 'abstract', 'purpose', 'version',
                        'category', 'topic', 'iso_topic', 'keywords',
                        'expedition_year', 'expedition_number',
                        'project_number', 'project_name',
                        'temporal_start_date', 'temporal_end_date',
                        'data_type', 'collection_progress',
                    ]
                    for field in simple_fields:
                        val = request.POST.get(field, "").strip()
                        if val:
                            try:
                                setattr(dataset, field, val)
                            except Exception:
                                pass
                        elif field in ['temporal_start_date', 'temporal_end_date']:
                            try:
                                setattr(dataset, field, None)
                            except Exception:
                                pass

                # Auto-populate contact details
                if not dataset.contact_person:
                    dataset.contact_person = request.user.get_full_name() or request.user.username
                if not dataset.contact_email:
                    dataset.contact_email = request.user.email
                if not dataset.contact_phone:
                    dataset.contact_phone = ""

                dataset.save()

                # Try to save related forms even if not fully valid (draft mode)
                # Citation
                try:
                    for f in citation_form.fields.values(): f.required = False
                    if citation_form.is_valid():
                        citation = citation_form.save(commit=False)
                        citation.dataset = dataset
                        citation.save()
                except Exception as e:
                    print(f"Draft: Citation save skipped: {e}")
                # Platform
                try:
                    for f in platform_form.fields.values(): f.required = False
                    if platform_form.is_valid():
                        platform = platform_form.save(commit=False)
                        platform.dataset = dataset
                        platform.save()
                except Exception as e:
                    print(f"Draft: Platform save skipped: {e}")
                # GPS
                try:
                    for f in gps_form.fields.values(): f.required = False
                    if gps_form.is_valid():
                        gps = gps_form.save(commit=False)
                        gps.dataset = dataset
                        gps.save()
                except Exception as e:
                    print(f"Draft: GPS save skipped: {e}")
                # Location
                try:
                    for f in location_form.fields.values(): f.required = False
                    if location_form.is_valid():
                        location = location_form.save(commit=False)
                        # Auto-set category from expedition type
                        expedition_map = {
                            "antarctic": ("region", "Antarctica"),
                            "arctic": ("region", "Arctic"),
                            "southern_ocean": ("ocean", "Southern Ocean"),
                            "himalaya": ("region", "Himalaya"),
                        }
                        exp_type = request.POST.get('expedition_type', '')
                        if exp_type in expedition_map:
                            cat, loc_type = expedition_map[exp_type]
                            location.location_category = cat
                            location.location_type = loc_type
                        else:
                            location.location_category = request.POST.get('location_category', 'region')
                            location.location_type = request.POST.get('location-location_type', '')
                        location.dataset = dataset
                        location.save()
                except Exception as e:
                    print(f"Draft: Location save skipped: {e}")
                # Resolution
                try:
                    for f in resolution_form.fields.values(): f.required = False
                    if resolution_form.is_valid():
                        resolution = resolution_form.save(commit=False)
                        resolution.dataset = dataset
                        resolution.save()
                except Exception as e:
                    print(f"Draft: Resolution save skipped: {e}")
                # Paleo
                try:
                    for f in paleo_form.fields.values(): f.required = False
                    if paleo_form.is_valid() and any(paleo_form.cleaned_data.values()):
                        paleo = paleo_form.save(commit=False)
                        paleo.dataset = dataset
                        paleo.save()
                except Exception as e:
                    print(f"Draft: Paleo save skipped: {e}")
                # Scientists
                try:
                    for form in scientist_formset.forms:
                        for f in form.fields.values(): f.required = False
                    if scientist_formset.is_valid():
                        scientist_formset.instance = dataset
                        scientist_formset.save()
                except Exception as e:
                    print(f"Draft: Scientist save skipped: {e}")
                # Instruments
                try:
                    for form in instrument_formset.forms:
                        for f in form.fields.values(): f.required = False
                    if instrument_formset.is_valid():
                        instrument_formset.instance = dataset
                        instrument_formset.save()
                except Exception as e:
                    print(f"Draft: Instrument save skipped: {e}")

            messages.success(request, f"Draft saved successfully! You can continue editing it from your submissions.")
            return redirect("data_submission:my_submissions")

        # ═══ STANDARD VALIDATION (NEXT / PREVIEW / SUBMIT) ═══
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

                if action == "SAVE" or action == "PREVIEW" or not action:
                    # If it's a new dataset or already a draft/revision, it stays draft.
                    # BUT if it's already submitted, under_review, or published, 
                    # we should NOT downgrade it to draft just because they clicked "Save & Next".
                    if not previous_status or previous_status in ["draft", "revision_requested", "revision"]:
                        dataset.status = "draft"
                    else:
                        # Keep the existing status
                        dataset.status = previous_status
                elif action == "SUBMIT":
                    # Allow re-submission from draft, submitted, revision_requested, AND published
                    if previous_status not in ["draft", "submitted", "revision_requested", "published"]:
                        messages.error(request, "Invalid status transition.")
                        return redirect("data_submission:submit_dataset")
                    
                    dataset.status = 'submitted'
                    dataset.save()
                    
                    messages.success(request, "Dataset submitted successfully!")
                    return redirect("data_submission:my_submissions")

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
                


            logger.info(f"Dataset {dataset.metadata_id} {'submitted' if dataset.status == 'submitted' else 'saved'} by user {request.user.id}")

            # 🚀 REDIRECT TO FILE UPLOAD STEP
            return redirect("data_submission:upload_dataset_files", metadata_id=dataset.metadata_id)

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
                
            scientist_formset = LocalScientistFormSet(instance=dataset)
            instrument_formset = LocalInstrumentFormSet(instance=dataset)
        else:
            dataset_form = DatasetSubmissionForm()
            citation_form = DatasetCitationForm()
            platform_form = PlatformMetadataForm()
            gps_form = GPSMetadataForm()
            location_form = LocationMetadataForm()
            resolution_form = DataResolutionMetadataForm()
            paleo_form = PaleoTemporalCoverageForm()
            scientist_formset = LocalScientistFormSet()
            instrument_formset = LocalInstrumentFormSet()

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
            "dataset_id": dataset.metadata_id if dataset else None,
        },
    )

def view_submission(request, metadata_id):
    """Read-only view for users to see submission details.
    Published datasets are visible to any logged-in user.
    Draft/submitted/under_review/revision only visible to owner or staff."""
    

    from django.contrib import messages

    # Try to get by metadata_id first
    try:
        submission = DatasetSubmission.objects.get(metadata_id=metadata_id)
    except DatasetSubmission.DoesNotExist:
        # If not found and metadata_id looks like a number, try to find by primary key
        if metadata_id.isdigit():
            try:
                submission = DatasetSubmission.objects.get(id=int(metadata_id))
                return redirect('data_submission:view_submission', metadata_id=submission.metadata_id)
            except (DatasetSubmission.DoesNotExist, ValueError):
                messages.error(request, "The requested dataset could not be found.")
                return redirect('users:home')
        else:
            messages.error(request, "The requested dataset could not be found.")
            return redirect('users:home')
    
    # Published datasets are visible to everyone
    # Draft/submitted/under_review/revision only visible to owner or staff
    if submission.status != 'published':
        if not (request.user == submission.submitter or request.user.is_staff):
            messages.error(request, "You do not have permission to view this dataset.")
            return redirect('users:home')
    
    return render(
        request,
        'data_submission/view_submission.html',
        {
            'submission': submission,
        }
    )

def export_submission_xml(request, metadata_id):
    """View to export submission details as XML."""
    
    # Try to get by metadata_id first
    try:
        submission = DatasetSubmission.objects.get(metadata_id=metadata_id)
    except DatasetSubmission.DoesNotExist:
        # If not found and metadata_id looks like a number, try to find by primary key
        if metadata_id.isdigit():
            try:
                submission = DatasetSubmission.objects.get(id=int(metadata_id))
                # Redirect to the correct URL with metadata_id

                return redirect('data_submission:export_submission_xml', metadata_id=submission.metadata_id)
            except (DatasetSubmission.DoesNotExist, ValueError):
                raise Http404("No DatasetSubmission matches the given query.")
        else:
            raise Http404("No DatasetSubmission matches the given query.")
    
    # Check permissions
    if submission.status != 'published':
        if not (request.user.is_authenticated and (request.user == submission.submitter or request.user.is_staff)):
            raise Http404("No DatasetSubmission matches the given query.")
            
    from django.core import serializers
    from django.http import HttpResponse
    
    xml_data = serializers.serialize('xml', [submission])
    return HttpResponse(xml_data, content_type="application/xml")



def get_data_view(request, metadata_id):
    """View for the Get Data request form.

    When the form is submitted we **log** the request (for admins to review) and
    immediately email the user the dataset PDF (and optionally cc superusers).
    The previous approval/rejection flow has been removed.
    """
    # Try to get by metadata_id first
    try:
        submission = DatasetSubmission.objects.get(metadata_id=metadata_id)
    except DatasetSubmission.DoesNotExist:
        # If not found and metadata_id looks like a number, try to find by primary key
        if metadata_id.isdigit():
            try:
                submission = DatasetSubmission.objects.get(id=int(metadata_id))
                # Redirect to the correct URL with metadata_id
                return redirect('data_submission:get_data', metadata_id=submission.metadata_id)
            except (DatasetSubmission.DoesNotExist, ValueError):
                raise Http404("No DatasetSubmission matches the given query.")
        else:
            raise Http404("No DatasetSubmission matches the given query.")
    
    from .forms import DatasetRequestForm  # Import the form locally

    form = None
    if request.method == "POST":
        form = DatasetRequestForm(request.POST)
        if form.is_valid():
            dataset_request = form.save(commit=False)
            dataset_request.dataset = submission
            if request.user.is_authenticated:
                dataset_request.requester = request.user
            
            # Capture IP address and location
            dataset_request.request_ip = get_client_ip(request)
            dataset_request.request_location = get_location_from_ip(dataset_request.request_ip)
            
            dataset_request.save()

            # ── Auto-trigger: pre-cache popular datasets ──────────────
            from .models import DatasetRequest
            trigger_every = getattr(settings, 'PRECACHE_TRIGGER_EVERY', 20)
            total_requests = DatasetRequest.objects.count()
            if total_requests % trigger_every == 0:
                threading.Thread(
                    target=precache_popular_datasets,
                    daemon=True
                ).start()
                logger.info(f"PRE-CACHE triggered at {total_requests} total downloads")

            # fire off email notifications (separate function makes testing easier)
            send_dataset_request_email(dataset_request, request)

            # Redirect to success page
            return redirect('data_submission:get_data_success', metadata_id=submission.metadata_id)
    else:
        # pre-fill the name/email fields for logged-in users
        if request.user.is_authenticated:
            form = DatasetRequestForm(initial={
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
            })
        else:
            form = DatasetRequestForm()

    # Render the form (GET or invalid POST)
    return render(
        request,
        'data_submission/get_data.html',
        {
            'submission': submission,
            'form': form,
        }
    )


def send_dataset_request_email(dataset_request, request):
    """Compose and send email when a dataset request is created.

    """
    submission = dataset_request.dataset
    subject = f"NPDC Dataset Request: {submission.metadata_id}"

    temp_range = ""
    if submission.temporal_start_date and submission.temporal_end_date:
        temp_range = f"{submission.temporal_start_date} - {submission.temporal_end_date}"
    elif submission.temporal_start_date:
        temp_range = str(submission.temporal_start_date)
    elif submission.temporal_end_date:
        temp_range = str(submission.temporal_end_date)

    file_name = None
    download_url = None
    if submission.data_file:
        file_name = os.path.basename(submission.data_file.name)
        # Use the cached download view URL instead of direct media URL
        from django.urls import reverse
        cached_download_path = reverse('data_submission:download_dataset', args=[submission.metadata_id])
        download_url = request.build_absolute_uri(cached_download_path)
    else:
        try:
            if hasattr(submission, 'citation') and submission.citation and submission.citation.online_resource:
                file_name = "External Dataset Link"
                download_url = submission.citation.online_resource
        except Exception:
            pass

    body_lines = [
        f"Dear {dataset_request.first_name} {dataset_request.last_name},",
        "",
        "The requested datasets are available for download:",
        "",
        f"Dataset: {submission.metadata_id} | {submission.title}" +
            (f" | {temp_range}" if temp_range else ""),
        "",
    ]
    if file_name:
        body_lines.append(file_name)
        if download_url:
            body_lines.append(f"Please click on above file to download: {download_url}")
        body_lines.append("")
    else:
        body_lines.append("No data file is currently attached; please contact the administrator if you believe this is an error.")
        body_lines.append("")

    body_lines.extend([
        "Please note the following:-",
        "The datasets must be formally cited as the National Polar Data Center, including the URL (https://npdc.ncpor.res.in/), in any scientific publication that utilizes or incorporates these datasets.",
        "The datasets should not be shared with others, however, the NPDC URL (https://npdc.ncpor.res.in/) may be shared for the purpose of downloading the datasets.",
        "",
        "Sincerely,",
        "",
        "PDSS Team",
        "National Polar Data Center",
        "https://npdc.ncpor.res.in",
        "",
        "Note: This is a system generated mail. Please do not reply to this mail",
    ])

    message = "\n".join(body_lines)
    admin_emails = list(User.objects.filter(is_superuser=True).values_list('email', flat=True))

    mail = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[dataset_request.email],
        cc=admin_emails,
    )

    if submission.data_file:
        try:
            mail.attach_file(submission.data_file.path)
        except Exception:
            pass

    try:
        mail.send()
    except Exception as e:
        print(f"Failed to send dataset email: {e}")

    # helper does not render anything; the caller handles responses
    # return value intentionally omitted


def download_dataset(request, metadata_id):
    """Cached download view for dataset files.

    Instead of serving files directly from /media/ (which reads from disk
    every single time), this view caches the file content using Django's
    cache framework.  On subsequent requests for the same file, the
    cached bytes are served immediately — saving disk I/O and speeding
    up downloads for popular datasets.

    Flow:
      1st request → read from disk → store in cache → serve to user
      2nd request → serve from cache (disk never touched)
    """
    # ── Look up the dataset ──────────────────────────────────────────
    try:
        submission = DatasetSubmission.objects.get(metadata_id=metadata_id)
    except DatasetSubmission.DoesNotExist:
        if metadata_id.isdigit():
            try:
                submission = DatasetSubmission.objects.get(id=int(metadata_id))
                return redirect('data_submission:download_dataset',
                                metadata_id=submission.metadata_id)
            except (DatasetSubmission.DoesNotExist, ValueError):
                raise Http404("Dataset not found.")
        raise Http404("Dataset not found.")

    # ── Make sure there is a file to download ────────────────────────
    if not submission.data_file:
        raise Http404("No data file attached to this dataset.")

    # ── Build a unique cache key for this file ───────────────────────
    file_path = submission.data_file.path
    file_name = os.path.basename(submission.data_file.name)

    # Include file modification time so the cache auto-invalidates
    # when the file is replaced with a new upload.
    try:
        mtime = os.path.getmtime(file_path)
    except OSError:
        raise Http404("Data file not found on disk.")

    cache_key = f"download_{metadata_id}_{mtime}"

    # ── Try the cache first ──────────────────────────────────────────
    cached_data = cache.get(cache_key)

    if cached_data is not None:
        # Cache HIT — serve from cache, skip disk entirely
        file_bytes, content_type, etag = cached_data
        logger.info(f"CACHE HIT for dataset {metadata_id}")
    else:
        # Cache MISS — read from disk and store in cache
        try:
            with open(file_path, 'rb') as f:
                file_bytes = f.read()
        except OSError:
            raise Http404("Data file not found on disk.")

        content_type, _ = mimetypes.guess_type(file_name)
        content_type = content_type or 'application/octet-stream'

        # Generate an ETag for browser-side caching
        etag = hashlib.md5(f"{metadata_id}:{mtime}".encode()).hexdigest()

        # Cache timeout: 1 hour (3600 seconds)
        # For large files (>50 MB), skip caching to avoid memory pressure
        file_size_mb = len(file_bytes) / (1024 * 1024)
        cache_timeout = getattr(settings, 'DOWNLOAD_CACHE_TIMEOUT', 3600)
        max_cacheable_mb = getattr(settings, 'DOWNLOAD_CACHE_MAX_SIZE_MB', 50)

        if file_size_mb <= max_cacheable_mb:
            cache.set(cache_key, (file_bytes, content_type, etag), cache_timeout)
            logger.info(f"CACHE MISS → cached dataset {metadata_id} ({file_size_mb:.1f} MB)")
        else:
            logger.info(f"CACHE SKIP — dataset {metadata_id} too large ({file_size_mb:.1f} MB)")

    # ── Check ETag for 304 Not Modified (browser already has it) ─────
    if_none_match = request.META.get('HTTP_IF_NONE_MATCH', '')
    if if_none_match and if_none_match.strip('"') == etag:
        response = HttpResponse(status=304)
        response['ETag'] = f'"{etag}"'
        return response

    # ── Serve the file ───────────────────────────────────────────────
    response = HttpResponse(file_bytes, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    response['Content-Length'] = len(file_bytes)
    response['ETag'] = f'"{etag}"'
    response['Cache-Control'] = 'public, max-age=3600'  # Browser caches for 1 hour
    return response


def precache_popular_datasets():
    """Pre-cache the most frequently downloaded dataset files.

    Runs in a background thread, triggered every Nth download request.
    Finds the top N most-downloaded datasets in the last X days and
    loads their files into the cache — so the next user to hit
    /data/download/<id>/ gets an instant CACHE HIT.

    Uses the SAME cache key pattern as download_dataset(), so hits are
    seamless.
    """
    from .models import DatasetRequest

    top_n = getattr(settings, 'PRECACHE_TOP_N', 10)
    lookback_days = getattr(settings, 'PRECACHE_LOOKBACK_DAYS', 7)
    cache_timeout = getattr(settings, 'DOWNLOAD_CACHE_TIMEOUT', 43200)
    max_cacheable_mb = getattr(settings, 'DOWNLOAD_CACHE_MAX_SIZE_MB', 50)

    cutoff = timezone.now() - timedelta(days=lookback_days)

    # Find the top N most downloaded datasets in the lookback window
    popular = (
        DatasetRequest.objects
        .filter(request_date__gte=cutoff)
        .values('dataset__metadata_id', 'dataset_id')
        .annotate(download_count=Count('id'))
        .order_by('-download_count')[:top_n]
    )

    cached_count = 0
    for entry in popular:
        try:
            dataset = DatasetSubmission.objects.get(id=entry['dataset_id'])
            if not dataset.data_file:
                continue

            file_path = dataset.data_file.path
            metadata_id = dataset.metadata_id

            try:
                mtime = os.path.getmtime(file_path)
            except OSError:
                continue

            cache_key = f"download_{metadata_id}_{mtime}"

            # Skip if already cached
            if cache.get(cache_key) is not None:
                continue

            # Read and cache
            try:
                with open(file_path, 'rb') as f:
                    file_bytes = f.read()
            except OSError:
                continue

            file_size_mb = len(file_bytes) / (1024 * 1024)
            if file_size_mb > max_cacheable_mb:
                logger.info(f"PRE-CACHE SKIP — {metadata_id} too large ({file_size_mb:.1f} MB)")
                continue

            file_name = os.path.basename(dataset.data_file.name)
            content_type, _ = mimetypes.guess_type(file_name)
            content_type = content_type or 'application/octet-stream'
            etag = hashlib.md5(f"{metadata_id}:{mtime}".encode()).hexdigest()

            cache.set(cache_key, (file_bytes, content_type, etag), cache_timeout)
            cached_count += 1
            logger.info(
                f"PRE-CACHED {metadata_id} ({file_size_mb:.1f} MB, "
                f"{entry['download_count']} downloads in {lookback_days}d)"
            )

        except DatasetSubmission.DoesNotExist:
            continue
        except Exception as e:
            logger.error(f"PRE-CACHE ERROR for dataset {entry.get('dataset_id')}: {e}")
            continue

    logger.info(f"PRE-CACHE complete: {cached_count} datasets pre-cached")

def get_data_success_view(request, metadata_id):
    """View for the Get Data success message."""
    
    # Try to get by metadata_id first
    try:
        submission = DatasetSubmission.objects.get(metadata_id=metadata_id)
    except DatasetSubmission.DoesNotExist:
        # If not found and metadata_id looks like a number, try to find by primary key
        if metadata_id.isdigit():
            try:
                submission = DatasetSubmission.objects.get(id=int(metadata_id))
                # Redirect to the correct URL with metadata_id

                return redirect('data_submission:get_data_success', metadata_id=submission.metadata_id)
            except (DatasetSubmission.DoesNotExist, ValueError):
                raise Http404("No DatasetSubmission matches the given query.")
        else:
            raise Http404("No DatasetSubmission matches the given query.")
    
    return render(
        request,
        'data_submission/get_data_success.html',
        {
            'submission': submission,
        }
    )

@login_required
def submission_success(request, metadata_id):
    
    # Try to get by metadata_id first
    try:
        submission = DatasetSubmission.objects.get(metadata_id=metadata_id)
    except DatasetSubmission.DoesNotExist:
        # If not found and metadata_id looks like a number, try to find by primary key
        if metadata_id.isdigit():
            try:
                submission = DatasetSubmission.objects.get(id=int(metadata_id))
                return redirect('data_submission:submission_success', metadata_id=submission.metadata_id)
            except (DatasetSubmission.DoesNotExist, ValueError):
                raise Http404("No DatasetSubmission matches the given query.")
        else:
            raise Http404("No DatasetSubmission matches the given query.")
    
    # Only submitter or admin can view success page
    if not (request.user == submission.submitter or is_admin(request.user)):
        raise Http404("No DatasetSubmission matches the given query.")
    
    return render(request, 'data_submission/submission_success.html', {'submission': submission})


@login_required
def my_submissions(request):
    # 1. Saved / Draft Metadata (exclude legacy datasets tagged in keywords)
    draft_submissions = DatasetSubmission.objects.filter(
        submitter=request.user,
        status='draft'
    ).exclude(
        keywords__contains='legacy_id:'
    ).order_by('-submission_date')

    # 2. Submitted (includes under_review, revision_requested)
    submitted_submissions = DatasetSubmission.objects.filter(
        submitter=request.user,
        status__in=['submitted', 'under_review', 'revision_requested']
    ).order_by('-submission_date')

    # 3. Published
    published_submissions = DatasetSubmission.objects.filter(
        submitter=request.user,
        status='published'
    ).order_by('-submission_date')

    context = {
        'incomplete_submissions': draft_submissions,
        'submitted_submissions': submitted_submissions,
        'published_submissions': published_submissions,
    }

    return render(request, 'data_submission/my_submissions.html', context)


@login_required
@user_passes_test(lambda u: is_admin(u) or is_expedition_admin(u))
def admin_dashboard(request):
    submissions = DatasetSubmission.objects.all()
    
    # Check if user is an expedition admin (child admin)
    profile = getattr(request.user, 'profile', None)
    is_expedition = profile and profile.expedition_admin_type
    
    # Filter submissions for Expedition Admins only
    if is_expedition:
        submissions = submissions.filter(expedition_type=profile.expedition_admin_type)
            
    context = {
        'total_submissions': submissions.count(),
        'submitted': submissions.filter(status='submitted').count(),
        'published': submissions.filter(status='published').count(),
        'pending_submissions': submissions.filter(status='submitted').count(),
        'rejected_submissions': submissions.filter(status='revision').count(),
        'user_count': User.objects.count(),
        'recent_submissions': submissions.order_by('-submission_date')[:10],
    }

    # Render the main premium dashboard for all admin types (data is already filtered above)
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
            
    # GET Filters
    query = request.GET.get('q', '').strip()
    expedition = request.GET.get('expedition', '').strip()
    category = request.GET.get('category', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if query:
        submissions = submissions.filter(
            Q(title__icontains=query) |
            Q(abstract__icontains=query) |
            Q(metadata_id__icontains=query) |
            Q(submitter__first_name__icontains=query) |
            Q(submitter__last_name__icontains=query) |
            Q(submitter__email__icontains=query)
        )
    if expedition:
        submissions = submissions.filter(expedition_type=expedition)
    if category:
        submissions = submissions.filter(category=category)
    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            submissions = submissions.filter(submission_date__date__gte=parsed_start)
        except ValueError:
            pass
    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            submissions = submissions.filter(submission_date__date__lte=parsed_end)
        except ValueError:
            pass
    
    # Context items needed for the frontend filter UI
    expedition_choices = DatasetSubmission.EXPEDITION_TYPES
    category_choices = DatasetSubmission.CATEGORY_CHOICES
    
    return render(
        request,
        'admin/review_submissions.html',
        {
            'submissions': submissions,
            'current_q': query,
            'current_expedition': expedition,
            'current_category': category,
            'current_start_date': start_date,
            'current_end_date': end_date,
            'expedition_choices': expedition_choices,
            'category_choices': category_choices,
        }
    )


@login_required
@user_passes_test(lambda u: is_reviewer(u) or is_admin(u) or is_expedition_admin(u))
def all_submissions(request):
    """View to see all datasets (Published, Draft, Pending) with correct expedition filtering."""
    submissions_list = DatasetSubmission.objects.all().order_by('-submission_date')

    # Filter for Child Admins
    if not request.user.is_superuser:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.expedition_admin_type:
            submissions_list = submissions_list.filter(expedition_type=profile.expedition_admin_type)
            
    # GET Filters
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    expedition = request.GET.get('expedition', '').strip()
    category = request.GET.get('category', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if query:
        submissions_list = submissions_list.filter(
            Q(title__icontains=query) |
            Q(abstract__icontains=query) |
            Q(metadata_id__icontains=query) |
            Q(submitter__first_name__icontains=query) |
            Q(submitter__last_name__icontains=query) |
            Q(submitter__email__icontains=query)
        )
    if status:
        submissions_list = submissions_list.filter(status=status)
    if expedition:
        submissions_list = submissions_list.filter(expedition_type=expedition)
    if category:
        submissions_list = submissions_list.filter(category=category)
    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            submissions_list = submissions_list.filter(submission_date__date__gte=parsed_start)
        except ValueError:
            pass
    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            submissions_list = submissions_list.filter(submission_date__date__lte=parsed_end)
        except ValueError:
            pass
            
    # Pagination
    paginator = Paginator(submissions_list, 10) # 10 submissions per page
    page_number = request.GET.get('page')
    submissions = paginator.get_page(page_number)
    
    # Context items needed for the frontend filter UI
    expedition_choices = DatasetSubmission.EXPEDITION_TYPES
    category_choices = DatasetSubmission.CATEGORY_CHOICES
    status_choices = DatasetSubmission.STATUS_CHOICES
    
    return render(
        request,
        'admin/all_submissions.html',
        {
            'submissions': submissions,
            'total_submissions': submissions_list.count(),
            'current_q': query,
            'current_status': status,
            'current_expedition': expedition,
            'current_category': category,
            'current_start_date': start_date,
            'current_end_date': end_date,
            'expedition_choices': expedition_choices,
            'category_choices': category_choices,
            'status_choices': status_choices,
        }
    )


@login_required
@user_passes_test(lambda u: is_reviewer(u) or is_admin(u) or is_expedition_admin(u))
@require_http_methods(["GET", "POST"])
def review_submission_detail(request, metadata_id):
    
    # Try to get by metadata_id first
    try:
        submission = DatasetSubmission.objects.get(metadata_id=metadata_id)
    except DatasetSubmission.DoesNotExist:
        # If not found and metadata_id looks like a number, try to find by primary key
        if metadata_id.isdigit():
            try:
                submission = DatasetSubmission.objects.get(id=int(metadata_id))
                # Redirect to the correct URL with metadata_id

                return redirect('data_submission:review_submission_detail', metadata_id=submission.metadata_id)
            except (DatasetSubmission.DoesNotExist, ValueError):
                raise Http404("No DatasetSubmission matches the given query.")
        else:
            raise Http404("No DatasetSubmission matches the given query.")
    
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
                metadata_id=submission.metadata_id
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
Dataset ID: {submission.metadata_id}
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
                
                logger.info(f"Publication notification sent for dataset {submission.metadata_id}")
                
        except Exception as e:
            logger.error(f"Failed to send status notification: {str(e)}")

        messages.success(request, "Submission reviewed successfully.")
        
        # Log the review action
        logger.info(f"User {request.user.id} changed dataset {submission.metadata_id} from {previous_status} to {status}")
        

        
        return redirect('data_submission:review_submissions')

    # Safe check if user is super admin (not a limited expedition admin)
    is_super_admin = request.user.is_superuser
    if not is_super_admin and request.user.is_staff:
        profile = getattr(request.user, 'profile', None)
        is_super_admin = not (profile and profile.expedition_admin_type)

    return render(
        request,
        'admin/review_submission_detail.html',
        {
            'submission': submission,
            'status_transitions': STATUS_TRANSITIONS.get(submission.status, []),
            'is_super_admin': is_super_admin
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


def is_non_expedition_admin(user):
    """Super Admin or Normal Admin (staff without expedition_admin_type)."""
    if not user.is_staff:
        return False
    profile = getattr(user, 'profile', None)
    return user.is_superuser or not (profile and profile.expedition_admin_type)

@login_required
@user_passes_test(is_non_expedition_admin)
@require_http_methods(["POST"])
def admin_delete_dataset(request, metadata_id):
    """Only Super Admin and Normal Admin can delete. Expedition admins cannot."""
    
    # Try to get by metadata_id first
    try:
        dataset = DatasetSubmission.objects.get(metadata_id=metadata_id)
    except DatasetSubmission.DoesNotExist:
        # If not found and metadata_id looks like a number, try to find by primary key
        if metadata_id.isdigit():
            try:
                dataset = DatasetSubmission.objects.get(id=int(metadata_id))
                # Redirect to the correct URL with metadata_id
                from django.shortcuts import redirect
                return redirect('data_submission:admin_delete_dataset', metadata_id=dataset.metadata_id)
            except (DatasetSubmission.DoesNotExist, ValueError):
                raise Http404("No DatasetSubmission matches the given query.")
        else:
            raise Http404("No DatasetSubmission matches the given query.")
    
    title = dataset.title
    dataset.delete()
    messages.success(request, f'Dataset "{title}" deleted successfully.')
    logger.info(f"Super admin {request.user.id} deleted dataset {metadata_id}")
    return redirect("data_submission:all_submissions")


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
def upload_dataset_files(request, metadata_id):
    """
    Step 2: Upload files for the dataset submission.
    """
    
    # Try to get by metadata_id first
    try:
        dataset = DatasetSubmission.objects.get(metadata_id=metadata_id)
    except DatasetSubmission.DoesNotExist:
        # If not found and metadata_id looks like a number, try to find by primary key
        if metadata_id.isdigit():
            try:
                dataset = DatasetSubmission.objects.get(id=int(metadata_id))
                # Redirect to the correct URL with metadata_id
                return redirect('data_submission:upload_dataset_files', metadata_id=dataset.metadata_id)
            except (DatasetSubmission.DoesNotExist, ValueError):
                raise Http404("No DatasetSubmission matches the given query.")
        else:
            raise Http404("No DatasetSubmission matches the given query.")
    
    # RBAC: Only submitter or admin can upload files
    if not (request.user == dataset.submitter or is_admin(request.user)):
        messages.error(request, "You do not have permission to edit this dataset.")
        return redirect('data_submission:my_submissions')
        
    if request.method == 'POST':
        from .forms import DatasetUploadForm
        form = DatasetUploadForm(request.POST, request.FILES, instance=dataset)
        if form.is_valid():
            dataset = form.save(commit=False)
            dataset.status = 'submitted' # Finalize submission
            dataset.save()
            
            # 🚀 Auto-update Online Resource field with the download link
            if hasattr(dataset, 'citation') and dataset.data_file:
                try:
                    from django.urls import reverse
                    get_data_url = reverse('data_submission:get_data', args=[dataset.metadata_id])
                    dataset.citation.online_resource = request.build_absolute_uri(get_data_url)
                    dataset.citation.save()
                except Exception as e:
                    logger.error(f"Error updating online resource link: {str(e)}")
            
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
Dataset ID: {dataset.metadata_id}
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
                logger.info(f"Submission notification sent to admins for dataset {dataset.metadata_id}")
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
Dataset ID: {dataset.metadata_id}
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
            # Admins go back to review detail; regular users see success page
            if is_admin(request.user):
                return redirect('data_submission:review_submission_detail', metadata_id=dataset.metadata_id)
            return redirect('data_submission:submission_success', metadata_id=dataset.metadata_id)
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

def _check_ai_limit(request):
    """Check per-user AI rate limit. Returns JsonResponse if limited, else None."""
    if not check_ai_rate_limit(request.user.id):
        return JsonResponse({'error': 'AI rate limit reached. Please wait before trying again (max 30 requests/hour).'}, status=429)
    return None


@login_required
@require_post_method
def ai_classify_view(request):
    """API: AI auto-classify dataset into category, topic, ISO topic."""
    limited = _check_ai_limit(request)
    if limited:
        return limited
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
    limited = _check_ai_limit(request)
    if limited:
        return limited
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
    limited = _check_ai_limit(request)
    if limited:
        return limited
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
    limited = _check_ai_limit(request)
    if limited:
        return limited
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
    limited = _check_ai_limit(request)
    if limited:
        return limited
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
    limited = _check_ai_limit(request)
    if limited:
        return limited
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
    limited = _check_ai_limit(request)
    if limited:
        return limited
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
    limited = _check_ai_limit(request)
    if limited:
        return limited
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
    limited = _check_ai_limit(request)
    if limited:
        return limited
    try:
        data = json.loads(request.body)
        submission_id = data.get('submission_id')

        if not submission_id:
            return JsonResponse({'error': 'Submission ID is required.'}, status=400)

        submission = DatasetSubmission.objects.get(metadata_id=submission_id)

        # Build submission data dict for AI analysis
        submission_data = {
            'id': submission.metadata_id,
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
def admin_edit_submission(request, metadata_id):
    """
    View for Admins (Super & Child) to edit a submission.
    """
    
    # Try to get by metadata_id first
    try:
        submission = DatasetSubmission.objects.get(metadata_id=metadata_id)
    except DatasetSubmission.DoesNotExist:
        # If not found and metadata_id looks like a number, try to find by primary key
        if metadata_id.isdigit():
            try:
                submission = DatasetSubmission.objects.get(id=int(metadata_id))
                # Redirect to the correct URL with metadata_id
                return redirect('data_submission:admin_edit_submission', metadata_id=submission.metadata_id)
            except (DatasetSubmission.DoesNotExist, ValueError):
                raise Http404("No DatasetSubmission matches the given query.")
        else:
            raise Http404("No DatasetSubmission matches the given query.")

    # 🚨 PERMISSION CHECK: Child Admins can only edit their type
    if not request.user.is_superuser:
        profile = getattr(request.user, 'profile', None)
        if profile and profile.expedition_admin_type:
            if submission.expedition_type != profile.expedition_admin_type:
                messages.error(request, "You are not authorized to edit this submission.")
                return redirect('data_submission:review_submissions')

    if request.method == "POST":
        action = request.POST.get("save")
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
            
        scientist_formset = ScientistFormSetEdit(request.POST, instance=submission)
        instrument_formset = InstrumentFormSetEdit(request.POST, instance=submission)

        if action == "PREVIEW":
            # For Admins: Preview the current form data WITHOUT saving to DB or requiring strict validation
            # Create a mock dataset from current form fields (commit=False prevents DB save)
            preview_ds = dataset_form.save(commit=False)
            preview_ds.id = submission.id
            
            # Helper to safely grab partial form data
            def get_partial(f):
                for v in f.fields.values(): v.required = False
                if f.is_valid():
                    try: return f.save(commit=False)
                    except: return None
                return None

            preview_ds.citation = get_partial(citation_form) or citation_instance
            preview_ds.platform = get_partial(platform_form) or platform_instance
            preview_ds.gps = get_partial(gps_form) or gps_instance
            preview_ds.location = get_partial(location_form) or location_instance
            preview_ds.resolution = get_partial(resolution_form) or resolution_instance
            preview_ds.paleo_temporal = get_partial(paleo_form) or paleo_instance
            
            return render(request, 'data_submission/preview_dataset.html', {
                'dataset': preview_ds,
                'is_admin_preview': True
            })

        # For Admins, we only strictly require the main Dataset form and Scientist/Instrument formsets.
        # Legacy datasets might not have Citation, Platform, etc.
        main_valid = all([dataset_form.is_valid(), scientist_formset.is_valid(), instrument_formset.is_valid()])

        if main_valid:
            with transaction.atomic():
                submission = dataset_form.save()
                
                submission.status_updated_at = timezone.now()
                # Save related forms only if they are valid
                if citation_form.is_valid():
                    cit = citation_form.save(commit=False)
                    cit.dataset = submission
                    cit.save()
                    
                if platform_form.is_valid():
                    plat = platform_form.save(commit=False)
                    plat.dataset = submission
                    plat.save()
                    
                if gps_form.is_valid():
                    gps = gps_form.save(commit=False)
                    gps.dataset = submission
                    gps.save()
                    
                if location_form.is_valid():
                    loc = location_form.save(commit=False)
                    loc.dataset = submission
                    loc.save()
                    
                if resolution_form.is_valid():
                    res = resolution_form.save(commit=False)
                    res.dataset = submission
                    res.save()
                    
                if paleo_form.is_bound and paleo_form.is_valid():
                    pal = paleo_form.save(commit=False)
                    pal.dataset = submission
                    pal.save()
                
                scientist_formset.instance = submission
                scientist_formset.save()
                
                instrument_formset.instance = submission
                instrument_formset.save()
                
                messages.success(request, f"Submission {submission.metadata_id} updated successfully.")
                return redirect("data_submission:upload_dataset_files", metadata_id=submission.metadata_id)
        else:
             messages.error(request, "Please correct the errors on the Main form, Scientists, or Instruments.")
    else:
        # GET - Populate forms with instance data
        dataset_form = DatasetSubmissionForm(instance=submission)
        citation_form = DatasetCitationForm(instance=getattr(submission, 'citation', None))
        platform_form = PlatformMetadataForm(instance=getattr(submission, 'platform', None))
        gps_form = GPSMetadataForm(instance=getattr(submission, 'gps', None))
        location_form = LocationMetadataForm(instance=getattr(submission, 'location', None))
        resolution_form = DataResolutionMetadataForm(instance=getattr(submission, 'resolution', None))
        paleo_form = PaleoTemporalCoverageForm(instance=getattr(submission, 'paleo_temporal', None))
        
        scientist_formset = ScientistFormSetEdit(instance=submission)
        instrument_formset = InstrumentFormSetEdit(instance=submission)

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
            "dataset_id": submission.metadata_id,
        },
    )

from .models import DatasetRequest

@user_passes_test(is_admin)
def admin_data_requests_view(request):
    """Admin view to list all data requests.
    
    - Superuser/staff can see all requests
    - Expedition admins can only see requests for their assigned expedition type
    """
    # Get base queryset
    requests_list = DatasetRequest.objects.all().select_related(
        'dataset', 'requester', 'reviewed_by'
    ).order_by('-request_date')
    
    # Filter by expedition type if user is an expedition admin (not superuser)
    if not request.user.is_superuser:
        # Get the user's profile
        try:
            profile = request.user.profile
            if profile.expedition_admin_type:
                # Filter to only requests for datasets with this expedition type
                requests_list = requests_list.filter(
                    dataset__expedition_type=profile.expedition_admin_type
                )
        except:
            # If no profile or error, return empty queryset for non-superusers
            requests_list = requests_list.none()
    
    # Pagination logic
    paginator = Paginator(requests_list, 10)  # 10 requests per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(
        request,
        'admin/admin_data_requests.html',
        {
            'requests': page_obj,
            'title': 'Data Download Requests',
        }
    )

# removed email-related imports; approval flow no longer sends mail

# decorator left behind when functions were commented out
# @user_passes_test(is_admin)
# def admin_approve_data_request(request, request_id):
#     """Admin view to approve a request and email the user."""
#     req = get_object_or_404(DatasetRequest, id=request_id)
#     
#     if request.method == 'POST':
#         req.status = 'approved'
#         req.reviewed_by = request.user
#         req.reviewed_at = timezone.now()
#         req.save()
#         
#         # Prepare the download link
#         if req.dataset.data_file:
#             download_url = request.build_absolute_uri(req.dataset.data_file.url)
#             link_text = f"Download Link: {download_url}"
#         else:
#             link_text = "This dataset does not currently have a downloadable file attached. Please contact the administrator for manual access."
# 
#         # Compile and send the email
#         subject = f"Dataset Request Approved: {req.dataset.metadata_id}"
#         message = (
#             f"Dear {req.first_name} {req.last_name},\n\n"
#             f"Your request to download the dataset '{req.dataset.title}' ({req.dataset.metadata_id}) has been APPROVED.\n\n"
#             f"{link_text}\n\n"
#             f"Thank you,\nNational Polar Data Center"
#         )
#         
#         try:
#             send_mail(
#                 subject,
#                 message,
#                 settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@npdc.ncpor.res.in',
#                 [req.email],
#                 fail_silently=False,
#             )
#             messages.success(request, f"Request from {req.first_name} {req.last_name} approved! An email with the download link has been sent to {req.email}.")
#         except Exception as e:
#             messages.warning(request, f"Request approved, but failed to send email: {str(e)}")
#         
#     return redirect('data_submission:admin_data_requests')
# 
# # decorator left behind
# # @user_passes_test(is_admin)
# def admin_reject_data_request(request, request_id):
#     """Admin view to reject a request."""
#     req = get_object_or_404(DatasetRequest, id=request_id)
#     
#     if request.method == 'POST':
#         req.status = 'rejected'
#         req.reviewed_by = request.user
#         req.reviewed_at = timezone.now()
#         req.save()
#         
#         messages.warning(request, f"Request from {req.first_name} {req.last_name} has been rejected.")
#         
#     return redirect('data_submission:admin_data_requests')