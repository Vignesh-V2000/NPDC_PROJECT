"""
Django management command to fix datasets with NULL metadata_ids.

Usage:
    python manage.py fix_null_metadata_ids                    # Check only
    python manage.py fix_null_metadata_ids --unpublish        # Unpublish NULL datasets
    python manage.py fix_null_metadata_ids --delete            # Delete NULL datasets (risky!)
    python manage.py fix_null_metadata_ids --auto-fix         # Auto-generate metadata_ids
"""

from django.core.management.base import BaseCommand
from django.db import connection
from data_submission.models import DatasetSubmission
import uuid
from datetime import datetime


class Command(BaseCommand):
    help = 'Fix datasets with NULL or empty metadata_ids'

    def add_arguments(self, parser):
        parser.add_argument(
            '--unpublish',
            action='store_true',
            help='Unpublish datasets with NULL metadata_ids (move to draft)',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete datasets with NULL metadata_ids (RISKY - permanent)',
        )
        parser.add_argument(
            '--auto-fix',
            action='store_true',
            help='Auto-generate metadata_ids for NULL datasets',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('NPDC Null Metadata ID Fixer'))
        self.stdout.write(self.style.SUCCESS('=' * 70))

        # Check current status
        null_count = DatasetSubmission.objects.filter(
            status='published',
            metadata_id__isnull=True
        ).count()

        empty_count = DatasetSubmission.objects.filter(
            status='published',
            metadata_id=''
        ).count()

        total_null = null_count + empty_count

        valid_count = DatasetSubmission.objects.filter(
            status='published'
        ).exclude(metadata_id__isnull=True).exclude(metadata_id='').count()

        self.stdout.write('\nCurrent Status:')
        self.stdout.write(f'  Published with NULL metadata_id:  {null_count}')
        self.stdout.write(f'  Published with empty metadata_id: {empty_count}')
        self.stdout.write(f'  Total NULL/empty:                 {total_null}')
        self.stdout.write(f'  Published with valid metadata_id: {valid_count}')
        self.stdout.write(f'  ---')
        self.stdout.write(f'  Total showing in search:          {self.total_count()}')

        if total_null == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ No issues found!'))
            return

        # Execute action
        if options['auto_fix']:
            self._auto_fix_metadata_ids(options['dry_run'])
        elif options['unpublish']:
            self._unpublish_null_datasets(options['dry_run'])
        elif options['delete']:
            self._delete_null_datasets(options['dry_run'])
        else:
            # Just show status
            self.stdout.write(self.style.WARNING(
                '\nNo action specified. Use --unpublish, --delete, or --auto-fix'
            ))

    def total_count(self):
        """Get total published dataset count"""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM data_submission_datasetsubmission WHERE status = %s",
                ['published']
            )
            return cursor.fetchone()[0]

    def _unpublish_null_datasets(self, dry_run=False):
        """Move datasets with NULL metadata_id to draft status"""
        self.stdout.write(self.style.WARNING('\n--- UNPUBLISH NULL DATASETS ---'))
        self.stdout.write('This will move datasets with NULL metadata_id to draft status')

        qs_null = DatasetSubmission.objects.filter(
            status='published',
            metadata_id__isnull=True
        )
        qs_empty = DatasetSubmission.objects.filter(
            status='published',
            metadata_id=''
        )

        count = qs_null.count() + qs_empty.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY RUN] Would unpublish {count} datasets'))
            return

        confirm = input(f'Unpublish {count} datasets? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Cancelled')
            return

        updated1 = qs_null.update(status='draft')
        updated2 = qs_empty.update(status='draft')

        self.stdout.write(self.style.SUCCESS(f'✓ Unpublished {updated1 + updated2} datasets'))
        self.stdout.write(f'  They are now in draft status and won\'t appear in search')

        # Show summary
        self._show_summary()

    def _delete_null_datasets(self, dry_run=False):
        """Delete datasets with NULL metadata_id"""
        self.stdout.write(self.style.ERROR('\n--- DELETE NULL DATASETS ---'))
        self.stdout.write(self.style.ERROR('WARNING: This is PERMANENT and cannot be undone!'))

        qs_null = DatasetSubmission.objects.filter(
            status='published',
            metadata_id__isnull=True
        )
        qs_empty = DatasetSubmission.objects.filter(
            status='published',
            metadata_id=''
        )

        count = qs_null.count() + qs_empty.count()

        if dry_run:
            self.stdout.write(self.style.ERROR(f'[DRY RUN] Would delete {count} datasets'))
            return

        confirm = input(f'DELETE {count} datasets permanently? Type "DELETE": ')
        if confirm != 'DELETE':
            self.stdout.write('Cancelled')
            return

        deleted1, _ = qs_null.delete()
        deleted2, _ = qs_empty.delete()

        self.stdout.write(self.style.SUCCESS(f'✓ Deleted {deleted1 + deleted2} datasets'))

        # Show summary
        self._show_summary()

    def _auto_fix_metadata_ids(self, dry_run=False):
        """Auto-generate metadata_ids for NULL datasets"""
        self.stdout.write(self.style.WARNING('\n--- AUTO-GENERATE METADATA IDS ---'))

        qs_null = DatasetSubmission.objects.filter(
            status='published',
            metadata_id__isnull=True
        )
        qs_empty = DatasetSubmission.objects.filter(
            status='published',
            metadata_id=''
        )

        all_qs = qs_null | qs_empty
        count = all_qs.count()

        if dry_run:
            self.stdout.write(self.style.WARNING(f'[DRY RUN] Would generate {count} metadata_ids'))
            return

        confirm = input(f'Generate metadata_ids for {count} datasets? (yes/no): ')
        if confirm.lower() != 'yes':
            self.stdout.write('Cancelled')
            return

        updated = 0
        for dataset in all_qs:
            # Generate format: MF-{timestamp}-{random}
            timestamp = int(datetime.now().timestamp() * 1000)
            random_id = str(uuid.uuid4())[:8].upper()
            metadata_id = f'MF-{timestamp}-{random_id}'

            dataset.metadata_id = metadata_id
            dataset.save()
            updated += 1

            if updated % 100 == 0:
                self.stdout.write(f'  Generated {updated}/{count} metadata_ids...')

        self.stdout.write(self.style.SUCCESS(f'✓ Generated {updated} metadata_ids'))

        # Show summary
        self._show_summary()

    def _show_summary(self):
        """Show summary after fix"""
        self.stdout.write('\nVerification:')
        null_count = DatasetSubmission.objects.filter(
            status='published',
            metadata_id__isnull=True
        ).count()
        empty_count = DatasetSubmission.objects.filter(
            status='published',
            metadata_id=''
        ).count()
        valid_count = DatasetSubmission.objects.filter(
            status='published'
        ).exclude(metadata_id__isnull=True).exclude(metadata_id='').count()

        self.stdout.write(f'  Published with NULL/empty metadata_id: {null_count + empty_count}')
        self.stdout.write(f'  Published with valid metadata_id: {valid_count}')
        self.stdout.write(f'  Total published: {null_count + empty_count + valid_count}')

        if null_count + empty_count == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ Fix successful!'))
        else:
            self.stdout.write(self.style.WARNING(f'\n⚠ Still {null_count + empty_count} datasets with NULL metadata_ids'))
