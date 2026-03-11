import random
from data_submission.models import DatasetSubmission

submissions = DatasetSubmission.objects.all()
updated = 0

for s in submissions:
    if s.metadata_id and s.metadata_id.startswith('MF') and '-' not in s.metadata_id:
        while True:
            new_id = f"MF-{''.join([str(random.randint(0, 9)) for _ in range(10)])}"
            if not DatasetSubmission.objects.filter(metadata_id=new_id).exists():
                break
        
        print(f"Updating {s.metadata_id} to {new_id} for ID {s.id}")
        s.metadata_id = new_id
        s.save(update_fields=['metadata_id'])
        updated += 1

print(f"Total updated: {updated}")
