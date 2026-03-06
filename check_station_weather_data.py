"""
Diagnostic script to check why station weather data is showing as zero on home page.

This script:
1. Checks if station tables exist in the database
2. Verifies if they contain data
3. Shows the latest temperature values
4. Identifies any data issues or connection problems

Run with: python manage.py shell < check_station_weather_data.py
"""

import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

print("=" * 80)
print("STATION WEATHER DATA DIAGNOSTIC")
print("=" * 80)

# Station configurations (same as in views.py)
stations = [
    {
        'key': 'maitri',
        'name': 'Maitri',
        'location': 'Antarctica - Maitri',
        'table': 'maitri_maitri',
        'temp_col': 'temp',
        'date_col': 'date',
        'is_kelvin': False,
    },
    {
        'key': 'bharati',
        'name': 'Bharati',
        'location': 'Antarctica - Bharati',
        'table': 'imd_bharati',
        'temp_col': 'tempr',
        'date_col': 'obstime',
        'is_kelvin': False,
    },
    {
        'key': 'himansh',
        'name': 'Himansh',
        'location': 'Himalaya - Himansh',
        'table': 'himansh_himansh',
        'temp_col': 'air_temp',
        'date_col': 'date',
        'is_kelvin': False,
    },
    {
        'key': 'himadri',
        'name': 'Himadri',
        'location': 'Arctic - Himadri',
        'table': 'himadri_radiometer_surface',
        'temp_col': 'temperature',
        'date_col': 'date',
        'is_kelvin': True,
    },
]

# Check each station
for station in stations:
    print(f"\n{'-' * 80}")
    print(f"STATION: {station['name']} ({station['location']})")
    print(f"Table: {station['table']}")
    print(f"{'-' * 80}")
    
    try:
        with connection.cursor() as cursor:
            # 1. Check if table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, [station['table']])
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                print(f"❌ TABLE DOES NOT EXIST: {station['table']}")
                continue
            
            print(f"✓ Table exists")
            
            # 2. Get table info
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position
            """, [station['table']])
            
            columns = cursor.fetchall()
            print(f"\nColumns ({len(columns)}):")
            for col_name, col_type in columns:
                print(f"  • {col_name}: {col_type}")
            
            # 3. Count total rows
            cursor.execute(f"SELECT COUNT(*) FROM {station['table']}")
            total_rows = cursor.fetchone()[0]
            print(f"\nTotal rows: {total_rows}")
            
            if total_rows == 0:
                print("⚠️  TABLE IS EMPTY - No weather data")
                continue
            
            # 4. Check how many have temperature data
            cursor.execute(f"""
                SELECT COUNT(*) FROM {station['table']} 
                WHERE {station['temp_col']} IS NOT NULL
            """)
            rows_with_temp = cursor.fetchone()[0]
            print(f"Rows with temperature data: {rows_with_temp}")
            
            # 5. Get temperature stats
            cursor.execute(f"""
                SELECT 
                    MIN({station['temp_col']}) as min_temp,
                    MAX({station['temp_col']}) as max_temp,
                    AVG({station['temp_col']}) as avg_temp
                FROM {station['table']} 
                WHERE {station['temp_col']} IS NOT NULL
            """)
            
            min_t, max_t, avg_t = cursor.fetchone()
            print(f"\nTemperature Statistics:")
            print(f"  Min: {min_t}")
            print(f"  Max: {max_t}")
            print(f"  Avg: {avg_t}")
            
            # 6. Get latest temperature record
            print(f"\nLatest Records (Last 5):")
            cursor.execute(f"""
                SELECT {station['date_col']}, {station['temp_col']}
                FROM {station['table']}
                WHERE {station['temp_col']} IS NOT NULL
                ORDER BY {station['date_col']} DESC
                LIMIT 5
            """)
            
            latest = cursor.fetchall()
            if latest:
                for i, (date_val, temp_val) in enumerate(latest, 1):
                    # Convert Kelvin to Celsius if needed
                    if station['is_kelvin'] and temp_val:
                        temp_display = round(float(temp_val) - 273.15, 1)
                        unit = "°C (from Kelvin)"
                    else:
                        temp_display = temp_val
                        unit = "°C"
                    
                    print(f"  {i}. {date_val} → {temp_display} {unit}")
            else:
                print("  ❌ No records found with temperature data")
            
            # 7. Check for sentinel values or issues
            cursor.execute(f"""
                SELECT {station['temp_col']}, COUNT(*) as count
                FROM {station['table']}
                GROUP BY {station['temp_col']}
                ORDER BY count DESC
                LIMIT 10
            """)
            
            temp_dist = cursor.fetchall()
            print(f"\nTemperature Value Distribution (Top 10):")
            for temp_val, count in temp_dist:
                if temp_val is None:
                    print(f"  NULL: {count} records")
                elif temp_val <= -999:
                    print(f"  {temp_val} (SENTINEL VALUE - Missing data): {count} records")
                else:
                    print(f"  {temp_val}: {count} records")
                    
    except Exception as e:
        print(f"❌ ERROR: {e}")

print("\n" + "=" * 80)
print("DIAGNOSIS")
print("=" * 80)

print("""
If all temperatures are showing as 0:

1. TABLE DOESN'T EXIST
   → Station data tables need to be created or populated by data processing scripts
   → Run the official NPDC station data processing scripts:
     - maitri_data_input.py
     - last24HrsDataProcessing.py (Bharati)
     - email_process_himansh.py
     - himadri_data_process_radio_surface.py

2. TABLE IS EMPTY
   → The station tables exist but have no data
   → Check if the data processing scripts have run recently
   → Check cron jobs for error logs

3. ALL VALUES ARE SENTINEL (-999)
   → Data exists but is marked as invalid/missing
   → This is expected if stations aren't currently collecting data

4. WRONG DATABASE CONNECTION
   → The Django app is connecting to the wrong database
   → Check settings.py for DATABASES configuration
   → Verify the connection to the station data database

5. COLUMN NAMES MISMATCH
   → The column names in station_models.py don't match actual table columns
   → Update column definitions in users/station_models.py
""")

print("=" * 80)
