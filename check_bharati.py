import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.db import connection

print("Checking imd_bharati columns:")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'imd_bharati' 
        ORDER BY ordinal_position
    """)
    cols = cursor.fetchall()
    for col in cols:
        print(f"  - {col[0]}")
    
    # Get latest record with correct column
    print("\nLatest 3 records from imd_bharati:")
    cursor.execute("SELECT obstime FROM imd_bharati ORDER BY obstime DESC LIMIT 3")
    rows = cursor.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"  {i}. {row[0]}")
