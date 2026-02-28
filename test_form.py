import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "npdc.settings")
django.setup()

from data_submission.models import DatasetSubmission
from data_submission.forms import DatasetSubmissionForm, DatasetCitationForm, PlatformMetadataForm, LocationMetadataForm, DataResolutionMetadataForm, PaleoTemporalCoverageForm

def test():
    sub = DatasetSubmission.objects.get(id=947)
    
    # Simulate GET
    form = DatasetSubmissionForm(instance=sub)
    
    # Build POST data from the form's initial data to simulate a perfect unmodified submission
    post_data = {}
    for name, field in form.fields.items():
        val = form.initial.get(name)
        if val is not None:
             post_data[name] = val
             
    # Add prefix for citation form just to test it empty
    
    form_post = DatasetSubmissionForm(post_data, instance=sub)
    print("Dataset form valid?", form_post.is_valid())
    if not form_post.is_valid():
        print("Dataset form errors:", form_post.errors)

test()
