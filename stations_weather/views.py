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
    HimanshWeatherData,
    Last24HrsData
)

# Indian Standard Time (UTC+5:30)
IST = pytz_timezone('Asia/Kolkata')


def convert_to_ist(dt):
    """Convert datetime to IST
    
    Database stores naive datetimes that are already in IST format.
    We just need to localize them to the IST timezone without conversion.
    """
    if dt is None:
        return None
    
    if dt.tzinfo is None:
        # Naive datetime - database stores as IST, so just localize
        return IST.localize(dt)
    else:
        # Already timezone-aware - convert to IST
        return dt.astimezone(IST)


def format_date_ist(dt, display_as_11pm=False):
    """Format datetime in IST
    
    Args:
        dt: datetime object to format
        display_as_11pm: If True, always show time as 11:00 PM regardless of actual time
    """
    if dt is None:
        return 'N/A'
    ist_dt = convert_to_ist(dt)
    
    if display_as_11pm:
        # Replace time with 11:00 PM
        ist_dt = ist_dt.replace(hour=23, minute=0, second=0, microsecond=0)
    
    return ist_dt.strftime('%d %b %Y %I:%M %p')


def get_weather_data_priority(queryset, date_field_name):
    """
    Get weather data with priority: 11 PM → 10 PM → 9 PM (PM only)
    Fallback to most recent PM data (12:00 PM onwards, any date)
    
    Args:
        queryset: Base Django queryset with date filtering already applied
        date_field_name: Name of the date field ('date' or 'obstime', etc.)
    
    Returns:
        tuple: (data_object, was_found_at_11pm) where was_found_at_11pm is True if data is from 11 PM slot
    """
    yesterday = timezone.now() - timedelta(days=1)
    
    # Try 11 PM on yesterday (23:00-23:59)
    time_11pm_start = yesterday.replace(hour=23, minute=0, second=0, microsecond=0)
    time_11pm_end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    filter_11pm = {f'{date_field_name}__gte': time_11pm_start, f'{date_field_name}__lte': time_11pm_end}
    data = queryset.filter(**filter_11pm).order_by(f'-{date_field_name}').first()
    if data:
        return data, True
    
    # Try 10 PM on yesterday (22:00-22:59)
    time_10pm_start = yesterday.replace(hour=22, minute=0, second=0, microsecond=0)
    time_10pm_end = yesterday.replace(hour=22, minute=59, second=59, microsecond=999999)
    filter_10pm = {f'{date_field_name}__gte': time_10pm_start, f'{date_field_name}__lte': time_10pm_end}
    data = queryset.filter(**filter_10pm).order_by(f'-{date_field_name}').first()
    if data:
        return data, False
    
    # Try 9 PM on yesterday (21:00-21:59)
    time_9pm_start = yesterday.replace(hour=21, minute=0, second=0, microsecond=0)
    time_9pm_end = yesterday.replace(hour=21, minute=59, second=59, microsecond=999999)
    filter_9pm = {f'{date_field_name}__gte': time_9pm_start, f'{date_field_name}__lte': time_9pm_end}
    data = queryset.filter(**filter_9pm).order_by(f'-{date_field_name}').first()
    if data:
        return data, False
    
    # Fallback: Get most recent PM data (12:00 PM onwards, any date)
    # Only include data with hour >= 12 (noon or later)
    from django.db.models import Q
    
    pm_filter = Q()
    for hour in range(12, 24):
        pm_filter |= Q(**{f'{date_field_name}__hour': hour})
    
    data = queryset.filter(pm_filter).order_by(f'-{date_field_name}').first()
    if data:
        return data, False
    
    # If still no PM data found, return latest data regardless of time
    data = queryset.all().order_by(f'-{date_field_name}').first()
    return data, False


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
    Returns temperature and timestamp for each station
    Shows yesterday's 9-11 PM data (priority: 11 PM → 10 PM → 9 PM)
    All stations display their actual recorded timestamp.
    """
    from datetime import timedelta
    
    try:
        stations_data = {}
        
        # Maitri (Antarctica)
        if table_exists('maitri_maitri'):
            try:
                maitri, was_11pm = get_weather_data_priority(
                    MaitriWeatherData.objects.all(),
                    'date'
                )
                
                if maitri:
                    stations_data['maitri'] = {
                        'name': 'Antarctica - Maitri',
                        'temperature': round(maitri.temp, 1) if maitri.temp else None,
                        'humidity': round(maitri.rh, 1) if maitri.rh else None,
                        'pressure': round(maitri.ap, 1) if maitri.ap else None,
                        'wind_speed': round(maitri.ws, 1) if maitri.ws else None,
                        'wind_direction': round(maitri.wd, 1) if maitri.wd else None,
                        'date': maitri.date.isoformat() if maitri.date else None,
                        'formatted_date': format_date_ist(maitri.date),
                    }
            except Exception as e:
                print(f"Error fetching Maitri data: {e}")
        
        # Bharati (Antarctica)
        if table_exists('imd_bharati'):
            try:
                bharati, was_11pm = get_weather_data_priority(
                    BharatiWeatherData.objects.all(),
                    'obstime'
                )
                
                if bharati:
                    stations_data['bharati'] = {
                        'name': 'Antarctica - Bharati',
                        'temperature': round(bharati.tempr, 1) if bharati.tempr else None,
                        'humidity': round(bharati.rh, 1) if bharati.rh else None,
                        'pressure': round(bharati.ap, 1) if bharati.ap else None,
                        'wind_speed': round(bharati.ws, 1) if bharati.ws else None,
                        'wind_direction': round(bharati.wd, 1) if bharati.wd else None,
                        'date': bharati.obstime.isoformat() if bharati.obstime else None,
                        'formatted_date': format_date_ist(bharati.obstime),
                    }
            except Exception as e:
                print(f"Error fetching Bharati data: {e}")
        
        # Himadri (Arctic)
        if table_exists('himadri_radiometer_surface'):
            try:
                himadri, was_11pm = get_weather_data_priority(
                    HimadriWeatherData.objects.all(),
                    'date'
                )
                
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
        
        # Himansh (Himalaya)
        if table_exists('himansh_himansh'):
            try:
                himansh, was_11pm = get_weather_data_priority(
                    HimanshWeatherData.objects.all(),
                    'date'
                )
                
                if himansh:
                    stations_data['himansh'] = {
                        'name': 'Himalaya - Himansh',
                        'temperature': round(himansh.air_temp, 1) if himansh.air_temp else None,
                        'humidity': round(himansh.rh, 1) if himansh.rh else None,
                        'pressure': round(himansh.ap, 1) if himansh.ap else None,
                        'wind_speed': round(himansh.ws, 1) if himansh.ws else None,
                        'wind_direction': round(himansh.wd, 1) if himansh.wd else None,
                        'date': himansh.date.isoformat() if himansh.date else None,
                        'formatted_date': format_date_ist(himansh.date),
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
    Shows yesterday's 9-11 PM data (priority: 11 PM → 10 PM → 9 PM)
    All stations display their actual recorded timestamp.
    """
    from datetime import timedelta
    
    try:
        station_code = station_code.lower()
        
        if station_code == 'maitri' and table_exists('maitri_maitri'):
            try:
                maitri, was_11pm = get_weather_data_priority(
                    MaitriWeatherData.objects.all(),
                    'date'
                )
                
                if maitri:
                    return JsonResponse({
                        'status': 'success',
                        'station': 'Maitri',
                        'temperature': round(maitri.temp, 1) if maitri.temp else None,
                        'humidity': round(maitri.rh, 1) if maitri.rh else None,
                        'pressure': round(maitri.ap, 1) if maitri.ap else None,
                        'wind_speed': round(maitri.ws, 1) if maitri.ws else None,
                        'wind_direction': round(maitri.wd, 1) if maitri.wd else None,
                        'date': maitri.date.isoformat() if maitri.date else None,
                        'formatted_date': format_date_ist(maitri.date),
                    })
            except Exception as e:
                print(f"Error fetching Maitri data: {e}")
        
        elif station_code == 'bharati' and table_exists('imd_bharati'):
            try:
                bharati, was_11pm = get_weather_data_priority(
                    BharatiWeatherData.objects.all(),
                    'obstime'
                )
                
                if bharati:
                    return JsonResponse({
                        'status': 'success',
                        'station': 'Bharati',
                        'temperature': round(bharati.tempr, 1) if bharati.tempr else None,
                        'humidity': round(bharati.rh, 1) if bharati.rh else None,
                        'pressure': round(bharati.ap, 1) if bharati.ap else None,
                        'wind_speed': round(bharati.ws, 1) if bharati.ws else None,
                        'wind_direction': round(bharati.wd, 1) if bharati.wd else None,
                        'date': bharati.obstime.isoformat() if bharati.obstime else None,
                        'formatted_date': format_date_ist(bharati.obstime),
                    })
            except Exception as e:
                print(f"Error fetching Bharati data: {e}")
        
        elif station_code == 'himadri' and table_exists('himadri_radiometer_surface'):
            try:
                himadri, was_11pm = get_weather_data_priority(
                    HimadriWeatherData.objects.all(),
                    'date'
                )
                
                if himadri:
                    temp_celsius = himadri.temperature_celsius if himadri.temperature else None
                    return JsonResponse({
                        'status': 'success',
                        'station': 'Himadri',
                        'temperature': round(temp_celsius, 1) if temp_celsius else None,
                        'humidity': round(himadri.relative_humidity, 1) if himadri.relative_humidity else None,
                        'pressure': round(himadri.air_pressure, 1) if himadri.air_pressure else None,
                        'date': himadri.date.isoformat() if himadri.date else None,
                        'formatted_date': format_date_ist(himadri.date),
                    })
            except Exception as e:
                print(f"Error fetching Himadri data: {e}")
        
        elif station_code == 'himansh' and table_exists('himansh_himansh'):
            try:
                himansh, was_11pm = get_weather_data_priority(
                    HimanshWeatherData.objects.all(),
                    'date'
                )
                
                if himansh:
                    return JsonResponse({
                        'status': 'success',
                        'station': 'Himansh',
                        'temperature': round(himansh.air_temp, 1) if himansh.air_temp else None,
                        'humidity': round(himansh.rh, 1) if himansh.rh else None,
                        'pressure': round(himansh.ap, 1) if himansh.ap else None,
                        'wind_speed': round(himansh.ws, 1) if himansh.ws else None,
                        'wind_direction': round(himansh.wd, 1) if himansh.wd else None,
                        'date': himansh.date.isoformat() if himansh.date else None,
                        'formatted_date': format_date_ist(himansh.date),
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

