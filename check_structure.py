import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.db import connection

print("=" * 100)
print("TABLE STRUCTURES")
print("=" * 100)

tables = ['maitri_maitri', 'imd_bharati', 'himadri_radiometer_surface']

for table in tables:
    print(f"\nTable: {table}")
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """)
        cols = cursor.fetchall()
        for col in cols:
            print(f"  - {col[0]:30} {col[1]:20} nullable={col[2]}")

print("\n" + "=" * 100)
print("LATEST DATES IN EACH TABLE")
print("=" * 100)

print("\nMaitri (date column):")
with connection.cursor() as cursor:
    cursor.execute("SELECT date FROM maitri_maitri ORDER BY date DESC LIMIT 3")
    for row in cursor.fetchall():
        print(f"  {row[0]}")

print("\nBharati (obstime column):")
with connection.cursor() as cursor:
    cursor.execute("SELECT obstime FROM imd_bharati ORDER BY obstime DESC LIMIT 3")
    for row in cursor.fetchall():
        print(f"  {row[0]}")

print("\nHimadri (date column):")
with connection.cursor() as cursor:
    cursor.execute("SELECT date FROM himadri_radiometer_surface ORDER BY date DESC LIMIT 3")
    for row in cursor.fetchall():
        print(f"  {row[0]}")
