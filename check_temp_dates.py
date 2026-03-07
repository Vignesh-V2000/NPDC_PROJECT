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
    HimanshWaterLevel
)
from stations_weather.views import get_weather_data_priority, format_date_ist
from django.utils import timezone
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

print("\n" + "="*100)
print("CHECKING ACTUAL DATA DATES & TIMES FOR TEMPERATURES")
print("="*100 + "\n")

today = timezone.now()
yesterday = today - timedelta(days=1)

print(f"Today UTC: {today}")
print(f"Yesterday UTC: {yesterday}\n")

# MAITRI
print("MAITRI:")
if table_exists('maitri_maitri'):
    maitri, was_11pm = get_weather_data_priority(MaitriWeatherData.objects.all(), 'date')
    if maitri:
        print(f"  Temperature: {maitri.temp}°C")
        print(f"  ACTUAL Date/Time in DB: {maitri.date}")
        hour = maitri.date.hour
        am_pm = "AM" if hour < 12 else "PM"
        print(f"  Time slot: Hour {hour} ({am_pm})")
        print(f"  From 11 PM slot: {was_11pm}")
        print(f"  Displayed as: {format_date_ist(maitri.date, display_as_11pm=True)}")
else:
    print(f"  Table not found")

print("\n" + "-"*100)

# BHARATI
print("BHARATI:")
if table_exists('imd_bharati'):
    bharati, was_11pm = get_weather_data_priority(BharatiWeatherData.objects.all(), 'obstime')
    if bharati:
        print(f"  Temperature: {bharati.tempr}°C")
        print(f"  ACTUAL Date/Time in DB: {bharati.obstime}")
        hour = bharati.obstime.hour
        am_pm = "AM" if hour < 12 else "PM"
        print(f"  Time slot: Hour {hour} ({am_pm})")
        print(f"  From 11 PM slot: {was_11pm}")
        print(f"  Displayed as: {format_date_ist(bharati.obstime, display_as_11pm=True)}")
else:
    print(f"  Table not found")

print("\n" + "-"*100)

# HIMADRI
print("HIMADRI:")
if table_exists('himadri_radiometer_surface'):
    himadri, was_11pm = get_weather_data_priority(HimadriWeatherData.objects.all(), 'date')
    if himadri:
        temp_celsius = himadri.temperature_celsius
        print(f"  Temperature: {temp_celsius}°C")
        print(f"  ACTUAL Date/Time in DB: {himadri.date}")
        hour = himadri.date.hour
        am_pm = "AM" if hour < 12 else "PM"
        print(f"  Time slot: Hour {hour} ({am_pm})")
        print(f"  From 11 PM slot: {was_11pm}")
        print(f"  Displayed as: {format_date_ist(himadri.date, display_as_11pm=True)}")
else:
    print(f"  Table not found")

print("\n" + "-"*100)

# HIMANSH
print("HIMANSH:")
if table_exists('himansh_water_level'):
    himansh, was_11pm = get_weather_data_priority(HimanshWaterLevel.objects.all(), 'date')
    if himansh:
        print(f"  Water Level: {himansh.water_level}")
        print(f"  ACTUAL Date/Time in DB: {himansh.date}")
        hour = himansh.date.hour if himansh.date else None
        if hour is not None:
            am_pm = "AM" if hour < 12 else "PM"
            print(f"  Time slot: Hour {hour} ({am_pm})")
        print(f"  From 11 PM slot: {was_11pm}")
        print(f"  Displayed as: {format_date_ist(himansh.date, display_as_11pm=True)}")
    else:
        print(f"  No data found")
else:
    print(f"  Table not found")

print("\n" + "="*100)
