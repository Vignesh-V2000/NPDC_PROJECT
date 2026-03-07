#!/usr/bin/env python
import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from stations_weather.models import (
    MaitriWeatherData,
    BharatiWeatherData,
    HimadriWeatherData,
)
from stations_weather.views import get_weather_data_priority, format_date_ist
from django.utils import timezone

print("\n" + "="*80)
print("VERIFYING TEMPERATURE-DATE MATCHING")
print("="*80 + "\n")

yesterday = timezone.now() - timedelta(days=1)
print(f"Yesterday's date: {yesterday.date()}\n")

# Test Maitri
print("MAITRI - Checking all data to verify temperature-date match:")
print("-" * 80)
maitri_all = MaitriWeatherData.objects.all().order_by('-date')[:10]
print(f"{'Date/Time':<30} {'Temp':<8} {'RH':<8}")
print("-" * 80)
for record in maitri_all:
    print(f"{str(record.date):<30} {str(record.temp):<8} {str(record.rh):<8}")

print("\n" + "="*80)
print("NOW TESTING get_weather_data_priority() RESULT:")
print("="*80 + "\n")

maitri, was_11pm = get_weather_data_priority(
    MaitriWeatherData.objects.all(),
    'date'
)

if maitri:
    print("MAITRI Selected Record:")
    print(f"  Date/Time: {maitri.date}")
    print(f"  Temperature: {maitri.temp}°C")
    print(f"  Humidity: {maitri.rh}%")
    print(f"  Displayed as: {format_date_ist(maitri.date, display_as_11pm=True)}")
    
    # Verify in database
    print("\nDirect Database Lookup to Verify:")
    verify = MaitriWeatherData.objects.filter(date=maitri.date).first()
    if verify:
        print(f"  ✓ Record found in database at {verify.date}")
        print(f"  Temperature in DB: {verify.temp}°C")
        print(f"  Match: {'✓ YES' if verify.temp == maitri.temp else '✗ NO'}")
    else:
        print(f"  ✗ Record NOT found in database for {maitri.date}")

print("\n" + "="*80)
print("BHARATI - Checking all data:")
print("-" * 80)
bharati_all = BharatiWeatherData.objects.all().order_by('-obstime')[:10]
print(f"{'Date/Time':<30} {'Temp':<8} {'RH':<8}")
print("-" * 80)
for record in bharati_all:
    print(f"{str(record.obstime):<30} {str(record.tempr):<8} {str(record.rh):<8}")

print("\n" + "="*80)
print("NOW TESTING get_weather_data_priority() RESULT FOR BHARATI:")
print("="*80 + "\n")

bharati, was_11pm = get_weather_data_priority(
    BharatiWeatherData.objects.all(),
    'obstime'
)

if bharati:
    print("BHARATI Selected Record:")
    print(f"  Date/Time: {bharati.obstime}")
    print(f"  Temperature: {bharati.tempr}°C")
    print(f"  Humidity: {bharati.rh}%")
    print(f"  Displayed as: {format_date_ist(bharati.obstime, display_as_11pm=True)}")
    
    # Verify in database
    print("\nDirect Database Lookup to Verify:")
    verify = BharatiWeatherData.objects.filter(obstime=bharati.obstime).first()
    if verify:
        print(f"  ✓ Record found in database at {verify.obstime}")
        print(f"  Temperature in DB: {verify.tempr}°C")
        print(f"  Match: {'✓ YES' if verify.tempr == bharati.tempr else '✗ NO'}")
    else:
        print(f"  ✗ Record NOT found in database for {bharati.obstime}")

print("\n" + "="*80)
