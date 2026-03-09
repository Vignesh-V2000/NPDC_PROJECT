import logging
from datetime import timedelta

from django.http import JsonResponse
from django.utils import timezone
from django.db import connections

logger = logging.getLogger(__name__)


def table_exists(table_name):
    """Check if a table exists in any of the configured databases."""
    for db_alias in ['default', 'data_analysis', 'polardb']:
        try:
            from django.conf import settings
            if db_alias not in settings.DATABASES:
                continue
            conn = connections[db_alias]
            cursor = conn.cursor()
            cursor.execute(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s);",
                [table_name]
            )
            if cursor.fetchone()[0]:
                return True
        except Exception:
            continue
    return False


def get_weather_data_priority(model_class, date_field, temp_field, humidity_field=None,
                               pressure_field=None, wind_speed_field=None,
                               wind_direction_field=None, db_alias=None):
    """
    Fetch the most recent weather data from the given model.
    First tries to get yesterday's 9-11 PM data, then falls back to most recent record.
    """
    try:
        now_ist = timezone.now() + timedelta(hours=5, minutes=30)
        yesterday_ist = now_ist - timedelta(days=1)

        # Try to get yesterday's data between 9 PM and 11:59 PM
        start_time = yesterday_ist.replace(hour=21, minute=0, second=0, microsecond=0)
        end_time = yesterday_ist.replace(hour=23, minute=59, second=59, microsecond=999999)

        qs = model_class.objects.using(db_alias) if db_alias else model_class.objects.all()
        record = qs.filter(**{
            f'{date_field}__gte': start_time,
            f'{date_field}__lte': end_time,
        }).order_by(f'-{date_field}').first()

        # Fallback: get the absolute most recent record
        if not record:
            qs = model_class.objects.using(db_alias) if db_alias else model_class.objects.all()
            record = qs.order_by(f'-{date_field}').first()

        if not record:
            return None

        temp_value = getattr(record, temp_field, None)
        date_value = getattr(record, date_field, None)

        result = {
            'temperature': round(temp_value, 1) if temp_value is not None else None,
            'date': date_value.isoformat() if date_value else None,
            'formatted_date': date_value.strftime("%d %b %Y") if date_value else 'No Date',
        }

        if humidity_field:
            hum = getattr(record, humidity_field, None)
            result['humidity'] = round(hum, 1) if hum is not None else None

        if pressure_field:
            pres = getattr(record, pressure_field, None)
            result['pressure'] = round(pres, 1) if pres is not None else None

        if wind_speed_field:
            ws = getattr(record, wind_speed_field, None)
            result['wind_speed'] = round(ws, 1) if ws is not None else None

        if wind_direction_field:
            wd = getattr(record, wind_direction_field, None)
            result['wind_direction'] = round(wd, 1) if wd is not None else None

        return result

    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None


def weather_api(request):
    """API endpoint returning current weather data for all stations."""
    from .models import (
        MaitriWeatherData, BharatiWeatherData,
        HimadriWeatherData, HimanshWeatherData
    )
    from django.conf import settings

    data = {}

    # Maitri
    try:
        db = 'polardb' if 'polardb' in settings.DATABASES else None
        maitri = get_weather_data_priority(
            MaitriWeatherData, 'date', 'temp',
            humidity_field='rh', pressure_field='ap',
            wind_speed_field='ws', wind_direction_field='wd',
            db_alias=db
        )
        if maitri:
            maitri['name'] = 'Antarctica - Maitri'
            data['maitri'] = maitri
    except Exception as e:
        logger.error(f"Maitri error: {e}")

    # Bharati
    try:
        db = 'data_analysis' if 'data_analysis' in settings.DATABASES else None
        bharati = get_weather_data_priority(
            BharatiWeatherData, 'obstime', 'tempr',
            humidity_field='rh', pressure_field='ap',
            wind_speed_field='ws', wind_direction_field='wd',
            db_alias=db
        )
        if bharati:
            bharati['name'] = 'Antarctica - Bharati'
            data['bharati'] = bharati
    except Exception as e:
        logger.error(f"Bharati error: {e}")

    # Himadri
    try:
        db = 'polardb' if 'polardb' in settings.DATABASES else None
        himadri = get_weather_data_priority(
            HimadriWeatherData, 'date', 'temperature',
            humidity_field='relative_humidity', pressure_field='air_pressure',
            db_alias=db
        )
        if himadri and himadri.get('temperature') is not None:
            # Convert Kelvin to Celsius
            himadri['temperature'] = round(himadri['temperature'] - 273.15, 1)
            himadri['name'] = 'Arctic - Himadri'
            data['himadri'] = himadri
    except Exception as e:
        logger.error(f"Himadri error: {e}")

    # Himansh
    try:
        db = 'polardb' if 'polardb' in settings.DATABASES else None
        himansh = get_weather_data_priority(
            HimanshWeatherData, 'date', 'air_temp',
            humidity_field='rh', pressure_field='ap',
            wind_speed_field='ws', wind_direction_field='wd',
            db_alias=db
        )
        if himansh:
            himansh['name'] = 'Himalaya - Himansh'
            data['himansh'] = himansh
    except Exception as e:
        logger.error(f"Himansh error: {e}")

    return JsonResponse({'status': 'success', 'data': data})


def weather_station(request, station_code):
    """API endpoint returning weather data for a specific station."""
    from .models import (
        MaitriWeatherData, BharatiWeatherData,
        HimadriWeatherData, HimanshWeatherData
    )
    from django.conf import settings

    station_map = {
        'maitri': {
            'model': MaitriWeatherData, 'date_field': 'date', 'temp_field': 'temp',
            'humidity_field': 'rh', 'pressure_field': 'ap',
            'wind_speed_field': 'ws', 'wind_direction_field': 'wd',
            'name': 'Antarctica - Maitri',
            'db': 'polardb' if 'polardb' in settings.DATABASES else None,
        },
        'bharati': {
            'model': BharatiWeatherData, 'date_field': 'obstime', 'temp_field': 'tempr',
            'humidity_field': 'rh', 'pressure_field': 'ap',
            'wind_speed_field': 'ws', 'wind_direction_field': 'wd',
            'name': 'Antarctica - Bharati',
            'db': 'data_analysis' if 'data_analysis' in settings.DATABASES else None,
        },
        'himadri': {
            'model': HimadriWeatherData, 'date_field': 'date', 'temp_field': 'temperature',
            'humidity_field': 'relative_humidity', 'pressure_field': 'air_pressure',
            'name': 'Arctic - Himadri',
            'db': 'polardb' if 'polardb' in settings.DATABASES else None,
        },
        'himansh': {
            'model': HimanshWeatherData, 'date_field': 'date', 'temp_field': 'air_temp',
            'humidity_field': 'rh', 'pressure_field': 'ap',
            'wind_speed_field': 'ws', 'wind_direction_field': 'wd',
            'name': 'Himalaya - Himansh',
            'db': 'polardb' if 'polardb' in settings.DATABASES else None,
        },
    }

    if station_code not in station_map:
        return JsonResponse({'status': 'error', 'message': 'Station not found'}, status=404)

    config = station_map[station_code]
    result = get_weather_data_priority(
        config['model'], config['date_field'], config['temp_field'],
        humidity_field=config.get('humidity_field'),
        pressure_field=config.get('pressure_field'),
        wind_speed_field=config.get('wind_speed_field'),
        wind_direction_field=config.get('wind_direction_field'),
        db_alias=config.get('db'),
    )

    if result:
        if station_code == 'himadri' and result.get('temperature') is not None:
            result['temperature'] = round(result['temperature'] - 273.15, 1)
        result['name'] = config['name']
        return JsonResponse({'status': 'success', 'data': result})

    return JsonResponse({'status': 'error', 'message': 'No data available'}, status=404)
