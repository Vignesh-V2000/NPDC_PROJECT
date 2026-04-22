import os
import django
import sys
import random

# Add project root to sys.path
sys.path.append('c:\\Users\\rahul\\OneDrive\\Documents\\GitHub\\NPDC_PROJECT')

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "npdc.settings")
django.setup()

from data_submission.models import DatasetSubmission

def update_metadata_ids():
    submissions = DatasetSubmission.objects.all()
    updated_count = 0
    
    for submission in submissions:
        # Check if it has an old metadata_id (length 12 typically since it was MF + 10 hex characters)
        # Or you can check if it just doesn't contain a hyphen after MF
        current_id = submission.metadata_id
        
        if current_id and current_id.startswith('MF') and '-' not in current_id:
            # Generate new MF-XXXXXXXXXX id
            while True:
                random_digits = ''.join([str(random.randint(0, 9)) for _ in range(10)])
                new_id = f"MF-{random_digits}"
                if not DatasetSubmission.objects.filter(metadata_id=new_id).exists():
                    break
            
            print(f"Updating {current_id} -> {new_id} for Dataset ID: {submission.id}")
            submission.metadata_id = new_id
            submission.save(update_fields=['metadata_id'])
            updated_count += 1
            
    print(f"\nSuccessfully updated {updated_count} submissions.")

if __name__ == '__main__':
    update_metadata_ids()
