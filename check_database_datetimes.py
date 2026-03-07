"""
Script to check the actual datetime values stored in weather station tables
This helps diagnose the timezone issue without modifying anything
"""

import os
import django
from datetime import datetime
from pytz import timezone as pytz_timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.db import connection
from stations_weather.models import MaitriWeatherData, BharatiWeatherData, HimadriWeatherData

print("=" * 100)
print("DATABASE DATETIME VALUES CHECK")
print("=" * 100)

IST = pytz_timezone('Asia/Kolkata')
UTC = pytz_timezone('UTC')

# Check each table
tables_to_check = [
    {
        'name': 'Maitri',
        'model': MaitriWeatherData,
        'date_field': 'date',
        'table': 'maitri_maitri'
    },
    {
        'name': 'Bharati', 
        'model': BharatiWeatherData,
        'date_field': 'date',
        'table': 'imd_bharati'
    },
    {
        'name': 'Himadri',
        'model': HimadriWeatherData,
        'date_field': 'date',
        'table': 'himadri_radiometer_surface'
    }
]

for table_info in tables_to_check:
    print(f"\n{'='*100}")
    print(f"TABLE: {table_info['name']} ({table_info['table']})")
    print(f"{'='*100}")
    
    try:
        # Get latest record
        latest = table_info['model'].objects.all().order_by('-' + table_info['date_field']).first()
        
        if latest:
            dt = getattr(latest, table_info['date_field'])
            print(f"\nLatest record datetime object:")
            print(f"  Raw datetime: {dt}")
            print(f"  Type: {type(dt)}")
            print(f"  Has timezone info: {dt.tzinfo is not None}")
            if dt.tzinfo:
                print(f"  Timezone: {dt.tzinfo}")
            
            print(f"\nISO format: {dt.isoformat()}")
            
            # Raw SQL query to see what's in the database
            with connection.cursor() as cursor:
                col_name = table_info['date_field']
                sql = f"SELECT {col_name} FROM {table_info['table']} ORDER BY {col_name} DESC LIMIT 1"
                cursor.execute(sql)
                result = cursor.fetchone()
                if result:
                    print(f"\nDirect SQL query result:")
                    print(f"  Raw value from DB: {result[0]}")
                    print(f"  Type: {type(result[0])}")
        else:
            print("  ❌ No data in table")
    
    except Exception as e:
        print(f"  ❌ Error: {e}")

print(f"\n{'='*100}")
print("DJANGO SETTINGS CHECK")
print(f"{'='*100}")
from django.conf import settings
print(f"USE_TZ: {settings.USE_TZ}")
print(f"TIME_ZONE: {settings.TIME_ZONE}")
print(f"DB Engine: {settings.DATABASES['default']['ENGINE']}")

print(f"\n{'='*100}")
print("CURRENT SERVER TIME")
print(f"{'='*100}")
from django.utils import timezone
now = timezone.now()
print(f"Django timezone.now(): {now}")
print(f"Timezone: {now.tzinfo}")

# Check if displayed time has 24 hour offset
print(f"\n{'='*100}")
print("TIME OFFSET ANALYSIS")
print(f"{'='*100}")
print("""
If database shows: 5 March 2026 11:00 PM
And website shows: 6 March 2026 11:00 PM

This indicates a 24-hour date offset.

Possible causes:
1. Data processing scripts are adding 24 hours when storing IST
2. Website is interpreting IST as UTC and adding 5:30 hours (past midnight)
3. There's a date boundary issue in data processing
""")
