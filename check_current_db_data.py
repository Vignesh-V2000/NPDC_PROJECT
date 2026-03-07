import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.db import connection

print("=" * 100)
print("CHECKING CURRENT DATABASE VALUES")
print("=" * 100)

tables = {
    'maitri_maitri': 'date',
    'imd_bharati': 'obstime', 
    'himadri_radiometer_surface': 'date',
}

for table, date_col in tables.items():
    print(f"\n{table}:")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT {date_col} FROM {table} ORDER BY {date_col} DESC LIMIT 5")
        rows = cursor.fetchall()
        for i, row in enumerate(rows, 1):
            print(f"  {i}. {row[0]}")
