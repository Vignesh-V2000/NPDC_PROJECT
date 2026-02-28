import os
import sys

# Ensure project root on path
sys.path.insert(0, r'c:\Users\rahul\OneDrive\Documents\GitHub\NPDC_COPY')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')

import django
django.setup()

from data_submission.models import DatasetSubmission

published = DatasetSubmission.objects.filter(status='published')
print('Published total:', published.count())

print('\nTop 5 Recent Published:')
for ds in published.order_by('-submission_date')[:5]:
    print(ds.id, ds.title, ds.submission_date, getattr(ds, 'number_of_files', None), getattr(ds, 'file_size_mb', None))

print('\nTop 5 Popular (by number_of_files, file_size_mb):')
for ds in published.order_by('-number_of_files', '-file_size_mb')[:5]:
    print(ds.id, ds.title, ds.submission_date, getattr(ds, 'number_of_files', None), getattr(ds, 'file_size_mb', None))
