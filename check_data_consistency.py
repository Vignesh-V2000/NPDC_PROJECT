import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from stations_weather.models import MaitriWeatherData, BharatiWeatherData, HimadriWeatherData
from django.db import connection
from datetime import datetime, date

print("=" * 100)
print("CHECKING FOR DATA INCONSISTENCY")
print("=" * 100)

# Check via ORM multiple times
print("\n1. MAITRI - Multiple ORM queries:")
for i in range(3):
    maitri = MaitriWeatherData.objects.all().order_by('-date').first()
    if maitri:
        print(f"   Query {i+1}: {maitri.date}")

# Check latest dates in DB
print("\n2. MAITRI - Raw SQL latest 5 records:")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT date FROM maitri_maitri 
        ORDER BY date DESC 
        LIMIT 5
    """)
    for i, (dt,) in enumerate(cursor.fetchall(), 1):
        print(f"   {i}. {dt}")

# Check if there are multiple March 6 records
print("\n3. MAITRI - All March 6 records:")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT date FROM maitri_maitri 
        WHERE DATE(date) = '2026-03-06'
        ORDER BY date DESC
    """)
    count = 0
    for (dt,) in cursor.fetchall():
        count += 1
        print(f"   {dt}")
    print(f"   Total March 6 records: {count}")

# Check Bharati
print("\n4. BHARATI - Raw SQL latest 5 records:")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT obstime FROM imd_bharati 
        ORDER BY obstime DESC 
        LIMIT 5
    """)
    for i, (dt,) in enumerate(cursor.fetchall(), 1):
        print(f"   {i}. {dt}")

# Check Himadri
print("\n5. HIMADRI - Raw SQL latest 5 records:")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT date FROM himadri_radiometer_surface 
        ORDER BY date DESC 
        LIMIT 5
    """)
    for i, (dt,) in enumerate(cursor.fetchall(), 1):
        print(f"   {i}. {dt}")

print("\n" + "=" * 100)
