"""
Management command to create sample test metadata for each expedition admin.
Usage: python manage.py create_test_metadata
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from data_submission.models import DatasetSubmission
from datetime import datetime, date, timedelta


class Command(BaseCommand):
    help = 'Create sample test metadata for ant, arc, soe, and him expedition admins'

    def handle(self, *args, **options):
        # Test user mapping
        test_users = {
            'ant': {
                'expedition': 'antarctic',
                'title': 'Antarctic Sample Dataset - Test Metadata',
            },
            'arc': {
                'expedition': 'arctic',
                'title': 'Arctic Sample Dataset - Test Metadata',
            },
            'soe': {
                'expedition': 'southern_ocean',
                'title': 'Southern Ocean Sample Dataset - Test Metadata',
            },
            'him': {
                'expedition': 'himalaya',
                'title': 'Himalaya Sample Dataset - Test Metadata',
            },
        }

        created_count = 0

        for username, info in test_users.items():
            try:
                # Get or create the Django user
                user = User.objects.get(username=username)
                self.stdout.write(f"Found user: {username}")
            except User.DoesNotExist:
                # Try to create from legacy user_login
                from users.models import UserLogin, Profile
                try:
                    legacy_user = UserLogin.objects.get(user_id=username)
                    user = User.objects.create_user(
                        username=username,
                        email=legacy_user.e_mail or f'{username}@ncaor.gov.in',
                        first_name='Test',
                        last_name=username.upper(),
                        is_active=True,
                        is_staff=True,
                    )
                    # Create or update profile
                    expedition_map = {'ant': 'antarctic', 'arc': 'arctic', 'soe': 'southern_ocean', 'him': 'himalaya'}
                    Profile.objects.update_or_create(
                        user=user,
                        defaults={
                            'title': 'Mr',
                            'organisation': legacy_user.organisation or 'NCAOR',
                            'designation': legacy_user.designation or 'ITHEAD',
                            'is_approved': True,
                            'approved_at': timezone.now(),
                            'expedition_admin_type': expedition_map.get(username),
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"Created user from legacy data: {username}"))
                except UserLogin.DoesNotExist:
                    self.stdout.write(self.style.ERROR(f"User '{username}' not found in Django auth or legacy user_login. Skipping."))
                    continue

            # Create sample dataset
            try:
                dataset = DatasetSubmission.objects.create(
                    title=info['title'],
                    abstract='Sample test metadata for automated testing. This dataset contains dummy data.',
                    purpose='Testing expedition admin functionality and metadata submission workflows.',
                    version='1.0',
                    keywords='test, sample, dummy, metadata, {}'.format(info['expedition']),
                    topic='Test Topic',
                    data_center='National Polar Data Center',
                    
                    # Expedition info
                    expedition_type=info['expedition'],
                    expedition_year='2025-2026',
                    expedition_number=f'TEST-{username.upper()}-001',
                    
                    # Project info
                    project_number=f'PRJ-{username.upper()}-2026',
                    project_name=f'Test Project for {username.upper()} Admin',
                    category='atmosphere',
                    iso_topic='climatologyMeteorologyAtmosphere',
                    data_set_progress='complete',
                    
                    # Temporal coverage - 28 Feb 2026
                    temporal_start_date=date(2026, 2, 28),
                    temporal_end_date=date(2026, 2, 28),
                    
                    # Spatial coverage (sample coordinates)
                    west_longitude=-180.0 if info['expedition'] != 'himalaya' else 60.0,
                    east_longitude=180.0 if info['expedition'] != 'himalaya' else 100.0,
                    south_latitude=-90.0 if info['expedition'] == 'antarctic' else (-60.0 if info['expedition'] == 'southern_ocean' else 25.0),
                    north_latitude=-60.0 if info['expedition'] == 'antarctic' else (0.0 if info['expedition'] == 'southern_ocean' else 40.0),
                    
                    # Contact info
                    contact_person=f'Test Contact for {username}',
                    contact_email=f'test_{username}@ncpor.res.in',
                    contact_phone='+91-832-2525600',
                    
                    # Submitter
                    submitter=user,
                    status='submitted',
                )
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created test metadata for {username.upper()} ({info["expedition"]}): {dataset.title}'
                    )
                )
                created_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error creating metadata for {username}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Successfully created {created_count} test metadata records dated 28 Feb 2026')
        )
