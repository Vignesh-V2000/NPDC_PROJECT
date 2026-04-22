"""
Reassign all datasets to vssamy@ncpor.res.in
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.contrib.auth.models import User
from data_submission.models import DatasetSubmission
from users.models import UserLogin

# Get or create vssamy user
try:
    vssamy_user = User.objects.get(username='vssamy@ncpor.res.in')
    print(f'✓ Found user: {vssamy_user.username} ({vssamy_user.email})')
except User.DoesNotExist:
    print('✗ User vssamy@ncpor.res.in not found in Django auth')
    print('  Creating from legacy data...')
    try:
        legacy = UserLogin.objects.filter(e_mail='vssamy@ncpor.res.in').first()
        if legacy:
            vssamy_user = User.objects.create_user(
                username='vssamy@ncpor.res.in',
                email='vssamy@ncpor.res.in',
                first_name='V Sakthivel',
                last_name='Samy',
                is_active=True,
            )
            print(f'✓ Created user: {vssamy_user.username}')
        else:
            print('  Legacy user not found, creating with defaults...')
            vssamy_user = User.objects.create_user(
                username='vssamy@ncpor.res.in',
                email='vssamy@ncpor.res.in',
                first_name='Sakthivel',
                last_name='Samy',
                is_active=True,
            )
            print(f'✓ Created user: {vssamy_user.username}')
    except Exception as e:
        print(f'  Error: {e}')
        exit(1)

# Get all datasets
datasets = DatasetSubmission.objects.all()
print(f'\nFound {datasets.count()} datasets:')
print("-" * 80)

for ds in datasets:
    old_submitter = ds.submitter.username if ds.submitter else 'None'
    print(f'  {ds.title[:50]}...')
    print(f'    Current submitter: {old_submitter}')

print("\n" + "-" * 80)
print(f"\nReassigning ALL {datasets.count()} datasets to: {vssamy_user.username}\n")

# Reassign all datasets
updated_count = datasets.update(submitter=vssamy_user)

print(f'✓ Successfully reassigned {updated_count} datasets to {vssamy_user.username}')
print("\nUpdated datasets:")
print("-" * 80)

for ds in DatasetSubmission.objects.all():
    print(f'  {ds.title[:50]}...')
    print(f'    New submitter: {ds.submitter.username}')

print("\n" + "=" * 80)
print(f'✓ All datasets now submitted by: {vssamy_user.username}')
print("=" * 80)
