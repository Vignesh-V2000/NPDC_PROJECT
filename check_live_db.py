import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.db import connection
from datetime import datetime

print("=" * 100)
print("LIVE DATABASE DATA CHECK")
print("=" * 100)

tables = {
    'maitri_maitri': ('date', 'temp'),
    'imd_bharati': ('obstime', 'tempr'), 
    'himadri_radiometer_surface': ('date', 'temperature'),
}

for table, (date_col, temp_col) in tables.items():
    print(f"\n{table}:")
    with connection.cursor() as cursor:
        # Get latest 10 records
        cursor.execute(f"""
            SELECT {date_col}, {temp_col} 
            FROM {table} 
            ORDER BY {date_col} DESC 
            LIMIT 10
        """)
        rows = cursor.fetchall()
        for i, (dt, temp) in enumerate(rows, 1):
            print(f"  {i}. {dt} | Temp: {temp}")

print("\n" + "=" * 100)
print("EXPECTED:")
print("=" * 100)
print("Should show March 6 2026 data (latest from yesterday)")
print("Currently shows March 5 2026 data (day before)")
print("\nIf you see March 5 as latest, the data hasn't been updated yet")
print("on the live database for March 6.")
