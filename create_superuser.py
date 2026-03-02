"""
Create Django user for superuser@gmail.com (info@ncaor.org)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.contrib.auth.models import User
from users.models import UserLogin, Profile
from django.utils import timezone

# Get legacy user
legacy_user = UserLogin.objects.filter(e_mail='info@ncaor.org').first()
if not legacy_user:
    print("✗ Legacy user not found")
    exit(1)

print(f"Legacy user: {legacy_user.user_id}")

# Create or update Django user
django_user, created = User.objects.get_or_create(
    username=legacy_user.user_id.lower(),
    defaults={
        'email': legacy_user.e_mail,
        'first_name': 'Super',
        'last_name': 'User',
        'is_active': True,
        'is_staff': True,
        'is_superuser': True,
    }
)

# Set password
django_user.set_password('admin123')
django_user.save()

# Create or update profile
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
print(f"\n✓ {status} Django user:")
print(f"  Username: {django_user.username}")
print(f"  Email: {django_user.email}")
print(f"  Password: admin123")
print(f"  Is Staff: {django_user.is_staff}")
print(f"  Is Superuser: {django_user.is_superuser}")

print(f"\n✓ Ready to login!")
print(f"  URL: http://localhost:8000/admin")
print(f"  Username: {django_user.username}")
print(f"  Password: admin123")
