import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.db import connection
from datetime import datetime, date

print("=" * 100)
print("CHECKING FOR MARCH 6 DATA AT 11:00 PM")
print("=" * 100)

tables = {
    'maitri_maitri': 'date',
    'imd_bharati': 'obstime',
    'himadri_radiometer_surface': 'date',
    'himansh_water_level': 'date',
}

for table, date_col in tables.items():
    print(f"\n{'-'*100}")
    print(f"TABLE: {table} (column: {date_col})")
    print(f"{'-'*100}")
    
    # Check for 11:00 PM data (23:00-23:59)
    print(f"\n✓ DATA AT 11:00 PM (23:00-23:59) on March 6:")
    with connection.cursor() as cursor:
        sql = f"""
            SELECT {date_col} 
            FROM {table}
            WHERE DATE({date_col}) = '2026-03-06'
            AND EXTRACT(HOUR FROM {date_col}) = 23
            ORDER BY {date_col} DESC
        """
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            if rows:
                for i, (dt,) in enumerate(rows, 1):
                    print(f"    Found: {dt}")
            else:
                print(f"    ✗ NOT FOUND - No data at 11:00 PM on March 6")
        except Exception as e:
            print(f"    Error: {e}")
    
    # Show all March 6 data
    print(f"\n✓ ALL MARCH 6 DATA:")
    with connection.cursor() as cursor:
        sql = f"""
            SELECT {date_col}
            FROM {table}
            WHERE DATE({date_col}) = '2026-03-06'
            ORDER BY {date_col} DESC
        """
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            if rows:
                print(f"    Total records: {len(rows)}")
                for i, (dt,) in enumerate(rows[:10], 1):
                    hour = dt.hour
                    print(f"      {i}. {dt}  (Hour: {hour:02d})")
            else:
                print(f"    No March 6 data found")
        except Exception as e:
            print(f"    Error: {e}")
    
    # Show latest records
    print(f"\n✓ LATEST 5 RECORDS:")
    with connection.cursor() as cursor:
        sql = f"""
            SELECT {date_col}
            FROM {table}
            ORDER BY {date_col} DESC
            LIMIT 5
        """
        try:
            cursor.execute(sql)
            rows = cursor.fetchall()
            for i, (dt,) in enumerate(rows, 1):
                if '2026-03-06' in str(dt):
                    print(f"    {i}. {dt}  ← MARCH 6")
                elif '2026-03-05' in str(dt):
                    print(f"    {i}. {dt}  ← MARCH 5")
                else:
                    print(f"    {i}. {dt}")
        except Exception as e:
            print(f"    Error: {e}")

print("\n" + "=" * 100)
print("CONCLUSION")
print("=" * 100)
print("""
Check the results above:

• If "March 6 at 11:00 PM" data is FOUND:
  ✓ Website will display March 6 consistently
  ✓ No flickering between dates

• If "March 6 at 11:00 PM" data is NOT FOUND:
  • Will use fallback (latest available data)
  • May show March 5 if that's the latest data
  • Fallback ensures something is always displayed
""")
