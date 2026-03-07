#!/usr/bin/env python
import os
import django
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

import requests
from django.utils import timezone


def test_api():
    """Test the weather API endpoint"""
    print("\n" + "="*80)
    print("TESTING WEATHER API WITH 9-11 PM PRIORITY LOGIC")
    print("="*80 + "\n")
    
    # Make request to local API
    url = "http://localhost:8000/weather/api/weather/"
    try:
        response = requests.get(url)
        data = response.json()
        
        print("✓ API Response Status:", response.status_code)
        print("\nData returned:")
        
        if 'data' in data:
            for station, info in data['data'].items():
                print(f"\n{station.upper()}:")
                print(f"  Name: {info.get('name')}")
                print(f"  Temperature: {info.get('temperature')}°C")
                print(f"  Formatted Date: {info.get('formatted_date')}")
                print(f"  Raw Date: {info.get('date')}")
        else:
            print("No data returned")
            
    except requests.exceptions.ConnectionError:
        print("✗ ERROR: Cannot connect to API at", url)
        print("Make sure Django development server is running: python manage.py runserver")
    except Exception as e:
        print(f"✗ ERROR: {e}")


def test_direct_models():
    """Test the data directly from models with the new logic"""
    print("\n" + "="*80)
    print("TESTING DIRECT MODEL QUERIES WITH 9-11 PM PRIORITY")
    print("="*80 + "\n")
    
    from stations_weather.models import (
        MaitriWeatherData,
        BharatiWeatherData,
        HimadriWeatherData,
        HimanshWaterLevel
    )
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
    
    yesterday = timezone.now() - timedelta(days=1)
    print(f"Yesterday's date: {yesterday.date()}\n")
    
    # Test Maitri
    print("MAITRI:")
    if table_exists('maitri_maitri'):
        maitri, was_11pm = get_weather_data_priority(
            MaitriWeatherData.objects.all(),
            'date'
        )
        if maitri:
            print(f"  Data found: YES")
            print(f"  From 11 PM slot: {was_11pm}")
            print(f"  Actual time: {maitri.date}")
            print(f"  Displayed as: {format_date_ist(maitri.date, display_as_11pm=True)}")
            print(f"  Temperature: {maitri.temp}°C")
        else:
            print(f"  Data found: NO")
    else:
        print(f"  Table not found")
    
    # Test Bharati
    print("\nBHARATI:")
    if table_exists('imd_bharati'):
        bharati, was_11pm = get_weather_data_priority(
            BharatiWeatherData.objects.all(),
            'obstime'
        )
        if bharati:
            print(f"  Data found: YES")
            print(f"  From 11 PM slot: {was_11pm}")
            print(f"  Actual time: {bharati.obstime}")
            print(f"  Displayed as: {format_date_ist(bharati.obstime, display_as_11pm=True)}")
            print(f"  Temperature: {bharati.tempr}°C")
        else:
            print(f"  Data found: NO")
    else:
        print(f"  Table not found")
    
    # Test Himadri
    print("\nHIMADRI:")
    if table_exists('himadri_radiometer_surface'):
        himadri, was_11pm = get_weather_data_priority(
            HimadriWeatherData.objects.all(),
            'date'
        )
        if himadri:
            print(f"  Data found: YES")
            print(f"  From 11 PM slot: {was_11pm}")
            print(f"  Actual time: {himadri.date}")
            print(f"  Displayed as: {format_date_ist(himadri.date, display_as_11pm=True)}")
            print(f"  Temperature: {himadri.temperature_celsius}°C")
        else:
            print(f"  Data found: NO")
    else:
        print(f"  Table not found")
    
    # Test Himansh
    print("\nHIMANSH:")
    if table_exists('himansh_water_level'):
        himansh, was_11pm = get_weather_data_priority(
            HimanshWaterLevel.objects.all(),
            'date'
        )
        if himansh:
            print(f"  Data found: YES")
            print(f"  From 11 PM slot: {was_11pm}")
            print(f"  Actual time: {himansh.date}")
            print(f"  Displayed as: {format_date_ist(himansh.date, display_as_11pm=True)}")
            print(f"  Water level: {himansh.water_level}")
        else:
            print(f"  Data found: NO")
    else:
        print(f"  Table not found")


if __name__ == '__main__':
    test_direct_models()
    print("\n" + "-"*80)
    print("To test the API endpoint, start the Django dev server:")
    print("  python manage.py runserver")
    print("Then run: python test_priority_9to11pm.py")
    print("-"*80 + "\n")
