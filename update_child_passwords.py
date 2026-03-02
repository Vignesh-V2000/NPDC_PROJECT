#!/usr/bin/env python
"""Update child admin passwords to admin123."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.contrib.auth.models import User

print("Updating child admin passwords...\n")

for username in ['ant', 'arc', 'soe', 'him']:
    try:
        user = User.objects.get(username=username)
        user.set_password('admin123')
        user.save()
        print(f'✓ Password set for {username} → admin123')
    except User.DoesNotExist:
        print(f'⚠️  User {username} not found')

print("\n✅ All child admin passwords updated!")
print("\nYou can now login with:")
print("  - ant / admin123")
print("  - arc / admin123")
print("  - soe / admin123")
print("  - him / admin123")
