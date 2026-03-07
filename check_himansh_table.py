#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from stations_weather.models import HimanshWaterLevel
from django.db import connection

print("\n" + "="*80)
print("CHECKING HIMANSH TABLE STATUS")
print("="*80 + "\n")

# Check if table exists
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = 'himansh_water_level'
        )
    """)
    table_exists = cursor.fetchone()[0]

if table_exists:
    print("✓ Table 'himansh_water_level' EXISTS\n")
    
    # Count total records
    total_count = HimanshWaterLevel.objects.count()
    print(f"Total records in table: {total_count}")
    
    if total_count > 0:
        print("\nLatest 5 records:")
        print("-" * 80)
        for record in HimanshWaterLevel.objects.all().order_by('-date')[:5]:
            print(f"  Date: {record.date}")
            print(f"  Water Level: {record.water_level}")
            print()
    else:
        print("\n⚠ Table is EMPTY - no records found")
else:
    print("✗ Table 'himansh_water_level' DOES NOT EXIST")

print("="*80)
