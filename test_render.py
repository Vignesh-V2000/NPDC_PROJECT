import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc.settings')
django.setup()

logging.disable(logging.CRITICAL)

from django.template import Template, Context
from data_submission.models import DatasetSubmission
from data_submission.forms import DatasetSubmissionForm

d = DatasetSubmission.objects.last()
print("Dataset PK:", d.pk)
print("Title from DB:", d.title)

f = DatasetSubmissionForm(instance=d)
t = Template('{% load crispy_forms_tags %}{{ form.title|as_crispy_field }}')
c = Context({'form': f})
html = t.render(c)
print("HTML OUTPUT:\n", html)
