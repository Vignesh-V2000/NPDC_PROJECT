"""
Check if station data exists in the other databases (polardb / data_analysis).
Run on the production machine: python check_db_tables.py
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.db import connection

# Get Django's DB host info
db_settings = connection.settings_dict
django_host = db_settings['HOST']
django_port = db_settings['PORT']
django_user = db_settings['USER']
django_password = db_settings['PASSWORD']

print(f"Django DB: {db_settings['NAME']} @ {django_host}:{django_port} (user: {django_user})")
print()

# Now try connecting to polardb and data_analysis on same host AND on localhost
import psycopg2

targets = [
    # Try same host as Django (172.27.11.202:5444)
    {'host': django_host, 'port': django_port, 'user': django_user, 'password': django_password, 'dbname': 'polardb'},
    {'host': django_host, 'port': django_port, 'user': django_user, 'password': django_password, 'dbname': 'data_analysis'},
    # Try localhost with postgres user (as in the scripts)
    {'host': 'localhost', 'port': '5432', 'user': 'postgres', 'password': 'postgres', 'dbname': 'polardb'},
    {'host': 'localhost', 'port': '5432', 'user': 'postgres', 'password': 'postgres', 'dbname': 'data_analysis'},
    # Try localhost with same port as Django
    {'host': 'localhost', 'port': django_port, 'user': django_user, 'password': django_password, 'dbname': 'polardb'},
    {'host': 'localhost', 'port': django_port, 'user': django_user, 'password': django_password, 'dbname': 'data_analysis'},
]

station_tables = ['maitri_maitri', 'imd_bharati', 'himansh_himansh', 'himadri_radiometer_surface', 'last_24_hrs_data']

for target in targets:
    label = f"{target['dbname']} @ {target['host']}:{target['port']} (user: {target['user']})"
    print(f"--- Trying: {label} ---")
    try:
        conn = psycopg2.connect(
            host=target['host'],
            port=target['port'],
            dbname=target['dbname'],
            user=target['user'],
            password=target['password'],
            connect_timeout=5
        )
        cur = conn.cursor()
        print(f"  CONNECTED OK!")
        
        for table in station_tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                if count > 0:
                    # Get columns
                    cur.execute(f"""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = '{table}' 
                        ORDER BY ordinal_position
                    """)
                    cols = cur.fetchall()
                    col_names = [c[0] for c in cols]
                    
                    # Try to get latest row
                    date_col = None
                    for dc in ['date', 'obstime', 'date_time']:
                        if dc in col_names:
                            date_col = dc
                            break
                    
                    if date_col:
                        cur.execute(f"SELECT * FROM {table} ORDER BY {date_col} DESC LIMIT 1")
                    else:
                        cur.execute(f"SELECT * FROM {table} LIMIT 1")
                    row = cur.fetchone()
                    
                    print(f"  TABLE {table}: {count} rows")
                    print(f"    Columns: {col_names}")
                    print(f"    Latest row:")
                    for i, col in enumerate(cols):
                        print(f"      {col[0]} ({col[1]}) = {row[i]}")
                else:
                    print(f"  TABLE {table}: EXISTS but EMPTY (0 rows)")
            except Exception as e:
                err_msg = str(e).split('\n')[0]
                print(f"  TABLE {table}: NOT FOUND - {err_msg}")
                conn.rollback()
        
        conn.close()
    except Exception as e:
        err_msg = str(e).split('\n')[0]
        print(f"  FAILED to connect: {err_msg}")
    print()

print("Done!")
