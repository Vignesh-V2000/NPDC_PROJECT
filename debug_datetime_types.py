import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from stations_weather.models import MaitriWeatherData, BharatiWeatherData, HimadriWeatherData
from pytz import timezone as pytz_timezone
from datetime import datetime

IST = pytz_timezone('Asia/Kolkata')
UTC = pytz_timezone('UTC')

print("=" * 100)
print("DEBUGGING DATETIME TYPES AND CONVERSIONS")
print("=" * 100)

# Maitri
print("\n1. MAITRI:")
maitri = MaitriWeatherData.objects.all().order_by('-date').first()
if maitri:
    dt = maitri.date
    print(f"   Raw from DB: {dt}")
    print(f"   Type: {type(dt)}")
    print(f"   Has tzinfo: {dt.tzinfo is not None}")
    if dt.tzinfo:
        print(f"   Timezone: {dt.tzinfo}")
    
    # Test both conversion paths
    print("\n   If treated as naive UTC:")
    if dt.tzinfo is None:
        utc_dt = UTC.localize(dt)
        ist_time = utc_dt.astimezone(IST)
        print(f"     UTC: {utc_dt}")
        print(f"     IST: {ist_time}")
        print(f"     Formatted: {ist_time.strftime('%d %b %Y %I:%M %p')}")
    
    print("\n   If treated as already aware:")
    if dt.tzinfo:
        ist_time = dt.astimezone(IST)
        print(f"     IST: {ist_time}")
        print(f"     Formatted: {ist_time.strftime('%d %b %Y %I:%M %p')}")

# Bharati  
print("\n2. BHARATI:")
bharati = BharatiWeatherData.objects.all().order_by('-obstime').first()
if bharati:
    dt = bharati.obstime
    print(f"   Raw from DB: {dt}")
    print(f"   Type: {type(dt)}")
    print(f"   Has tzinfo: {dt.tzinfo is not None}")
    if dt.tzinfo:
        print(f"   Timezone: {dt.tzinfo}")
    
    print("\n   If treated as naive UTC:")
    if dt.tzinfo is None:
        utc_dt = UTC.localize(dt)
        ist_time = utc_dt.astimezone(IST)
        print(f"     UTC: {utc_dt}")
        print(f"     IST: {ist_time}")
        print(f"     Formatted: {ist_time.strftime('%d %b %Y %I:%M %p')}")
    
    print("\n   If treated as already aware:")
    if dt.tzinfo:
        ist_time = dt.astimezone(IST)
        print(f"     IST: {ist_time}")
        print(f"     Formatted: {ist_time.strftime('%d %b %Y %I:%M %p')}")

# Himadri
print("\n3. HIMADRI:")
himadri = HimadriWeatherData.objects.all().order_by('-date').first()
if himadri:
    dt = himadri.date
    print(f"   Raw from DB: {dt}")
    print(f"   Type: {type(dt)}")
    print(f"   Has tzinfo: {dt.tzinfo is not None}")
    if dt.tzinfo:
        print(f"   Timezone: {dt.tzinfo}")

print("\n" + "=" * 100)
print("DJANGO SETTINGS:")
print("=" * 100)
from django.conf import settings
print(f"USE_TZ: {settings.USE_TZ}")
print(f"TIME_ZONE: {settings.TIME_ZONE}")
