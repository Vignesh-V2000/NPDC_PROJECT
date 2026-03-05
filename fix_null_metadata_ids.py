#!/usr/bin/env python
"""
Fix script to handle datasets with NULL or empty metadata_ids.

This script identifies datasets with NULL/empty metadata_ids and provides
three options for remediation:
1. Auto-generate metadata_ids (if structure known)
2. Unpublish them (revert to draft)
3. Delete them (if they're test/incomplete records)
"""

import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from data_submission.models import DatasetSubmission

def check_status():
    """Check current status of datasets with NULL metadata_ids"""
    with connection.cursor() as cursor:
        # Count by metadata_id status
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN metadata_id IS NULL OR metadata_id = '' THEN 'NULL/EMPTY'
                    ELSE 'VALID'
                END as status,
                COUNT(*) as count
            FROM data_submission_datasetsubmission
            WHERE status = 'published'
            GROUP BY status
        """)
        results = cursor.fetchall()
        for status, count in results:
            print(f"  {status}: {count}")
    
    return True

def option_1_unpublish_null_metadata():
    """
    Option 1: Unpublish datasets with NULL metadata_ids (safest option)
    This reverts them to 'draft' status so they won't appear in search.
    They can be manually reviewed and either deleted or properly assigned metadata_ids.
    """
    print("\n=== OPTION 1: UNPUBLISH NULL METADATA_ID DATASETS ===")
    print("This will revert datasets with NULL metadata_id to 'draft' status")
    print("(Safest option - they can be reviewed and fixed later)\n")
    
    count = DatasetSubmission.objects.filter(
        status='published',
        metadata_id__isnull=True
    ).count()
    
    count2 = DatasetSubmission.objects.filter(
        status='published',
        metadata_id=''
    ).count()
    
    total = count + count2
    print(f"Datasets to unpublish: {total}")
    
    if input("Execute this fix? (yes/no): ").lower() == 'yes':
        # Move NULL to draft
        updated1 = DatasetSubmission.objects.filter(
            status='published',
            metadata_id__isnull=True
        ).update(status='draft')
        
        # Move empty string to draft
        updated2 = DatasetSubmission.objects.filter(
            status='published',
            metadata_id=''
        ).update(status='draft')
        
        print(f"✓ Unpublished {updated1 + updated2} datasets")
        print(f"They are now in 'draft' status and won't appear in search results")
        return True
    return False

def option_2_delete_null_metadata():
    """
    Option 2: Delete datasets with NULL metadata_ids (if they're test/incomplete)
    This is destructive - only use if you're sure these are unwanted records.
    """
    print("\n=== OPTION 2: DELETE NULL METADATA_ID DATASETS ===")
    print("WARNING: This is destructive and cannot be undone!")
    print("Only use if these are test/incomplete records.\n")
    
    count = DatasetSubmission.objects.filter(
        status='published',
        metadata_id__isnull=True
    ).count()
    
    count2 = DatasetSubmission.objects.filter(
        status='published',
        metadata_id=''
    ).count()
    
    total = count + count2
    print(f"Datasets to delete: {total}")
    
    confirm = input("Type 'DELETE' to confirm deletion: ")
    if confirm == 'DELETE':
        deleted1, _ = DatasetSubmission.objects.filter(
            status='published',
            metadata_id__isnull=True
        ).delete()
        
        deleted2, _ = DatasetSubmission.objects.filter(
            status='published',
            metadata_id=''
        ).delete()
        
        print(f"✓ Deleted {deleted1 + deleted2} datasets")
        return True
    else:
        print("Deletion cancelled")
    return False

def verify_fix():
    """Verify the fix worked"""
    print("\n=== VERIFICATION ===")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM data_submission_datasetsubmission 
            WHERE status = 'published' AND (metadata_id IS NULL OR metadata_id = '')
        """)
        null_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM data_submission_datasetsubmission 
            WHERE status = 'published' AND metadata_id IS NOT NULL AND metadata_id != ''
        """)
        valid_count = cursor.fetchone()[0]
    
    print(f"Published datasets with NULL/empty metadata_id: {null_count}")
    print(f"Published datasets with valid metadata_id: {valid_count}")
    print(f"Total published: {null_count + valid_count}")
    
    if null_count == 0:
        print("\n✓ Fix successful! The doubled count issue is resolved.")
    else:
        print(f"\n⚠ Still have {null_count} datasets with NULL metadata_ids")

if __name__ == '__main__':
    print("=" * 70)
    print("NPDC DATASET COUNT FIX - Null Metadata ID Handler")
    print("=" * 70)
    
    print("\nCurrent Status:")
    check_status()
    
    print("\n" + "=" * 70)
    print("AVAILABLE OPTIONS:")
    print("=" * 70)
    
    while True:
        print("\n1. Unpublish NULL datasets (safest - mark as draft)")
        print("2. Delete NULL datasets (risky - permanent deletion)")
        print("3. Just check status and exit")
        
        choice = input("\nSelect option (1/2/3): ").strip()
        
        if choice == '1':
            if option_1_unpublish_null_metadata():
                verify_fix()
            break
        elif choice == '2':
            if option_2_delete_null_metadata():
                verify_fix()
            break
        elif choice == '3':
            break
        else:
            print("Invalid choice")
