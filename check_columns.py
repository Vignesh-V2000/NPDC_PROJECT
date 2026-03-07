import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.db import connection

tables = {
    'maitri_maitri': 'Maitri',
    'imd_bharati': 'Bharati',
    'himadri_radiometer_surface': 'Himadri',
    'himansh_water_level': 'Himansh'
}

print("=" * 100)
print("DATABASE ACTUAL COLUMNS")
print("=" * 100)

for table, name in tables.items():
    print(f"\n{name} ({table}):")
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT column_name, data_type
            FROM information_schema.columns 
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """)
        cols = cursor.fetchall()
        for col in cols:
            print(f"  - {col[0]:30} {col[1]}")
