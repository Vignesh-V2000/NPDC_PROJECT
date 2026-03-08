import os
import django
from datetime import timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from stations_weather.models import (
    MaitriWeatherData,
    BharatiWeatherData,
    HimadriWeatherData,
    HimanshWeatherData
)
from django.db import connection

def check_table_exists(table_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, [table_name])
        return cursor.fetchone()[0]

def print_recent_records(model_class, station_name, date_field):
    table_name = model_class._meta.db_table
    print(f"\n{'='*50}")
    print(f"Checking {station_name} (Table: {table_name})")
    print(f"{'='*50}")
    
    if not check_table_exists(table_name):
        print(f"❌ Table '{table_name}' does not exist in the database.")
        return

    # Calculate 3 days ago from now
    three_days_ago = timezone.now() - timedelta(days=3)
    print(f"Fetching records from: {three_days_ago.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Filter records dynamically based on the date field
    filter_kwargs = {f"{date_field}__gte": three_days_ago}
    recent_records = model_class.objects.filter(**filter_kwargs).order_by(f'-{date_field}')
    
    count = recent_records.count()
    print(f"📊 Found {count} records in the last 3 days.")
    
    if count == 0:
        # If no records in last 3 days, show the most recent one
        latest = model_class.objects.order_by(f'-{date_field}').first()
        if latest:
            latest_date = getattr(latest, date_field)
            print(f"ℹ️ Most recent record is from: {latest_date.strftime('%Y-%m-%d %H:%M:%S') if latest_date else 'Unknown'}")
        else:
            print("ℹ️ Table is completely empty.")
    else:
        # Show all records from the last 3 days
        print(f"\nAll records from the last 3 days ({count} total):")
        for idx, record in enumerate(recent_records):
            rec_date = getattr(record, date_field)
            date_str = rec_date.strftime('%Y-%m-%d %H:%M:%S') if rec_date else 'Unknown'
            
            # Print specific fields based on station
            if model_class == HimanshWeatherData:
                print(f"  {idx+1}. {date_str} -> Temp: {record.air_temp}°C, RH: {record.rh}%, AP: {record.ap}")
            elif model_class == MaitriWeatherData:
                print(f"  {idx+1}. {date_str} -> Temp: {record.temp}°C, RH: {record.rh}%, WS: {record.ws}")
            elif model_class == BharatiWeatherData:
                print(f"  {idx+1}. {date_str} -> Temp: {record.tempr}°C, RH: {record.rh}%, WS: {record.ws}")
            elif model_class == HimadriWeatherData:
                print(f"  {idx+1}. {date_str} -> Temp: {record.temperature}°K, RH: {record.relative_humidity}%")

if __name__ == "__main__":
    print(f"🕒 Current System Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print_recent_records(MaitriWeatherData, "Maitri (Antarctica)", "date")
    print_recent_records(BharatiWeatherData, "Bharati (Antarctica)", "obstime")
    print_recent_records(HimadriWeatherData, "Himadri (Arctic)", "date")
    print_recent_records(HimanshWeatherData, "Himansh (Himalaya)", "date")
    
    print("\n" + "="*50)
    print("Done checking all stations.")
