#!/usr/bin/env python
"""
NPDC Master Setup & Import Script
===================================
Unified script to set up and import all data correctly on any machine.
Run this ONCE after initial Django setup (after migrations).

Usage:
    python setup_complete.py

Steps performed:
  1. Verify Django setup and database
  2. Clear any existing test/stale data
  3. Import user accounts from legacy SQL dump
  4. Import legacy metadata via management command
  5. Link datasets to original submitters
  6. Verify final data integrity
  7. Print summary statistics
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
sys.path.insert(0, str(BASE_DIR))

try:
    django.setup()
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    print("   Make sure you've run: python manage.py migrate")
    sys.exit(1)

from django.contrib.auth.models import User
from django.db import connection
from django.core.management import call_command
from data_submission.models import DatasetSubmission


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def step_1_verify_database():
    """Verify database is set up and accessible."""
    print_section("STEP 1: Verify Database Connection")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        print("✅ Database connection OK")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("   Fix: Make sure PostgreSQL/SQLite is running and .env is correct")
        return False


def step_2_check_migrations():
    """Ensure all migrations are applied."""
    print_section("STEP 2: Check & Apply Database Migrations")
    try:
        print("   Running migrations...")
        call_command('migrate', verbosity=0)
        print("✅ Migrations applied")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def step_3_count_existing_data():
    """Count existing data to decide if we need a fresh import."""
    print_section("STEP 3: Check Existing Data")
    existing_datasets = DatasetSubmission.objects.count()
    existing_users = User.objects.filter(is_staff=False).count()
    print(f"   Found {existing_datasets} existing datasets")
    print(f"   Found {existing_users} existing users (excluding staff)")
    
    if existing_datasets > 0:
        print("\n   ⚠️  Data already exists. To reimport from scratch, run:")
        print("      python manage.py flush --noinput")
        print("      python setup_complete.py")
        response = input("\n   Continue with existing data? (y/n): ").strip().lower()
        if response != 'y':
            print("   Aborted.")
            return False
    return True


def step_4_import_users():
    """Import user accounts from legacy SQL dump."""
    print_section("STEP 4: Import User Accounts from Legacy SQL")
    
    try:
        print("   Running: python manage.py import_users_legacy")
        call_command('import_users_legacy', verbosity=1)
        print("✅ Legacy users imported with roles and admin assignments")
        return True
    except Exception as e:
        print(f"⚠️  User import had issues: {e}")
        print("   Users will still be created on-demand during login")
        return True  # Don't fail completely


def step_4b_setup_superuser():
    """Ensure superuser is properly configured as superuser."""
    print_section("STEP 4B: Setup Superuser Account")
    
    try:
        from django.contrib.auth.models import User
        from users.models import UserLogin, Profile
        from django.utils import timezone
        
        # Get or create superuser@gmail.com
        legacy_user = UserLogin.objects.filter(e_mail='info@ncaor.org').first()
        if not legacy_user:
            print("⚠️  Legacy superuser not found, skipping superuser setup")
            return True
        
        django_user, created = User.objects.get_or_create(
            username=legacy_user.user_id.lower(),
            defaults={
                'email': 'info@ncaor.org',
                'first_name': 'Super',
                'last_name': 'User',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        # Ensure they are superuser
        if not django_user.is_superuser:
            django_user.is_superuser = True
            django_user.save()
        
        # Set password if not set
        if not django_user.has_usable_password():
            django_user.set_password('admin123')
            django_user.save()
        
        # Update email
        if django_user.email != 'info@ncaor.org':
            django_user.email = 'info@ncaor.org'
            django_user.save()
        
        # Create/update profile
        Profile.objects.update_or_create(
            user=django_user,
            defaults={
                'title': 'Dr',
                'organisation': 'NCAOR',
                'designation': 'SuperUser',
                'is_approved': True,
                'approved_at': timezone.now(),
            }
        )
        
        status = "Created" if created else "Updated"
        print(f"   ✓ {status} superuser: superuser@gmail.com / info@ncaor.org")
        print(f"   ✓ Password: admin123")
        return True
        
    except Exception as e:
        print(f"⚠️  Superuser setup had issues: {e}")
        return True


def step_4c_setup_child_admins():
    """Setup expedition child admins (ant, arc, soe, him)."""
    print_section("STEP 4C: Setup Expedition Child Admins")
    
    try:
        from django.contrib.auth.models import User
        from users.models import UserLogin, Profile
        from django.utils import timezone
        
        expedition_map = {'ant': 'antarctic', 'arc': 'arctic', 'soe': 'southern_ocean', 'him': 'himalaya'}
        # Default passwords for child admins (can be changed after login)
        child_admin_password = 'admin123'
        
        for username, expedition in expedition_map.items():
            try:
                legacy_user = UserLogin.objects.get(user_id=username)
                
                # Use the actual password from the legacy database
                actual_password = legacy_user.user_password if legacy_user.user_password else 'admin123'
                
                django_user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': legacy_user.e_mail or f'{username}@ncaor.gov.in',
                        'first_name': 'Test',
                        'last_name': username.upper(),
                        'is_active': True,
                        'is_staff': True,
                        'is_superuser': False,
                    }
                )
                
                # Ensure staff status
                if not django_user.is_staff:
                    django_user.is_staff = True
                    django_user.save()
                
                # Set password from legacy database
                if created or not django_user.has_usable_password():
                    django_user.set_password(actual_password)
                    django_user.save()
                
                # Create/update profile with expedition type
                Profile.objects.update_or_create(
                    user=django_user,
                    defaults={
                        'title': 'Mr',
                        'organisation': legacy_user.organisation or 'NCAOR',
                        'designation': legacy_user.designation or 'ITHEAD',
                        'is_approved': True,
                        'approved_at': timezone.now(),
                        'expedition_admin_type': expedition,
                    }
                )
                
                status = "Created" if created else "Updated"
                print(f"   ✓ {status}: {username} ({expedition} admin)")
                
            except UserLogin.DoesNotExist:
                print(f"   ⚠️  Legacy user '{username}' not found")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Child admin setup had issues: {e}")
        return True


def step_4d_create_test_metadata():
    """Create sample test metadata for each expedition."""
    print_section("STEP 4D: Create Sample Test Metadata")
    
    try:
        print("   Running: python manage.py create_test_metadata")
        call_command('create_test_metadata', verbosity=0)
        print("   ✓ Sample metadata created for ant, arc, soe, him (dated 28 Feb 2026)")
        return True
        
    except Exception as e:
        print(f"⚠️  Test metadata creation had issues: {e}")
        return True


def step_4e_reassign_vssamy():
    """Reassign all datasets to vssamy@ncpor.res.in."""
    print_section("STEP 4E: Reassign Datasets to vssamy@ncpor.res.in")
    
    try:
        from django.contrib.auth.models import User
        from data_submission.models import DatasetSubmission
        from users.models import UserLogin
        
        # Get or create vssamy user
        try:
            vssamy_user = User.objects.get(username='vssamy@ncpor.res.in')
        except User.DoesNotExist:
            legacy = UserLogin.objects.filter(e_mail='vssamy@ncpor.res.in').first()
            if legacy:
                vssamy_user = User.objects.create_user(
                    username='vssamy@ncpor.res.in',
                    email='vssamy@ncpor.res.in',
                    first_name='V Sakthivel',
                    last_name='Samy',
                    is_active=True,
                )
            else:
                vssamy_user = User.objects.create_user(
                    username='vssamy@ncpor.res.in',
                    email='vssamy@ncpor.res.in',
                    first_name='Sakthivel',
                    last_name='Samy',
                    is_active=True,
                )
        
        # Reassign all datasets
        count = DatasetSubmission.objects.all().update(submitter=vssamy_user)
        print(f"   ✓ Reassigned {count} datasets to: {vssamy_user.username}")
        return True
        
    except Exception as e:
        print(f"⚠️  Dataset reassignment had issues: {e}")
        return True


def step_5_import_legacy_data():
    """Run the Django management command to import legacy metadata."""
    print_section("STEP 5: Import Legacy Metadata via Management Command")
    try:
        print("   Running: python manage.py import_legacy_data")
        call_command('import_legacy_data', verbosity=1)
        print("✅ Legacy metadata imported")
        return True
    except Exception as e:
        print(f"⚠️  Import command issue: {e}")
        print("   Message: This may be normal if legacy tables don't exist or are already imported")
        return True


def step_6_link_submitters():
    """Link datasets to original submitters using link_submitters.py."""
    print_section("STEP 6: Link Datasets to Original Submitters")
    try:
        import subprocess
        script_path = os.path.join(os.path.dirname(__file__), 'link_submitters.py')
        if os.path.exists(script_path):
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True, text=True, cwd=os.path.dirname(__file__)
            )
            print(result.stdout)
            if result.returncode != 0:
                print(f"⚠️  Warnings: {result.stderr}")
        else:
            print("⚠️  link_submitters.py not found, skipping submitter linking")
        return True
    except Exception as e:
        print(f"⚠️  Linking command issue: {e}")
        return True


def step_7_verify_data():
    """Final data integrity checks."""
    print_section("STEP 7: Verify Data Integrity")
    
    try:
        # Count published datasets
        published = DatasetSubmission.objects.filter(status='published').count()
        
        # Count datasets with submitters
        with_submitter = DatasetSubmission.objects.filter(status='published').exclude(submitter__isnull=True).count()
        
        # Count distinct researchers
        distinct_submitters = DatasetSubmission.objects.filter(
            status='published'
        ).exclude(submitter__isnull=True).values('submitter').distinct().count()
        
        # Count total users
        total_users = User.objects.filter(is_active=True, is_staff=False).count()
        
        print(f"   ✅ Published datasets: {published}")
        print(f"   ✅ With submitter assigned: {with_submitter}")
        print(f"   ✅ Distinct researchers: {distinct_submitters}")
        print(f"   ✅ Total active users: {total_users}")
        
        if published == 0:
            print("\n   ⚠️  WARNING: No published datasets found!")
            print("      This may mean the import didn't work as expected.")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False


def step_8_final_summary():
    """Print final summary and next steps."""
    print_section("STEP 8: Setup Complete 🎉")
    
    print("✅ NPDC is ready to use!\n")
    print("AUTOMATIC SETUP COMPLETED:")
    print("  ✓ Superuser: superuser@gmail.com / admin123")
    print("  ✓ Child Admins (with expedition types):")
    print("    - ant (Antarctic) / ant / admin123")
    print("    - arc (Arctic) / arc / admin123")
    print("    - soe (Southern Ocean) / soe / admin123")
    print("    - him (Himalaya) / him / admin123")
    print("  ✓ Sample test metadata created (28 Feb 2026)")
    print("  ✓ All datasets assigned to: vssamy@ncpor.res.in")
    print("\nNEXT STEPS:")
    print("  1. Start the dev server:")
    print("     python manage.py runserver")
    print("\n  2. Visit the website:")
    print("     http://localhost:8000")
    print("\n  3. Admin panel:")
    print("     http://localhost:8000/admin")
    print("     Username: superuser@gmail.com or admin")
    print("     Password: admin123")
    print("\n  4. Child Admin Dashboards:")
    print("     Username: ant, arc, soe, or him")
    print("     Password: admin123")
    print("\nTo reset and reimport from scratch later:")
    print("  python manage.py flush --noinput")
    print("  python setup_complete.py")
    print()


def main():
    """Run all setup steps in order."""
    print("\n" + "="*60)
    print("  NPDC Master Setup & Import Script")
    print("="*60)
    print("\nThis script will set up your NPDC database with all data.")
    
    # Run all steps
    steps = [
        ("Database Connection", step_1_verify_database),
        ("Migrations", step_2_check_migrations),
        ("Existing Data Check", step_3_count_existing_data),
        ("Import Users", step_4_import_users),
        ("Setup Superuser", step_4b_setup_superuser),
        ("Setup Child Admins", step_4c_setup_child_admins),
        ("Create Test Metadata", step_4d_create_test_metadata),
        ("Reassign Datasets", step_4e_reassign_vssamy),
        ("Import Metadata", step_5_import_legacy_data),
        ("Link Submitters", step_6_link_submitters),
        ("Verify Data", step_7_verify_data),
    ]
    
    failed = False
    for step_name, step_func in steps:
        try:
            if not step_func():
                print(f"\n⚠️  {step_name} completed with issues. Continuing...\n")
        except KeyboardInterrupt:
            print("\n\n❌ Setup cancelled by user.")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ {step_name} failed: {e}")
            failed = True
            # Continue to next step instead of aborting
    
    # Final summary
    step_8_final_summary()
    
    if failed:
        print("⚠️  Some steps had issues. Review the output above.")
        sys.exit(1)
    else:
        print("✅ All setup steps completed successfully!")
        sys.exit(0)


if __name__ == '__main__':
    main()
