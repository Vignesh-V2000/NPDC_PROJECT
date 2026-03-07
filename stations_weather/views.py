from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Max
from django.utils import timezone
from django.db import connection
from datetime import timedelta
import json
from pytz import timezone as pytz_timezone

from .models import (
    MaitriWeatherData,
    BharatiWeatherData,
    HimadriWeatherData,
    HimanshWaterLevel,
    Last24HrsData
)

# Indian Standard Time (UTC+5:30)
IST = pytz_timezone('Asia/Kolkata')


def convert_to_ist(dt):
    """Convert datetime to IST
    Handles both naive (local IST) and timezone-aware datetimes
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Naive datetime - database stores them as IST already (no conversion needed)
        return IST.localize(dt)
    else:
        # Timezone-aware datetime - convert to IST
        return dt.astimezone(IST)


def format_date_ist(dt):
    """Format datetime in IST"""
    if dt is None:
        return 'N/A'
    ist_dt = convert_to_ist(dt)
    return ist_dt.strftime('%d %b %Y %I:%M %p')


def table_exists(table_name):
    """Check if a table exists in the database"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, [table_name])
        return cursor.fetchone()[0]


@csrf_exempt
@require_GET
def weather_api(request):
    """
    API endpoint to get current weather data from all stations
    Returns latest temperature and timestamp for each station
    """
    try:
        stations_data = {}
        
        # Maitri (Antarctica)
        if table_exists('maitri_maitri'):
            try:
                maitri = MaitriWeatherData.objects.all().order_by('-date').first()
                if maitri:
                    stations_data['maitri'] = {
                        'name': 'Antarctica - Maitri',
                        'temperature': round(maitri.temperature, 1) if maitri.temperature else None,
                        'humidity': round(maitri.humidity, 1) if maitri.humidity else None,
                        'pressure': round(maitri.pressure, 1) if maitri.pressure else None,
                        'wind_speed': round(maitri.wind_speed, 1) if maitri.wind_speed else None,
                        'wind_direction': round(maitri.wind_direction, 1) if maitri.wind_direction else None,
                        'date': maitri.date.isoformat() if maitri.date else None,
                        'formatted_date': format_date_ist(maitri.date),
                    }
            except Exception as e:
                print(f"Error fetching Maitri data: {e}")
        
        # Bharati (Antarctica)
        if table_exists('imd_bharati'):
            try:
                bharati = BharatiWeatherData.objects.all().order_by('-date').first()
                if bharati:
                    stations_data['bharati'] = {
                        'name': 'Antarctica - Bharati',
                        'temperature': round(bharati.temperature, 1) if bharati.temperature else None,
                        'humidity': round(bharati.humidity, 1) if bharati.humidity else None,
                        'pressure': round(bharati.pressure, 1) if bharati.pressure else None,
                        'wind_speed': round(bharati.wind_speed, 1) if bharati.wind_speed else None,
                        'wind_direction': round(bharati.wind_direction, 1) if bharati.wind_direction else None,
                        'date': bharati.date.isoformat() if bharati.date else None,
                        'formatted_date': format_date_ist(bharati.date),
                    }
            except Exception as e:
                print(f"Error fetching Bharati data: {e}")
        
        # Himadri (Arctic)
        if table_exists('himadri_radiometer_surface'):
            try:
                himadri = HimadriWeatherData.objects.all().order_by('-date').first()
                if himadri:
                    # Convert Kelvin to Celsius
                    temp_celsius = himadri.temperature_celsius if himadri.temperature else None
                    stations_data['himadri'] = {
                        'name': 'Arctic - Himadri',
                        'temperature': round(temp_celsius, 1) if temp_celsius else None,
                        'humidity': round(himadri.relative_humidity, 1) if himadri.relative_humidity else None,
                        'pressure': round(himadri.air_pressure, 1) if himadri.air_pressure else None,
                        'date': himadri.date.isoformat() if himadri.date else None,
                        'formatted_date': format_date_ist(himadri.date),
                    }
            except Exception as e:
                print(f"Error fetching Himadri data: {e}")
        
        # Himansh (Himalaya) - Use latest available date
        if table_exists('himansh_water_level'):
            try:
                himansh = HimanshWaterLevel.objects.all().order_by('-date_time').first()
                if himansh:
                    stations_data['himansh'] = {
                        'name': 'Himalaya - Himansh',
                        'water_level': round(himansh.water_level, 2) if himansh.water_level else None,
                        'date': himansh.date_time.isoformat() if himansh.date_time else None,
                        'formatted_date': format_date_ist(himansh.date_time),
                    }
            except Exception as e:
                print(f"Error fetching Himansh data: {e}")
        
        return JsonResponse({
            'status': 'success',
            'data': stations_data,
            'timestamp': timezone.now().isoformat()
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@require_GET
def weather_station(request, station_code):
    """
    Get weather data for a specific station
    station_code: maitri, bharati, himadri, himansh
    """
    try:
        station_code = station_code.lower()
        
        if station_code == 'maitri' and table_exists('maitri_maitri'):
            try:
                data = MaitriWeatherData.objects.all().order_by('-date').first()
                if data:
                    return JsonResponse({
                        'status': 'success',
                        'station': 'Maitri',
                        'temperature': round(data.temperature, 1) if data.temperature else None,
                        'humidity': round(data.humidity, 1) if data.humidity else None,
                        'pressure': round(data.pressure, 1) if data.pressure else None,
                        'wind_speed': round(data.wind_speed, 1) if data.wind_speed else None,
                        'wind_direction': round(data.wind_direction, 1) if data.wind_direction else None,
                        'date': data.date.isoformat() if data.date else None,
                        'formatted_date': format_date_ist(data.date),
                    })
            except Exception as e:
                print(f"Error fetching Maitri data: {e}")
        
        elif station_code == 'bharati' and table_exists('imd_bharati'):
            try:
                data = BharatiWeatherData.objects.all().order_by('-date').first()
                if data:
                    return JsonResponse({
                        'status': 'success',
                        'station': 'Bharati',
                        'temperature': round(data.temperature, 1) if data.temperature else None,
                        'humidity': round(data.humidity, 1) if data.humidity else None,
                        'pressure': round(data.pressure, 1) if data.pressure else None,
                        'wind_speed': round(data.wind_speed, 1) if data.wind_speed else None,
                        'wind_direction': round(data.wind_direction, 1) if data.wind_direction else None,
                        'date': data.date.isoformat() if data.date else None,
                        'formatted_date': format_date_ist(data.date),
                    })
            except Exception as e:
                print(f"Error fetching Bharati data: {e}")
        
        elif station_code == 'himadri' and table_exists('himadri_radiometer_surface'):
            try:
                data = HimadriWeatherData.objects.all().order_by('-date').first()
                if data:
                    temp_celsius = data.temperature_celsius if data.temperature else None
                    return JsonResponse({
                        'status': 'success',
                        'station': 'Himadri',
                        'temperature': round(temp_celsius, 1) if temp_celsius else None,
                        'humidity': round(data.relative_humidity, 1) if data.relative_humidity else None,
                        'pressure': round(data.air_pressure, 1) if data.air_pressure else None,
                        'date': data.date.isoformat() if data.date else None,
                        'formatted_date': format_date_ist(data.date),
                    })
            except Exception as e:
                print(f"Error fetching Himadri data: {e}")
        
        elif station_code == 'himansh' and table_exists('himansh_water_level'):
            try:
                data = HimanshWaterLevel.objects.all().order_by('-date_time').first()
                if data:
                    return JsonResponse({
                        'status': 'success',
                        'station': 'Himansh',
                        'water_level': round(data.water_level, 2) if data.water_level else None,
                        'date': data.date_time.isoformat() if data.date_time else None,
                        'formatted_date': format_date_ist(data.date_time),
                    })
            except Exception as e:
                print(f"Error fetching Himansh data: {e}")
        
        return JsonResponse({
            'status': 'error',
            'message': 'Station not found or data tables not yet populated'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

