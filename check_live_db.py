import psycopg2
from colorama import init, Fore, Style
import os
from dotenv import load_dotenv

# Initialize colorama
init(autoreset=True)
load_dotenv('.env')

# DB Configuration
DB_HOST = os.environ.get('WEATHER_DB_HOST', '172.27.12.28')
DB_PORT = os.environ.get('WEATHER_DB_PORT', '5444')
DB_USER = os.environ.get('WEATHER_DB_USER', 'enterprisedb')
DB_PASS = os.environ.get('WEATHER_DB_PASSWORD', 'postgres')

print(f"\n{Fore.CYAN}{Style.BRIGHT}==================================================")
print(f"{Fore.CYAN}{Style.BRIGHT}  NPDC STATION DATA LAUNCH CHECKER")
print(f"{Fore.CYAN}{Style.BRIGHT}==================================================\n")
print(f"Connecting to host {DB_HOST}:{DB_PORT} as {DB_USER}...\n")


def check_table(conn, table_name, date_col, station_name):
    try:
        cur = conn.cursor()
        # Check if table exists
        cur.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}');")
        exists = cur.fetchone()[0]
        
        if not exists:
            print(f"{Fore.RED}[X] {station_name:<20} Table '{table_name}' does not exist.")
            return

        # Check total records
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]

        if count == 0:
            print(f"{Fore.YELLOW}[!] {station_name:<20} Table '{table_name}' exists but has 0 records.")
            return
            
        # Handle column naming differences
        original_col = date_col
        fallback_cols = [date_col, 'date', 'obstime', 'DateAndTime', 'date_time', 'Date_Time']
        actual_col = None
        
        for col in fallback_cols:
            cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table_name}' AND column_name='{col}';")
            if cur.fetchone():
                actual_col = col
                break
                
        if not actual_col:
             # Fallback to whatever was originally requested if we somehow can't find it in information_schema
             actual_col = original_col

        # Get latest record
        cur.execute(f"SELECT {actual_col} FROM {table_name} ORDER BY {actual_col} DESC LIMIT 1;")
        latest_date = cur.fetchone()[0]
        
        print(f"{Fore.GREEN}[Y] {station_name:<20} {count:>7} records.   Most recent: {Fore.WHITE}{latest_date}")
        
    except Exception as e:
        print(f"{Fore.RED}[X] Error checking table '{table_name}': {e}")
        conn.rollback()


# ==========================================
# 1. DATABASE: data_analysis
# ==========================================
print(f"{Fore.MAGENTA}{Style.BRIGHT}DATABASE: data_analysis{Style.RESET_ALL}")
print("-" * 50)
try:
    conn_analysis = psycopg2.connect(dbname='data_analysis', user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    
    # Check tables generally used in data_analysis
    check_table(conn_analysis, 'imd_bharati', 'obstime', 'Bharati (data_anal)')
    check_table(conn_analysis, 'last_24_hrs_data', 'date', 'Last 24Hrs (data_anal)')
    
    conn_analysis.close()
except Exception as e:
    print(f"{Fore.RED}Could not connect to data_analysis database: {e}")

print("\n")


# ==========================================
# 2. DATABASE: polardb
# ==========================================
print(f"{Fore.MAGENTA}{Style.BRIGHT}DATABASE: polardb{Style.RESET_ALL}")
print("-" * 50)
try:
    conn_polar = psycopg2.connect(dbname='polardb', user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
    
    # Check tables typically stored in polardb
    check_table(conn_polar, 'maitri_maitri', 'date', 'Maitri Data')
    check_table(conn_polar, 'himansh_himansh', 'date', 'Himansh Weather')
    # According to models, some tables may also just duplicate here or need distinct tracking
    check_table(conn_polar, 'imd_bharati', 'obstime', 'Bharati Data (polar)')
    check_table(conn_polar, 'last_24_hrs_data', 'date', 'Last 24Hrs (polar)')
    check_table(conn_polar, 'himansh_water_level', 'date', 'Himansh Water Lvl')
    check_table(conn_polar, 'himadri_radiometer_surface', 'date', 'Himadri Surface')
    
    conn_polar.close()
except Exception as e:
    print(f"{Fore.RED}Could not connect to polardb database: {e}")

print(f"\n{Fore.CYAN}{Style.BRIGHT}==================================================")
