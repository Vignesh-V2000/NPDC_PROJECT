import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from stations_weather.models import MaitriWeatherData, HimadriWeatherData
from django.db import connection
from pytz import timezone as pytz_timezone
from datetime import datetime

IST = pytz_timezone('Asia/Kolkata')
UTC = pytz_timezone('UTC')

print("=" * 100)
print("COMPARISON: Database Raw vs Django ORM vs Formatted")
print("=" * 100)

# Maitri
print("\n" + "-" * 100)
print("MAITRI STATION")
print("-" * 100)

# Raw SQL
print("\n1. RAW SQL (direct from database):")
with connection.cursor() as cursor:
    cursor.execute("SELECT date FROM maitri_maitri ORDER BY date DESC LIMIT 1")
    raw_db = cursor.fetchone()[0]
    print(f"   {raw_db}")

# Django ORM
print("\n2. Django ORM Query:")
maitri = MaitriWeatherData.objects.all().order_by('-date').first()
if maitri:
    print(f"   {maitri.date}")
    print(f"   Type: {type(maitri.date)}")
    print(f"   Tzinfo: {maitri.date.tzinfo}")
    print(f"   ISO: {maitri.date.isoformat()}")
    
    # What the API returns
    print("\n3. When treated as UTC and converted to IST:")
    if maitri.date.tzinfo is None:
        utc_aware = UTC.localize(maitri.date)
        ist_time = utc_aware.astimezone(IST)
        print(f"   UTC: {utc_aware}")
        print(f"   IST: {ist_time}")
        print(f"   Formatted: {ist_time.strftime('%d %b %Y %I:%M %p')}")
    
    print("\n4. When treated as IST (already naive):")
    ist_time = IST.localize(maitri.date)
    print(f"   IST: {ist_time}")
    print(f"   Formatted: {ist_time.strftime('%d %b %Y %I:%M %p')}")

# Himadri
print("\n" + "-" * 100)
print("HIMADRI STATION")
print("-" * 100)

print("\n1. RAW SQL (direct from database):")
with connection.cursor() as cursor:
    cursor.execute("SELECT date FROM himadri_radiometer_surface ORDER BY date DESC LIMIT 1")
    raw_db = cursor.fetchone()[0]
    print(f"   {raw_db}")

print("\n2. Django ORM Query:")
himadri = HimadriWeatherData.objects.all().order_by('-date').first()
if himadri:
    print(f"   {himadri.date}")
    print(f"   Type: {type(himadri.date)}")
    print(f"   Tzinfo: {himadri.date.tzinfo}")
    
    print("\n3. When treated as UTC and converted to IST:")
    if himadri.date.tzinfo is None:
        utc_aware = UTC.localize(himadri.date)
        ist_time = utc_aware.astimezone(IST)
        print(f"   UTC: {utc_aware}")
        print(f"   IST: {ist_time}")
        print(f"   Formatted: {ist_time.strftime('%d %b %Y %I:%M %p')}")
