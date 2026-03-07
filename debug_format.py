#!/usr/bin/env python
import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.utils import timezone
from stations_weather.views import format_date_ist

today = timezone.now()
yesterday = today - timedelta(days=1)

print(f"Today (UTC): {today}")
print(f"Yesterday (UTC): {yesterday}")

# Create display date as done in the API
display_date = yesterday.replace(hour=23, minute=0, second=0, microsecond=0)
print(f"\nDisplay date (UTC): {display_date}")

# Format it
formatted = format_date_ist(display_date, display_as_11pm=True)
print(f"Formatted: {formatted}")

# Let's also test with just the date object
yesterday_date = yesterday.date()
print(f"\nYesterday date: {yesterday_date}")
