"""
Management command to import users from legacy user_login table to Django auth.
Usage: python manage.py import_users_legacy
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserLogin, Profile
from django.utils import timezone


class Command(BaseCommand):
    help = 'Import users from legacy user_login table to Django auth_user'

    def handle(self, *args, **options):
        print("\n" + "="*60)
        print("  Importing Users from Legacy user_login Table")
        print("="*60 + "\n")
        
        try:
            legacy_users = UserLogin.objects.filter(account_status='Active')
            self.stdout.write(f"Found {legacy_users.count()} active users in user_login table\n")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error querying user_login: {e}"))
            return

        created_count = 0
        updated_count = 0
        error_count = 0
        
        # Expedition admin mapping
        expedition_admin_mapping = {
            'arc': 'arctic',
            'ant': 'antarctic',
            'soe': 'southern_ocean',
            'him': 'himalaya',
        }

        for legacy_user in legacy_users:
            try:
                # Create or get Django user
                username = legacy_user.user_id.lower()
                email = legacy_user.user_id.lower()
                
                # Parse name
                full_name = (legacy_user.user_name or '').strip()
                name_parts = full_name.split() if full_name else ['User']
                first_name = name_parts[0] if name_parts else 'User'
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                
                # Get or create user
                django_user, created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'is_active': True,
                    }
                )
                
                # Set staff status for Administrator role
                is_admin = legacy_user.user_role and 'administrator' in legacy_user.user_role.lower()
                django_user.is_staff = is_admin
                django_user.is_superuser = False
                
                # Import password from legacy table
                if legacy_user.user_password and not django_user.has_usable_password():
                    django_user.set_password(legacy_user.user_password)
                
                django_user.save()
                
                # Create or update profile
                title_map = {'mr': 'Mr', 'ms': 'Ms', 'dr': 'Dr', 'prof': 'Prof'}
                raw_title = (legacy_user.title or '').strip().lower().rstrip('.')
                mapped_title = title_map.get(raw_title, 'Mr')
                
                expedition_admin_type = expedition_admin_mapping.get(legacy_user.user_id.lower())
                
                profile, profile_created = Profile.objects.get_or_create(
                    user=django_user,
                    defaults={
                        'title': mapped_title,
                        'preferred_name': (legacy_user.known_as or '').strip(),
                        'organisation': (legacy_user.organisation or '').strip() or 'NCAOR',
                        'designation': (legacy_user.designation or '').strip(),
                        'phone': (legacy_user.phone_number or '').strip()[:10],
                        'address': (legacy_user.address or '').strip(),
                        'is_approved': True,
                        'approved_at': timezone.now(),
                        'expedition_admin_type': expedition_admin_type,
                    }
                )
                
                if not profile_created:
                    # Update existing profile
                    profile.title = mapped_title
                    profile.preferred_name = (legacy_user.known_as or '').strip()
                    profile.organisation = (legacy_user.organisation or '').strip() or 'NCAOR'
                    profile.designation = (legacy_user.designation or '').strip()
                    profile.phone = (legacy_user.phone_number or '').strip()[:10]
                    profile.address = (legacy_user.address or '').strip()
                    profile.expedition_admin_type = expedition_admin_type
                    profile.save()
                
                # Print result
                if created:
                    status = "✓ Created"
                    created_count += 1
                else:
                    status = "↻ Updated"
                    updated_count += 1
                
                admin_text = " [ADMIN]" if is_admin else ""
                expedition_text = f" [{expedition_admin_type.upper()}]" if expedition_admin_type else ""
                
                self.stdout.write(f"{status}: {username}{admin_text}{expedition_text}")
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"✗ Error with {legacy_user.user_id}: {e}"))

        # Print summary
        print("\n" + "="*60)
        print(f"  Summary: {created_count} created, {updated_count} updated, {error_count} errors")
        print("="*60 + "\n")
        
        if error_count == 0:
            self.stdout.write(self.style.SUCCESS("✓ All users imported successfully!"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠️  {error_count} errors during import"))
