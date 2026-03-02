#!/usr/bin/env python
"""Inspect a user record via command line"""
import os, django, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','npdc_site.settings')
django.setup()
from django.contrib.auth.models import User
if len(sys.argv) < 2:
    print("Usage: python inspect_user.py <username>")
    sys.exit(1)
username = sys.argv[1]
try:
    u = User.objects.get(username=username)
    print('username:', u.username)
    print('email:', u.email)
    print('is_active:', u.is_active, 'is_staff:', u.is_staff, 'is_superuser:', u.is_superuser)
    print('password hash:', u.password)
    print('check password admin123 ->', u.check_password('admin123'))
except User.DoesNotExist:
    print(f'User {username} not found')
