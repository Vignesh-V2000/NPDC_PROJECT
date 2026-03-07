"""
Test script to verify the timezone fix for weather station dates

Run with: python manage.py shell < test_timezone_fix.py
"""

import os
import django
from datetime import datetime
from pytz import timezone as pytz_timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from stations_weather.views import convert_to_ist, format_date_ist

IST = pytz_timezone('Asia/Kolkata')

print("=" * 80)
print("TIMEZONE FIX TEST")
print("=" * 80)

# Test Case 1: Naive datetime (as stored in database)
print("\n1. Testing naive datetime (5 March 20:00):")
naive_dt = datetime(2026, 3, 5, 20, 0, 0)  # No timezone info
print(f"   Input (naive): {naive_dt}")
converted = convert_to_ist(naive_dt)
print(f"   After convert_to_ist: {converted}")
print(f"   Formatted: {format_date_ist(naive_dt)}")
print(f"   Expected: Should show '05 Mar 2026 08:00 PM' (IST)")

# Test Case 2: Early morning date (5 March 02:00)
print("\n2. Testing early morning datetime (5 March 02:00):")
early_dt = datetime(2026, 3, 5, 2, 0, 0)  # No timezone info
print(f"   Input (naive): {early_dt}")
converted = convert_to_ist(early_dt)
print(f"   After convert_to_ist: {converted}")
print(f"   Formatted: {format_date_ist(early_dt)}")
print(f"   Expected: Should show '05 Mar 2026 02:00 AM' (IST)")

# Test Case 3: UTC-aware datetime (as Django might provide)
print("\n3. Testing UTC-aware datetime (5 March 20:00 UTC):")
utc_tz = pytz_timezone('UTC')
aware_dt = utc_tz.localize(datetime(2026, 3, 5, 20, 0, 0))
print(f"   Input (UTC): {aware_dt}")
converted = convert_to_ist(aware_dt)
print(f"   After convert_to_ist: {converted}")
print(f"   Formatted: {format_date_ist(aware_dt)}")
print(f"   Expected: Should show '05 Mar 2026 08:00 PM' (interpreting as IST)")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
print("\nNote: With the fix, dates stored as naive in the database")
print("will display correctly as IST without being off by 5:30 hours.")
