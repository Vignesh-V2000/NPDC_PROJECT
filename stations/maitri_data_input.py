import os
import pandas as pd
from sqlalchemy import text, create_engine

directory_path = 'raw_data/Maitri/'
table_name = 'maitri_input_file'
db_connection_str = 'postgresql://postgres:postgres@localhost:5432/polardb'

engine = create_engine(db_connection_str)

def extract_file_pairs(directory):
    files = os.listdir(directory)
    files.sort()
    pairs = []

    for file in files:
        if file.endswith("(1).xlsx"):
            base_name = file[:-8]  # Remove the (1) from the filename
            pair_file = base_name + "(2).xlsx"
            if pair_file in files:
                pairs.append((file, pair_file))
    return pairs

def create_dataframe(directory):
    pairs = extract_file_pairs(directory)
    data = []

    for pair in pairs:
        file1, file2 = pair
        base_name = file1[:-8]  # Remove the (1) from the filename
        data.append((base_name, file1, file2, False))

    df = pd.DataFrame(data, columns=['base_name', 'file1', 'file2', 'processed'])
    return df

def save_to_database(df, table_name, connection_str):
    engine = create_engine(connection_str)
    existing_rows = pd.read_sql_table(table_name, engine)
    existing_filenames = set(existing_rows['base_name'])
    new_rows = df[~df['base_name'].isin(existing_filenames)]
    new_rows.to_sql(table_name, engine, if_exists='append', index=False)

def create_datetime(row):
    date = row['Date']
    time = row['Time']
    date_time_str = str(date)+' '+str(time)
    return pd.to_datetime(date_time_str)
    
def first_file(filename):
    print(filename)
    input_file1 = pd.read_excel(filename, sheet_name='1Min')
    input_file1['Date'] = input_file1.apply(create_datetime,axis=1)
    input_file1.drop(['Time','HourlyRainfall (mm)', 'DailyRainfall (mm)'], axis=1, inplace=True)
    input_file1 = input_file1.rename(columns={
        'Date':'date',
        'Temperature1MinAvg (DEG C)': 'temp',
        'DewPoint1MinAvg (DEG C)':'dew_point',
        'Humidity1MinAvg (%Rh)':'rh',
        'Pressure1MinAvg (mBar)':'ap',
        'QNH1MinAvg (mBar)':'ap_1',
        'QFE1MinAvg (mBar)':'ap_2'
    })
    input_file1['temp'] = pd.to_numeric(input_file1['temp'], errors='coerce')
    input_file1['dew_point'] = pd.to_numeric(input_file1['dew_point'], errors='coerce')
    input_file1['rh'] = pd.to_numeric(input_file1['rh'], errors='coerce')
    input_file1['ap'] = pd.to_numeric(input_file1['ap'], errors='coerce')
    input_file1['ap_1'] = pd.to_numeric(input_file1['ap_1'], errors='coerce')
    input_file1['ap_2'] = pd.to_numeric(input_file1['ap_2'], errors='coerce')
    return input_file1

def second_file(filename):
    print(filename)
    try:
        input_file2 = pd.read_excel(filename, sheet_name='Sheet1')
    except Exception as e:
        return pd.DataFrame(columns=['date','ws','wd'])
    input_file2 = input_file2.drop(0)
    input_file2['Date'] = input_file2.apply(create_datetime,axis=1)
    input_file2 = input_file2.rename(columns={
        'Date':'date',
        'Wind Direction (DEG)': 'wd',
        'Wind Speed (knots)':'ws'
    })
    input_file2.drop(['Time'], axis=1, inplace=True)
    input_file2 = input_file2[['date','ws','wd']]
    input_file2['ws'] = pd.to_numeric(input_file2['ws'], errors='coerce')
    input_file2['wd'] = pd.to_numeric(input_file2['wd'], errors='coerce')
    return input_file2

# input file list to db
input_file_df = create_dataframe(directory_path)
save_to_database(input_file_df, table_name, db_connection_str)

query = "SELECT * FROM "+table_name+" WHERE processed = false"
file_list = pd.read_sql_query(query, con=engine)
for index, row in file_list.iterrows():
    file1 = first_file(directory_path+row['file1'])
    file2 = second_file(directory_path+row['file2'])
    merged_df = pd.merge(file1, file2,how='left', on='date')
    merged_df.to_sql('maitri_maitri', engine, if_exists='append', index=False)
    if not os.path.isfile('filename.csv'):
        merged_df.to_csv('process_data/Maitri/Maitri.csv', header='column_names')
    else:
        merged_df.to_csv('process_data/Maitri/Maitri.csv', mode='a', header=False)
    update_query = text("UPDATE "+table_name+" SET processed = true WHERE sln = "+str(row['sln']))
    with engine.connect() as connection:
        connection.execute(update_query)
        connection.commit()
