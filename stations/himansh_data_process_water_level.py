import imaplib
import email
from email.header import decode_header
import os
import sys
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import text
import re
from datetime import datetime, timedelta
import argparse

# Import configuration
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    HIMANSH_WATER_RAW_DIR, HIMANSH_WATER_PROCESS_DIR,
    DB_CONNECTION_STRING,
    WATER_LEVEL_EMAIL_USER, WATER_LEVEL_EMAIL_PASS, WATER_LEVEL_EMAIL_IMAP,
    ensure_directories_exist, get_logger
)

logger = get_logger(__name__)
ensure_directories_exist()

# Email credentials
EMAIL_USER = WATER_LEVEL_EMAIL_USER
EMAIL_PASS = WATER_LEVEL_EMAIL_PASS

# Download directory for attachments
DOWNLOAD_FOLDER = str(HIMANSH_WATER_RAW_DIR)
PROCESS_FOLDER = str(HIMANSH_WATER_PROCESS_DIR)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESS_FOLDER, exist_ok=True)

# PostgreSQL connection
engine = create_engine(DB_CONNECTION_STRING)
table_name = 'himansh_water_level'

def sanitize_filename(original_filename):
    # Try to extract the timestamp at the end of the filename
    match = re.search(r'(\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2})\.csv$', original_filename)
    if match:
        new_filename = f"{match.group(1)}.csv"
    else:
        new_filename = original_filename.replace("(", "").replace(")", "").replace(" ", "_")
    
    return new_filename

def clean_subject(subject):
    try:
        subject, encoding = decode_header(subject)[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or 'utf-8')
    except:
        subject = str(subject)
    return subject

def process_water_level_csv(filepath):
    #print(f"Saving and Processing water level file: {filepath}")
    try:
        df = pd.read_csv(filepath, index_col=False)
        if len(df) <=1:
            print("\033[1;31mNo Data Found!\033[0m")
            return(None)

        # Clean column names
        print("\033[1;35mInserting Data to Database.\033[0m")
        df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
        df.rename(columns={"water_level_(m)": "water_level"}, inplace=True)

        if not {'date', 'time', 'water_level'}.issubset(df.columns):
            print("\033[1;31mRequired columns missing. Skipping file.\033[0m")
            return

        # Combine date and time
        df["date_time"] = pd.to_datetime(
            df["date"] + " " + df["time"],
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce"
        )
        df = df.dropna(subset=["date_time", "water_level"])
        df = df[["date_time", "water_level"]]
        if len(df) > 0:
            with engine.begin() as conn:
                query = text(f"""
                    INSERT INTO himansh_water_level ({', '.join(f'"{col}"' for col in df.columns)}) 
                    VALUES ({', '.join([f':{col}' for col in df.columns])}) 
                    ON CONFLICT ("date_time") 
                    DO UPDATE SET {', '.join([f'"{col}" = EXCLUDED."{col}"' for col in df.columns if col.lower() != "date_time"])};
                """)
                values = df.to_dict(orient="records")
                conn.execute(query, values)

            print(f"\033[1;32mUpserted {len(df)} records.\033[0m")
            # Save to monthly CSV
            df["year_str"] = df["date_time"].dt.strftime("%Y")
            df["month_str"] = df["date_time"].dt.strftime("%m")
            year_str = df["year_str"].iloc[0]
            month_str = df["month_str"].iloc[0]
            folder_path = os.path.join(PROCESS_FOLDER, year_str, month_str)
            os.makedirs(folder_path, exist_ok=True)
            monthly_file = os.path.join(folder_path,f"himansh_water_level_{year_str}_{month_str}.csv")

            # Load existing if present
            if os.path.exists(monthly_file):
                existing_df = pd.read_csv(monthly_file, parse_dates=["date_time"])
                # Drop completely empty columns (if any)
                existing_df = existing_df.dropna(axis=1, how='all')
            else:
                existing_df = pd.DataFrame(columns=["date_time", "water_level"])

            # Ensure correct columns
            if existing_df.empty:
                combined_df = df[["date_time", "water_level"]].copy()
            else:
                combined_df = pd.concat([existing_df, df[["date_time", "water_level"]]], ignore_index=True)

            combined_df = combined_df.drop_duplicates(subset=["date_time"]).sort_values("date_time")
            combined_df.to_csv(monthly_file, index=False)

    except Exception as e:
        print(f"\033[1;31mError processing file {filepath}: {e}\033[0m")

def fetch_and_process_emails(args):
    try:
        print("\033[1;35mConnecting to Gmail Account\033[0m")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        print("\033[1;32mConnected to Gmail\033[0m")
        if args.all:
            search_query = '(FROM "no-reply@aeronsystems.com" SUBJECT "Day(s) Report for Device Id")'
        else:
            start_date = (datetime.now() - timedelta(days=5)).strftime("%d-%b-%Y")
            search_query = f'(FROM "no-reply@aeronsystems.com" SUBJECT "Day(s) Report for Device Id" SINCE {start_date})'
        result, data = mail.search(None, search_query)  
        email_ids = data[0].split()

        print(f"\033[1;34mFound {len(email_ids)} emails.\033[0m")

        for email_id in reversed(email_ids):
            result, data = mail.fetch(email_id, "(RFC822)")
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)
            subject = msg["Subject"]
            email_date = email.utils.parsedate_to_datetime(msg["Date"])
            match = re.search(r'Device Id\s*=\s*([\d_]+)', subject)
            device_id = match.group(1) if match else None
            #print(f"Device ID: {device_id}") #Future Use
            if device_id == None:
                continue
            subject = clean_subject(msg["Subject"])
            print(f"\033[1;33mProcessing email:\033[0;36m{subject}\033[0m\t\033[1;33mDate: \033[0;36m{email_date.strftime('%Y-%m-%d %H:%M:%S')}\033[0m")

            for part in msg.walk():
                content_dispo = part.get("Content-Disposition")
                if content_dispo and "attachment" in content_dispo:
                    filename = part.get_filename()
                    if filename and filename.endswith(".csv") and "report" in filename.lower():
                        filepath = os.path.join(DOWNLOAD_FOLDER, sanitize_filename(filename))

                        with open(filepath, "wb") as f:
                            f.write(part.get_payload(decode=True))
                        process_water_level_csv(filepath)    
            print(f"\033[1;34m------\033[0m")
        mail.logout()
    except Exception as e:
        print(f"Failed to fetch or process emails: {e}")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--all", action="store_true", help="Run for all emails (not just last 5 days)")
    args = parser.parse_args()
    fetch_and_process_emails(args)
