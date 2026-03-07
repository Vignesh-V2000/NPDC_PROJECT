import imaplib
import email
from datetime import datetime, timedelta
import os
import pandas as pd
from sqlalchemy import create_engine
import psycopg2
import numpy as np

def extract_day(row):
    month = row['Month']
    day = row['mail_received_date'].day
    string_value = str(row['date'])  

    if month < 10:
        if day < 10:
            return int(string_value[5:6])
        else:
            return int(string_value[5:7])
    else:
        if day < 10:
            return int(string_value[6:7])
        else:
            return int(string_value[6:8])
        
def extract_month(row):
    month = row['mail_received_date'].month
    string_value = str(row['date'])

    if month < 10:
        return int(string_value[4:5])
    else:
        return int(string_value[4:6])

def extract_time(row):
    month = row['Month']
    day = row['Day']
    string_value = str(row['date']) 
    if month < 10:
        if day < 10:
            return string_value[6:-1]+":00"
        else:
            return string_value[7:-1]+":00"
    else:
        if day < 10:
            return string_value[7:-1]+":00"
        else:
            return string_value[8:-1]+":00"
            
def create_datetime(row):
    year = str(row['Year'])
    month = str(row['Month'])
    day = str(row['Day'])
    time = row['Time']
    date_time_str = year+"-"+month+"-"+day+" "+time
    return pd.to_datetime(date_time_str)

db_connection_str = 'postgresql://postgres:postgres@localhost:5432/polardb'
engine = create_engine(db_connection_str)

conn = psycopg2.connect(
    host="localhost",
    port="5432",
    database="polardb",
    user="postgres",
    password="postgres"
)
c = conn.cursor()

username = "himanshncpor@gmail.com"
password = "xiozroyjxavbchiz"
imap_server = "imap.gmail.com"
subject_to_check = "Himansh"

df = pd.DataFrame(columns=['date', 'acc_preciptn', 'tot_acc_preciptn', 'ap', 'wd', 'wd_6m', 'batt_avg', 'air_temp', 'pannel_temp', 'rh', 's_up', 's_dn', 'l_up', 'l_dn', 'albedo', 'ws', 'ws_6m', 'tcdt', 'sur_temp','mail_received_date', 'mail_processed_date'])

current_datetime = datetime.now().strftime('%a, %d %b %Y %H:%M:%S')
end_date = datetime.now()
start_date = end_date - timedelta(days=20)
run_for = 0 # put zero if want to run for all mail, 1 if running only for last two days

mail = imaplib.IMAP4_SSL(imap_server)
mail.login(username, password)
mail.select("inbox")
#mail.select("spam")

search_query = ''
if run_for == 1:
    search_query = f'(SUBJECT "{subject_to_check}") SINCE {start_date.strftime("%d-%b-%Y")} BEFORE {end_date.strftime("%d-%b-%Y")}'
else:
    search_query = f'(SUBJECT "{subject_to_check}")'

print(search_query)
status, data = mail.search(None, search_query)
if status == 'OK':
    for num in data[0].split():
        email_id = int(num)
        c.execute("SELECT * FROM himansh_email_headers WHERE email_id="+str(email_id))
        row = c.fetchone()
        if not row:
            status, msg_data = mail.fetch(num, '(RFC822)')
            if status == 'OK':
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                subject = msg["Subject"]
                date_time = msg["Date"]
                c.execute("INSERT INTO himansh_email_headers (email_id, subject, date_time) VALUES ("+str(email_id)+", '"+subject+"', '"+date_time+"')")
                conn.commit()
                
                for part in msg.walk():
                    if part.get_content_maintype() == 'multipart':
                        continue
                    
                    filename = part.get_filename()
                    if not filename:
                        filename = "noname"
                    if filename == "noname":
                        with open(os.path.join("raw_data/Himansh",filename+"_"
                                               +datetime.strptime(date_time.split("+")[0].strip(),"%a, %d %b %Y %H:%M:%S").strftime('%Y_%m_%d_%H_%M')+".txt"), 'wb') as f:
                            f.write(part.get_payload(decode=True))
                        attachment_data = part.get_payload(decode=True).decode()
                        start_index = attachment_data.find('@')
                        if start_index != -1:
                            start_index = attachment_data.find('@', start_index + 1)
                            end_index = attachment_data.find('#')
                            if start_index != -1 and end_index != -1:
                                extracted_string = attachment_data[start_index + 1: end_index]
                                print("Extracted string:", extracted_string)
                                try:
                                    l = extracted_string.split(',')
                                    l[0] = str(l[0])
                                    #l[1:] = [float(x) for x in l[1:]]
                                    l[1:] = [float(x) if x not in [":INF", "INF", "-INF"] else np.nan for x in l[1:]]
                                    l.append(date_time)
                                    l.append(current_datetime)
                                    df.loc[len(df)] = l
                                except ValueError as ve:
                                    print("Error Processing email: "+str(email_id)+" dated: "+date_time)
                                    print(ve)
                                with open('process_data/Himansh/Himansh.csv', 'a', newline='', encoding='utf-8') as csvfile:
                                    csvfile.write(str(email_id)+","+extracted_string+",\""+date_time+"\","+"\""+current_datetime+"\"\n")
conn.close()
mail.close()
mail.logout()
if len(df):
    df = df.dropna(subset=['date'])
    df['mail_received_date'] = pd.to_datetime(df['mail_received_date'], format='%a, %d %b %Y %H:%M:%S %z')
    df['mail_received_date'] = df['mail_received_date'].dt.tz_convert('Asia/Kolkata')
    #df["date"] = df["date"].astype(int).astype(str)
    df["Year"] = df["date"].str[0:4]
    df["Month"] = df.apply(extract_month, axis=1)
    df["Day"] = df.apply(extract_day, axis=1)
    df["Time"] = df.apply(extract_time,axis=1)
    df['date'] = df.apply(create_datetime,axis=1)
    df.drop(["Year","Month","Day","Time"], axis=1, inplace=True)
    df.drop([ 'mail_received_date', 'mail_processed_date'], axis=1, inplace=True)
    df.to_sql(name='himansh_himansh', con=engine, if_exists='append', index=False)
    print("All Data Inserted to database")
else:
    print("Nothing to Insert")
