#!/usr/bin/env python
import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.utils import timezone

today = timezone.now()
yesterday = today - timedelta(days=1)

print(f"Today: {today}")
print(f"Yesterday: {yesterday}")
print(f"Today's date only: {today.date()}")
print(f"Yesterday's date only: {yesterday.date()}")
