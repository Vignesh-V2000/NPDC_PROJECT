"""
Link imported datasets to their actual submitters instead of legacy_import.

Strategy:
1. For each dataset, find metadata_id from keywords (legacy_id:XXX)
2. Look up metadata_activities to find the user_id who submitted it
3. Look up user_login to get the email/name of that user
4. Create or match a Django User for that email
5. Update dataset.submitter to that user
6. Fallback: use scientist_details sci_email if no activity record exists
"""
import os
import sys
import django
import re

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth.models import User
from django.db import connection
from data_submission.models import DatasetSubmission

def get_legacy_users():
    """Build a map of legacy user_id -> (email, name) from user_login table."""
    user_map = {}
    with connection.cursor() as c:
        c.execute("SELECT user_id, e_mail, user_name FROM user_login")
        for user_id, email, name in c.fetchall():
            if email and email.strip():
                user_map[str(user_id)] = (email.strip().lower(), (name or '').strip())
    print(f"  Loaded {len(user_map)} legacy users with emails")
    return user_map

def get_activity_map():
    """Build a map of metadata_id -> user_id from metadata_activities."""
    activity_map = {}
    with connection.cursor() as c:
        # Get the earliest activity (creation/submission) for each metadata
        c.execute("""
            SELECT DISTINCT ON (metadata_id) metadata_id, user_id
            FROM metadata_activities
            WHERE metadata_id IS NOT NULL AND metadata_id != ''
            ORDER BY metadata_id, id ASC
        """)
        for metadata_id, user_id in c.fetchall():
            if metadata_id and user_id:
                activity_map[metadata_id.strip()] = str(user_id)
    print(f"  Loaded {len(activity_map)} activity records")
    return activity_map

def get_scientist_email_map():
    """Build a map of metadata_id -> sci_email from scientist_details."""
    sci_map = {}
    with connection.cursor() as c:
        c.execute("""
            SELECT m.metadata_id, s.sci_email, s.sci_name, s.sci_last_name
            FROM metadata_main_table m
            JOIN scientist_details s ON m.sci_id = s.sci_id
            WHERE s.sci_email IS NOT NULL AND s.sci_email != ''
              AND s.sci_email NOT LIKE '%%legacy%%'
        """)
        for metadata_id, sci_email, first, last in c.fetchall():
            if metadata_id and sci_email and '@' in sci_email:
                name = f"{(first or '').strip()} {(last or '').strip()}".strip()
                sci_map[metadata_id.strip()] = (sci_email.strip().lower(), name)
    print(f"  Loaded {len(sci_map)} scientist email records")
    return sci_map

def get_or_create_user(email, name=''):
    """Get or create a Django user by email."""
    email = email.lower().strip()
    
    # Skip admin/system emails
    skip_emails = ['legacy@npdc.gov.in', 'admin@npdc.gov.in', 'ictd@ncaor.gov.in']
    if email in skip_emails:
        return None
    
    # Try to find existing user by email
    try:
        user = User.objects.get(email=email)
        return user
    except User.DoesNotExist:
        pass
    except User.MultipleObjectsReturned:
        return User.objects.filter(email=email).first()
    
    # Create new user
    # Use email as username (truncated to 150 chars)
    username = email[:150]
    
    # Parse name
    parts = name.split() if name else []
    first_name = parts[0][:30] if parts else email.split('@')[0][:30]
    last_name = ' '.join(parts[1:])[:150] if len(parts) > 1 else ''
    
    # Clean name parts
    first_name = re.sub(r'[^A-Za-z\s.\-]', '', first_name) or 'User'
    last_name = re.sub(r'[^A-Za-z\s.\-]', '', last_name)
    
    user = User.objects.create(
        username=username,
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_active=True,
    )
    user.set_unusable_password()
    user.save()
    return user

def main():
    print("=" * 60)
    print("  Linking Datasets to Actual Submitters")
    print("=" * 60)
    
    # Load lookup tables
    print("\nLoading legacy data...")
    legacy_users = get_legacy_users()
    activity_map = get_activity_map()
    sci_email_map = get_scientist_email_map()
    
    # Get all datasets
    datasets = DatasetSubmission.objects.filter(status='published')
    total = datasets.count()
    print(f"\n  Total published datasets: {total}")
    
    linked_via_activity = 0
    linked_via_scientist = 0
    skipped_no_match = 0
    already_linked = 0
    errors = 0
    
    legacy_user = User.objects.filter(username='legacy_import').first()
    
    for ds in datasets:
        try:
            # Extract legacy metadata_id from keywords
            match = re.search(r'legacy_id:(\S+)', ds.keywords or '')
            if not match:
                skipped_no_match += 1
                continue
            
            metadata_id = match.group(1).strip().rstrip(',')
            
            # Skip if already linked to a real user
            if ds.submitter and ds.submitter != legacy_user:
                already_linked += 1
                continue
            
            # Strategy 1: Use metadata_activities -> user_login
            user_id = activity_map.get(metadata_id)
            if user_id and user_id in legacy_users:
                email, name = legacy_users[user_id]
                user = get_or_create_user(email, name)
                if user:
                    ds.submitter = user
                    ds.save(update_fields=['submitter'])
                    linked_via_activity += 1
                    continue
            
            # Strategy 2: Use scientist_details sci_email
            if metadata_id in sci_email_map:
                email, name = sci_email_map[metadata_id]
                # Skip the bulk ictd@ncpor.res.in email (it's a shared admin account)
                if email != 'ictd@ncpor.res.in':
                    user = get_or_create_user(email, name)
                    if user:
                        ds.submitter = user
                        ds.save(update_fields=['submitter'])
                        linked_via_scientist += 1
                        continue
            
            # Strategy 3: Use contact_email on the dataset itself
            if ds.contact_email and '@' in ds.contact_email and ds.contact_email != 'legacy@npdc.gov.in':
                email = ds.contact_email
                name = ds.contact_person or ''
                if email != 'ictd@ncpor.res.in':
                    user = get_or_create_user(email, name)
                    if user:
                        ds.submitter = user
                        ds.save(update_fields=['submitter'])
                        linked_via_scientist += 1
                        continue
            
            skipped_no_match += 1
            
        except Exception as e:
            errors += 1
            print(f"  Error on dataset {ds.id}: {e}")
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"  Results:")
    print(f"    Linked via activity records: {linked_via_activity}")
    print(f"    Linked via scientist email:  {linked_via_scientist}")
    print(f"    Already linked:              {already_linked}")
    print(f"    No match (kept legacy):      {skipped_no_match}")
    print(f"    Errors:                      {errors}")
    print(f"{'=' * 60}")
    
    # Stats
    distinct = DatasetSubmission.objects.filter(status='published').exclude(
        submitter__username='legacy_import'
    ).values('submitter').distinct().count()
    still_legacy = DatasetSubmission.objects.filter(
        status='published', submitter__username='legacy_import'
    ).count()
    print(f"\n  Distinct real submitters: {distinct}")
    print(f"  Still on legacy_import:   {still_legacy}")
    print(f"  Total users created:      {User.objects.filter(is_staff=False).count()}")

if __name__ == '__main__':
    main()
