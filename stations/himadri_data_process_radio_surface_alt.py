import os
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import Table, MetaData
import argparse
from sqlalchemy import text
import re

host = "localhost"
database = "polardb"
user = "postgres"
password = "postgres"
port = "5432"
table_name = "himadri_himadri_radiometer_temp_altitude"
connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
engine = create_engine(connection_string)
data_dir_base = "/opt/djangoProject/raw_data/Himadri/Radiometer/"
data_target_base = "/opt/djangoProject/process_data/Himadri/Radiometer/TEMP_ALT/"
monthly_file_name = "Himadri_Temp_Alt"

def list_csv_files(folder_path):
    csv_files = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv'):
            csv_files.append(os.path.join(folder_path, file_name))    
    return csv_files

def get_file_name(directory, year, month, day):
    date_prefix = f"{year}-{month}-{day}"
    matching_files = [
        file for file in os.listdir(directory) 
        if file.startswith(date_prefix) and file.endswith("_lv2.csv")
    ]
    return matching_files

def get_file_path(year=None, month=None):
    if year and month:
        print(f"Searching files for {year}/{month}")
        location = os.path.join(data_dir_base, year, month.zfill(2))
        if not os.path.exists(location):
            print(location+" Not Found")
            return None
        filelist = list_csv_files(location)
        if len(filelist) > 0:
            return filelist
        else:
            print("No file found for the provided year and month.")
            return None
    else:
        print("Searching files for last 5 days")
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        day3 = today - timedelta(days=2)
        day4 = today - timedelta(days=3)
        day5 = today - timedelta(days=4)
        possible_dates = [today, yesterday, day3, day4, day5]
        filelist = []
        for date_obj in possible_dates:
            year = date_obj.strftime("%Y")
            month = date_obj.strftime("%m")
            day = date_obj.strftime("%d")
            location = os.path.join(data_dir_base, year, month.zfill(2))
            if not os.path.exists(location):
                print(location+" Not Found")
                continue
            files = get_file_name(location, year, month, day)
            if files:
                for file in files:
                    f = os.path.join(location,file)
                    if os.path.exists(f):
                        filelist.append(f)
            else:
                print(f"File not found for date: {year}/{month}/{day}")
        if len(filelist) > 0:
            return filelist
        else:
            print("No file found for last 5 days.")
            return None

def format_column_name(col):
    if col.strip().lower() == 'date' or col.strip().lower() == 'dataquality':
        return col.lower()
    col = col.replace('.', '_')
    return f'_{col.strip()}'

def process_csv_file(file_path):
    #print("Processing File: "+file_path)
    file = file_path.split('/')[-1]
    df = pd.read_csv(file_path, skiprows=6, low_memory=False)
    df = df[df['400'].astype(str) == "401"]
    df = df[df['LV2 Processor'] == 'ZenithKV']
    df = df.drop(columns=['Record', '400', 'LV2 Processor'])
    temp_columns = df.columns
    df = df.rename(columns={"Date/Time": "date"})
    df.columns = [format_column_name(col) for col in df.columns]
    df['date'] = pd.to_datetime(df['date'], format='%m/%d/%y %H:%M:%S', errors='coerce')
    df.iloc[:, 1:] = df.iloc[:, 1:].apply(pd.to_numeric, errors='coerce')
    if len(df)>0:
        with engine.begin() as conn:
            query = text(f"""
                INSERT INTO {table_name} ({', '.join(f'"{col}"' for col in df.columns)}) 
                VALUES ({', '.join([f':{col}' for col in df.columns])}) 
                ON CONFLICT ("date") 
                DO UPDATE SET {', '.join([f'"{col}" = EXCLUDED."{col}"' for col in df.columns if col.lower() != "date"])};
            """)
            values = df.to_dict(orient="records") 
            conn.execute(query, values)
            print("Data successfully inserted/updated for file: "+file)
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})", file)
        year, month, day = match.groups()
        target_file = os.path.join(data_target_base,year,month,f"{year}-{month}-{day}.csv")
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        df.columns = temp_columns
        df.to_csv(target_file, index=False)
    else:
        print("No Data in the file "+file_path)

def save_last_month_csv(year=None, month=None):
    if not year and not month:
        last_month = datetime.today() - relativedelta(months=1)
        year = last_month.strftime("%Y")
        month = last_month.strftime("%m")
    file_path = os.path.join(data_target_base,year,f"{monthly_file_name}_{year}_{month}.csv")
    if not os.path.exists(file_path):
        query = text(f"""
            SELECT * FROM {table_name} 
            WHERE EXTRACT(YEAR FROM date) = {year} AND EXTRACT(MONTH FROM date) = {month}
            ORDER BY date;
        """)
        df = pd.read_sql(query, engine)
        df.drop(columns=['sln'], inplace=True)
        df.to_csv(file_path,index=False)
        print(f"Data Saved for {year}-{month} in ",file_path)
    else:
        print(f"File already exist for {year}-{month}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process Temperature with Altitude data coming from Himadri Station.")
    parser.add_argument("-y","--year", type=str, help="Year for the file to process")
    parser.add_argument("-m","--month", type=str, help="Month for the file to process")
    
    args = parser.parse_args()

    filelist = get_file_path(args.year, args.month) if args.year and args.month else get_file_path()
    
    if filelist:
        for file in filelist:
            process_csv_file(file)
        save_last_month_csv(args.year, args.month) if args.year and args.month else save_last_month_csv()
    else:
        print("No valid file to process.")
