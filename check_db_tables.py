"""
Run this on the production machine to see all database tables and their columns.
Usage: python check_db_tables.py

It will show:
1. Which database Django is connected to
2. All tables in the database
3. For station-related tables: column names, row count, and a sample row
"""
import os, sys, django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.db import connection

print("=" * 60)
print("DATABASE CONNECTION INFO")
print("=" * 60)
db_settings = connection.settings_dict
print(f"  Engine : {db_settings['ENGINE']}")
print(f"  Name   : {db_settings['NAME']}")
print(f"  Host   : {db_settings['HOST']}")
print(f"  Port   : {db_settings['PORT']}")
print(f"  User   : {db_settings['USER']}")
print()

print("=" * 60)
print("ALL TABLES IN DATABASE")
print("=" * 60)
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
    """)
    tables = [row[0] for row in cursor.fetchall()]
    for t in tables:
        print(f"  {t}")

print()
print("=" * 60)
print("STATION-RELATED TABLES (detail)")
print("=" * 60)

# Look for any table related to stations
station_keywords = ['maitri', 'bharati', 'himansh', 'himadri', 'weather', 'station', 'imd', 'radiometer', 'last_24']

for table in tables:
    if any(kw in table.lower() for kw in station_keywords):
        print(f"\n--- {table} ---")
        try:
            # Get columns
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{table}' 
                    ORDER BY ordinal_position
                """)
                columns = cursor.fetchall()
                print(f"  Columns:")
                for col_name, col_type in columns:
                    print(f"    {col_name} ({col_type})")
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  Row count: {count}")
                
                # Get latest row (try common date columns)
                if count > 0:
                    col_names = [c[0] for c in columns]
                    date_col = None
                    for possible in ['date', 'obstime', 'date_time', 'created_at', 'timestamp']:
                        if possible in col_names:
                            date_col = possible
                            break
                    
                    if date_col:
                        cursor.execute(f"SELECT * FROM {table} ORDER BY {date_col} DESC LIMIT 1")
                        row = cursor.fetchone()
                        print(f"  Latest row (by {date_col}):")
                        for i, col in enumerate(columns):
                            print(f"    {col[0]} = {row[i]}")
                    else:
                        cursor.execute(f"SELECT * FROM {table} LIMIT 1")
                        row = cursor.fetchone()
                        print(f"  Sample row:")
                        for i, col in enumerate(columns):
                            print(f"    {col[0]} = {row[i]}")
        except Exception as e:
            print(f"  ERROR: {e}")

print()
print("Done!")
