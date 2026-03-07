import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.db import connection

print("=" * 100)
print("RAW DATABASE DATETIME CHECK")
print("=" * 100)

tables = [
    ('maitri_maitri', 'date'),
    ('imd_bharati', 'date'),
    ('himadri_radiometer_surface', 'date'),
]

for table, date_col in tables:
    print(f"\n{'-'*100}")
    print(f"Table: {table}")
    print(f"{'-'*100}")
    
    try:
        with connection.cursor() as cursor:
            # Check if table exists first
            cursor.execute(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}')")
            exists = cursor.fetchone()[0]
            
            if not exists:
                print(f"  ❌ Table does not exist")
                continue
            
            # Get latest record
            cursor.execute(f"SELECT {date_col} FROM {table} ORDER BY {date_col} DESC LIMIT 5")
            rows = cursor.fetchall()
            
            if rows:
                print(f"  Latest 5 records:")
                for i, row in enumerate(rows, 1):
                    dt = row[0]
                    print(f"    {i}. {dt} (Type: {type(dt).__name__})")
            else:
                print(f"  ❌ No data in table")
    
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")

print(f"\n{'='*100}")
print("Settings Check:")
print(f"{'='*100}")
from django.conf import settings
print(f"USE_TZ: {settings.USE_TZ}")
print(f"TIME_ZONE: {settings.TIME_ZONE}")
