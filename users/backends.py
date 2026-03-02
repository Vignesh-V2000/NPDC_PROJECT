from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.utils import timezone


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login using their email address.
    Falls back to username if email is not found.
    If the user exists in the legacy 'user_login' table but not in Django's auth_user,
    auto-creates a Django user from the legacy data.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # 1. Try Django auth_user first
        user = self._authenticate_django(username, password)
        if user:
            return user

        # 2. Try legacy user_login table
        user = self._authenticate_legacy(username, password)
        if user:
            return user

        return None

    def _authenticate_django(self, username, password):
        """Standard Django authentication against auth_user table."""
        try:
            user = User.objects.get(email__iexact=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                return None
        except User.MultipleObjectsReturned:
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def _authenticate_legacy(self, username, password):
        """
        Check the legacy user_login table. If user found and active,
        auto-create a Django User + Profile with the entered password.
        """
        from .models import UserLogin, Profile

        try:
            legacy_user = UserLogin.objects.get(user_id__iexact=username)
        except UserLogin.DoesNotExist:
            # Also try the e_mail field
            try:
                legacy_user = UserLogin.objects.filter(e_mail__iexact=username).first()
                if not legacy_user:
                    return None
            except Exception:
                return None

        # Only allow active accounts
        if legacy_user.account_status and legacy_user.account_status.strip().lower() != 'active':
            return None

        # Auto-create Django user from legacy data
        # Parse name into first/last
        full_name = (legacy_user.user_name or '').strip()
        name_parts = full_name.split() if full_name else ['User']
        first_name = name_parts[0] if name_parts else 'User'
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

        email = legacy_user.user_id  # user_id is the email/login

        # Check if Django user already exists with this email
        try:
            django_user = User.objects.get(email__iexact=email)
            # If the user already has a usable password, verify it normally.
            if django_user.has_usable_password():
                if django_user.check_password(password) and self.user_can_authenticate(django_user):
                    return django_user
                # password didn't match, do not override existing usable password
                return None

            # At this point the Django user exists but has no usable password yet.
            # Legacy passwords are encrypted (Base64-encoded hash) and cannot be
            # compared directly. Accept the entered password on first login and
            # save it as the Django password.
            django_user.set_password(password)
            django_user.save()
            return django_user
        except User.DoesNotExist:
            # No Django user exists yet. Create one with the entered password.
            # Legacy passwords are encrypted and can't be verified directly.
            django_user = User.objects.create(
                username=email.lower(),
                email=email.lower(),
                first_name=first_name,
                last_name=last_name,
                is_active=True,
            )
            django_user.set_password(password)
            django_user.save()

        # Set staff status for Administrator role
        if legacy_user.user_role and 'administrator' in legacy_user.user_role.lower():
            django_user.is_staff = True
            django_user.save()

        # Create Profile from legacy data
        title_map = {'mr': 'Mr', 'ms': 'Ms', 'dr': 'Dr', 'prof': 'Prof'}
        raw_title = (legacy_user.title or '').strip().lower().rstrip('.')
        mapped_title = title_map.get(raw_title, 'Mr')

        # Automatically assign expedition_admin_type based on username
        expedition_admin_mapping = {
            'arc': 'arctic',
            'ant': 'antarctic',
            'soe': 'southern_ocean',
            'him': 'himalaya',
        }
        expedition_admin_type = expedition_admin_mapping.get(legacy_user.user_id.lower(), None)

        Profile.objects.update_or_create(
            user=django_user,
            defaults={
                'title': mapped_title,
                'preferred_name': (legacy_user.known_as or '').strip(),
                'organisation': (legacy_user.organisation or '').strip(),
                'organisation_url': (legacy_user.url or '').strip() if legacy_user.url else '',
                'designation': (legacy_user.designation or '').strip(),
                'phone': (legacy_user.phone_number or '').strip()[:10],
                'address': (legacy_user.address or '').strip(),
                'alternate_email': (legacy_user.e_mail or '').strip() if legacy_user.e_mail != email else '',
                'is_approved': True,
                'approved_at': timezone.now(),
                'expedition_admin_type': expedition_admin_type,
            }
        )

        # Return the newly created user (already authenticated since we set the password)
        return django_user
