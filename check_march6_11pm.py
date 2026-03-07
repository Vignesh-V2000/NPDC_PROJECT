import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.db import connection
from datetime import datetime, date

print("=" * 100)
print("CHECKING FOR MARCH 6 DATA AT 11:00 PM")
print("=" * 100)

# Check for March 6 data at 11:00 PM (23:00)
target_date = date(2026, 3, 6)
target_start = datetime(2026, 3, 6, 23, 0, 0)
target_end = datetime(2026, 3, 6, 23, 59, 59)

tables = {
    'maitri_maitri': 'date',
    'imd_bharati': 'obstime',
    'himadri_radiometer_surface': 'date',
    'himansh_water_level': 'date',
}

for table, date_col in tables.items():
    print(f"\n{'-'*100}")
    print(f"TABLE: {table}")
    print(f"{'-'*100}")
    
    # Check for 11:00 PM data (23:00-23:59)
    print(f"\n1. DATA AT 11:00 PM (23:00-23:59) on March 6:")
    with connection.cursor() as cursor:
        sql = f"""
            SELECT {date_col} 
            FROM {table}
            WHERE DATE({date_col}) = '2026-03-06'
            AND EXTRACT(HOUR FROM {date_col}) = 23
            ORDER BY {date_col} DESC
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        if rows:
            for i, (dt,) in enumerate(rows, 1):
                print(f"   ✓ {i}. {dt}")
        else:
            print(f"   ✗ No data found at 11:00 PM")
    
    # Check all March 6 data
    print(f"\n2. ALL MARCH 6 DATA (all hours):")
    with connection.cursor() as cursor:
        sql = f"""
            SELECT {date_col}, COUNT(*) as count
            FROM {table}
            WHERE DATE({date_col}) = '2026-03-06'
            GROUP BY DATE({date_col})
        """
        cursor.execute(sql)
        row = cursor.fetchone()
        if row:
            print(f"   Total March 6 records: {row[1]}")
        else:
            print(f"   No March 6 data found")
    
    # Show latest 10 records
    print(f"\n3. LATEST 10 RECORDS:")
    with connection.cursor() as cursor:
        sql = f"""
            SELECT {date_col}
            FROM {table}
            ORDER BY {date_col} DESC
            LIMIT 10
        """
        cursor.execute(sql)
        rows = cursor.fetchall()
        for i, (dt,) in enumerate(rows, 1):
            if '2026-03-06' in str(dt):
                print(f"   {i}. {dt}  ← MARCH 6")
            elif '2026-03-05' in str(dt):
                print(f"   {i}. {dt}  ← MARCH 5")
            else:
                print(f"   {i}. {dt}")

print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)
print("""
If March 6 at 11:00 PM data is PRESENT:
  - The website will show March 6 consistently

If March 6 at 11:00 PM data is ABSENT:
  - The fallback logic will show the latest available data
  - Might show March 5 or earlier data
""")
