"""
Management command to retroactively update `submission_date` on 
existing `DatasetSubmission` records using the legacy `metadata_ts`.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from data_submission.models import DatasetSubmission

class Command(BaseCommand):
    help = 'Fix legacy submission dates using metadata_ts from metadata_main_table'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Starting legacy date fix...'))

        query = """
            SELECT
                metadata_id,
                metadata_ts
            FROM metadata_main_table
            WHERE metadata_ts IS NOT NULL
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            
        self.stdout.write(f'Found {len(rows)} legacy records with timestamps.')
        
        updated = 0
        missing = 0
        
        for row in rows:
            metadata_id = row[0]
            metadata_ts = row[1]
            
            # Find the dataset using the legacy ID stored in keywords
            qs = DatasetSubmission.objects.filter(keywords__icontains=f"legacy_id:{metadata_id}")
            
            if qs.exists():
                for dataset in qs:
                    # Use .update() to bypass auto_now_add
                    DatasetSubmission.objects.filter(pk=dataset.pk).update(submission_date=metadata_ts)
                    updated += 1
            else:
                missing += 1
                
        self.stdout.write(self.style.SUCCESS(f'Update complete!'))
        self.stdout.write(f'  Updated: {updated}')
        self.stdout.write(f'  Not found in Django DB: {missing}')
