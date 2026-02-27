"""
Management command to link imported legacy datasets to their actual submitters.

Uses the `metadata_activities` table to find the first user who performed
an action on each metadata_id, then creates/finds the corresponding Django
User and updates the DatasetSubmission.submitter field.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import connection
from django.utils import timezone
from data_submission.models import DatasetSubmission
from users.models import UserLogin, Profile


class Command(BaseCommand):
    help = 'Link imported legacy datasets to their actual submitters via metadata_activities'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would change without making changes')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # 1. Build metadata_id → user_id (email) map from metadata_activities
        self.stdout.write("Building user-to-metadata map from metadata_activities...")
        with connection.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (metadata_id) metadata_id, user_id
                FROM metadata_activities 
                WHERE metadata_id IS NOT NULL AND metadata_id != ''
                AND user_id IS NOT NULL AND user_id != ''
                ORDER BY metadata_id, id ASC
            """)
            activity_map = {r[0]: r[1] for r in cur.fetchall()}
        self.stdout.write(f"  Found {len(activity_map)} metadata-to-user mappings")

        # 2. Get all imported datasets
        imported = DatasetSubmission.objects.filter(keywords__contains='legacy_id:')
        self.stdout.write(f"  Found {imported.count()} imported datasets")

        updated = 0
        skipped_no_activity = 0
        skipped_no_user = 0
        created_users = 0

        for ds in imported:
            # Extract metadata_id from keywords
            kw = ds.keywords or ''
            metadata_id = None
            for part in kw.split(','):
                part = part.strip()
                if part.startswith('legacy_id:'):
                    metadata_id = part.replace('legacy_id:', '').strip()
                    break

            if not metadata_id or metadata_id not in activity_map:
                skipped_no_activity += 1
                continue

            user_email = activity_map[metadata_id].strip().lower()

            # Skip admin/system accounts — keep as legacy_import
            if user_email in ('ant', 'arc', 'soe', 'him', 'admin'):
                # These are admin accounts that submitted on behalf of users
                # Try to find the actual scientist from scientist_details instead
                scientist = ds.scientists.first()
                if scientist and scientist.email:
                    user_email = scientist.email.strip().lower()
                else:
                    skipped_no_user += 1
                    continue

            if not user_email or '@' not in user_email:
                skipped_no_user += 1
                continue

            # Find or create Django user
            try:
                django_user = User.objects.filter(email__iexact=user_email).first()
                if not django_user:
                    raise User.DoesNotExist
            except User.DoesNotExist:
                # Try to find in legacy user_login
                try:
                    legacy = UserLogin.objects.filter(user_id__iexact=user_email).first()
                    if not legacy:
                        raise UserLogin.DoesNotExist
                    full_name = (legacy.user_name or '').strip()
                    name_parts = full_name.split() if full_name else ['User']
                    first_name = name_parts[0] if name_parts else 'User'
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                    if dry_run:
                        self.stdout.write(f"  [DRY RUN] Would create user: {user_email} ({full_name})")
                        updated += 1
                        continue

                    django_user = User.objects.create_user(
                        username=user_email,
                        email=user_email,
                        first_name=first_name,
                        last_name=last_name,
                        is_active=True,
                    )
                    # Set unusable password — they'll authenticate via legacy backend
                    django_user.set_unusable_password()
                    if legacy.user_role and 'administrator' in legacy.user_role.lower():
                        django_user.is_staff = True
                    django_user.save()

                    # Create profile
                    title_map = {'mr': 'Mr', 'ms': 'Ms', 'dr': 'Dr', 'prof': 'Prof'}
                    raw_title = (legacy.title or '').strip().lower().rstrip('.')
                    mapped_title = title_map.get(raw_title, 'Mr')

                    Profile.objects.update_or_create(
                        user=django_user,
                        defaults={
                            'title': mapped_title,
                            'preferred_name': (legacy.known_as or '').strip(),
                            'organisation': (legacy.organisation or '').strip(),
                            'organisation_url': (legacy.url or '').strip() if legacy.url else '',
                            'designation': (legacy.designation or '').strip(),
                            'phone': (legacy.phone_number or '').strip()[:10],
                            'address': (legacy.address or '').strip(),
                            'alternate_email': (legacy.e_mail or '').strip() if legacy.e_mail and legacy.e_mail.lower() != user_email else '',
                            'is_approved': True,
                            'approved_at': timezone.now(),
                        }
                    )
                    created_users += 1

                except UserLogin.DoesNotExist:
                    # User not in legacy table either — create minimal user
                    if dry_run:
                        self.stdout.write(f"  [DRY RUN] Would create minimal user: {user_email}")
                        updated += 1
                        continue

                    django_user = User.objects.create_user(
                        username=user_email,
                        email=user_email,
                        is_active=True,
                    )
                    django_user.set_unusable_password()
                    django_user.save()
                    Profile.objects.update_or_create(
                        user=django_user,
                        defaults={'title': 'Mr', 'is_approved': True, 'approved_at': timezone.now()}
                    )
                    created_users += 1
            except Exception:
                skipped_no_user += 1
                continue

            if dry_run:
                self.stdout.write(f"  [DRY RUN] {ds.title[:50]}... → {user_email}")
                updated += 1
                continue

            # Update submitter
            ds.submitter = django_user
            ds.save(update_fields=['submitter'])
            updated += 1

            if updated % 50 == 0:
                self.stdout.write(f"  Updated {updated}...")

        self.stdout.write(f"\n{'[DRY RUN] ' if dry_run else ''}Complete!")
        self.stdout.write(f"  Updated: {updated}")
        self.stdout.write(f"  New users created: {created_users}")
        self.stdout.write(f"  Skipped (no activity): {skipped_no_activity}")
        self.stdout.write(f"  Skipped (no valid user): {skipped_no_user}")
