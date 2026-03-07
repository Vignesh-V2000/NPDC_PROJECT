#!/usr/bin/env python
import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from stations_weather.models import MaitriWeatherData, BharatiWeatherData
from django.utils import timezone
from django.db.models import Q

print("\n" + "="*80)
print("DEBUGGING PM ONLY FILTER")
print("="*80 + "\n")

yesterday = timezone.now() - timedelta(days=1)
print(f"Yesterday's date: {yesterday.date()}\n")

# Show all Maitri data
print("ALL MAITRI DATA:")
all_maitri = MaitriWeatherData.objects.all().order_by('-date')[:10]
for record in all_maitri:
    hour = record.date.hour
    am_pm = "AM" if hour < 12 else "PM"
    print(f"  {record.date} (Hour {hour}: {am_pm})")

# Test PM filter
print("\nMAITRI DATA IN PM RANGE (12:00 onwards):")
pm_filter = Q()
for hour in range(12, 24):
    hour_start = yesterday.replace(hour=hour, minute=0, second=0, microsecond=0)
    hour_end = yesterday.replace(hour=hour, minute=59, second=59, microsecond=999999)
    pm_filter |= Q(date__gte=hour_start, date__lte=hour_end)

pm_maitri = MaitriWeatherData.objects.filter(pm_filter).order_by('-date')
print(f"  Found {pm_maitri.count()} records")
for record in pm_maitri:
    hour = record.date.hour
    am_pm = "AM" if hour < 12 else "PM"
    print(f"    {record.date} (Hour {hour}: {am_pm})")

# Show all Bharati data
print("\n" + "-"*80)
print("ALL BHARATI DATA:")
all_bharati = BharatiWeatherData.objects.all().order_by('-obstime')[:10]
for record in all_bharati:
    hour = record.obstime.hour
    am_pm = "AM" if hour < 12 else "PM"
    print(f"  {record.obstime} (Hour {hour}: {am_pm})")

# Test PM filter for Bharati
print("\nBHARATI DATA IN PM RANGE (12:00 onwards):")
pm_filter_bharati = Q()
for hour in range(12, 24):
    hour_start = yesterday.replace(hour=hour, minute=0, second=0, microsecond=0)
    hour_end = yesterday.replace(hour=hour, minute=59, second=59, microsecond=999999)
    pm_filter_bharati |= Q(obstime__gte=hour_start, obstime__lte=hour_end)

pm_bharati = BharatiWeatherData.objects.filter(pm_filter_bharati).order_by('-obstime')
print(f"  Found {pm_bharati.count()} records")
for record in pm_bharati:
    hour = record.obstime.hour
    am_pm = "AM" if hour < 12 else "PM"
    print(f"    {record.obstime} (Hour {hour}: {am_pm})")

print("\n" + "="*80)
