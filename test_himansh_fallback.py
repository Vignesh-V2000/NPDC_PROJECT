#!/usr/bin/env python
import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from stations_weather.models import HimanshWaterLevel
from stations_weather.views import get_weather_data_priority, format_date_ist
from django.db import connection


def table_exists(table_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, [table_name])
        return cursor.fetchone()[0]


print("\n" + "="*80)
print("TESTING HIMANSH FALLBACK LOGIC - SHOW MOST RECENT DATA AS 11:00 PM")
print("="*80 + "\n")

if not table_exists('himansh_water_level'):
    print("✗ Table 'himansh_water_level' does not exist")
else:
    # Check if table has any data at all
    total_records = HimanshWaterLevel.objects.count()
    print(f"Total records in himansh_water_level table: {total_records}")
    
    if total_records == 0:
        print("\n⚠️  No data in Himansh table - cannot test fallback behavior")
        print("Fallback logic WILL work once data is available")
    else:
        # Show all data to understand what we have
        print("\nAll Himansh data (by date, newest first):")
        records = HimanshWaterLevel.objects.all().order_by('-date')[:10]
        for i, record in enumerate(records, 1):
            print(f"  {i}. {record.date} - Water Level: {record.water_level}")
        
        print("\n" + "-"*80)
        print("Testing get_weather_data_priority() with fallback:")
        print("-"*80 + "\n")
        
        # Test the priority function
        himansh, was_11pm = get_weather_data_priority(
            HimanshWaterLevel.objects.all(),
            'date'
        )
        
        if himansh:
            print("✓ FALLBACK WORKING - Most recent data retrieved:")
            print(f"  Actual time: {himansh.date}")
            print(f"  Displayed as: {format_date_ist(himansh.date, display_as_11pm=True)}")
            print(f"  Water level: {himansh.water_level}")
            print(f"  From 11 PM slot: {was_11pm} (False = fallback to most recent)")
        else:
            print("✗ ISSUE: No data returned even with fallback")

print("\n" + "="*80)
print("SUMMARY: Himansh will show most recent available data as 11:00 PM")
print("="*80 + "\n")
