import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'himansh_himansh'")
    if cursor.fetchone()[0]:
        cursor.execute("SELECT count(*) FROM himansh_himansh")
        print("himansh_himansh count:", cursor.fetchone()[0])
    else:
        print("himansh_himansh table does not exist")
    
    cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'himansh_water_level'")
    if cursor.fetchone()[0]:
        cursor.execute("SELECT count(*) FROM himansh_water_level")
        print("himansh_water_level count:", cursor.fetchone()[0])
    else:
        print("himansh_water_level table does not exist")
