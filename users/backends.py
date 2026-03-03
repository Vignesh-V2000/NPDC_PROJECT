from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login using their email address.
    Falls back to username if email is not found.
    If the user exists in the legacy 'user_login' table but not in Django's auth_user,
    auto-creates a Django user from the legacy data.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        # NOTE: do NOT log passwords. We only log which branch is attempted
        ip = None
        try:
            ip = request.META.get('REMOTE_ADDR') if request is not None else None
        except Exception:
            ip = None
        logger.info("Authentication attempt for user=%s from=%s", username, ip)

        # 1. Try Django auth_user first
        user = self._authenticate_django(username, password)
        if user:
            logger.info("Authentication succeeded via Django auth for user=%s", username)
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
                logger.info("No Django user found for %s", username)
                return None
        except User.MultipleObjectsReturned:
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                logger.info("Multiple Django users matched but none by username for %s", username)
                return None

        # Report whether the user has a usable password (no secrets logged)
        try:
            logger.debug("Found Django user=%s has_usable_password=%s", username, user.has_usable_password())
        except Exception:
            pass

        try:
            pw_ok = user.check_password(password)
        except Exception as e:
            logger.exception("Error checking password for user=%s: %s", username, e)
            pw_ok = False

        logger.info("Password check for user=%s returned %s", username, pw_ok)

        if pw_ok and self.user_can_authenticate(user):
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

        logger.info("Legacy user found for %s with status=%s", legacy_user.user_id, legacy_user.account_status)

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
                # password didn't match. Since the Django password was already set in a previous
                # login, we must NOT override it. Authentication should fail.
                logger.info("Django password mismatch for user=%s; rejecting (password already set)", email)
                return None

            # At this point the Django user exists but has no usable password yet.
            # This is the first login. Legacy passwords are encrypted (Base64-encoded hash)
            # and cannot be compared directly. Accept the entered password and save it.
            logger.info("Django user has no usable password for user=%s; setting password from legacy path", email)
            django_user.set_password(password)
            django_user.save()
            # Fall through to Profile sync below
        except User.DoesNotExist:
            # No Django user exists yet. We'll try to create one, but there may
            # already be an account with the same username (case‑insensitive).
            # If that happens we should reuse/update the existing record instead
            # of crashing with IntegrityError.
            logger.info("Creating new Django user from legacy for user=%s", email)
            existing = User.objects.filter(username__iexact=email.lower()).first()
            if existing:
                # Reuse and ensure email field is correct & lowercase
                django_user = existing
                django_user.email = email.lower()
                django_user.first_name = first_name
                django_user.last_name = last_name
                django_user.is_active = True
                django_user.set_password(password)
                django_user.save()
            else:
                try:
                    django_user = User.objects.create(
                        username=email.lower(),
                        email=email.lower(),
                        first_name=first_name,
                        last_name=last_name,
                        is_active=True,
                    )
                    django_user.set_password(password)
                    django_user.save()
                except Exception as e:
                    logger.exception("Failed to create Django user for legacy %s: %s", email, e)
                    # As a fallback, try again by fetching any matching username
                    django_user = User.objects.filter(username__iexact=email.lower()).first()
                    if django_user:
                        django_user.set_password(password)
                        django_user.save()
                    else:
                        # If we still don't have a user, bail out to avoid None later
                        return None

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

        try:
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
        except Exception as e:
            # Profile update should not prevent authentication. Log and continue.
            logger.exception("Failed to update/create Profile for user %s: %s", getattr(django_user, 'email', '<unknown>'), e)

        # Return the newly created user (already authenticated since we set the password)
        return django_user
