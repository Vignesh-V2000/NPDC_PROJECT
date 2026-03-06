# Station Data Processing Scripts - Quick Start Guide

## 1. Setup (One-Time)

### Step 1: Set Environment Variables
Create a `.env` file in the project root OR set system environment variables:

**Windows (Command Prompt):**
```cmd
set NPDC_DB_HOST=localhost
set NPDC_DB_PORT=5432
set NPDC_DB_NAME=npdc_db
set NPDC_DB_USER=postgres
set NPDC_DB_PASSWORD=your_password
set HIMANSH_EMAIL_USER=himanshncpor@gmail.com
set HIMANSH_EMAIL_PASS=your_app_password
set WATER_LEVEL_EMAIL_USER=pnsharmancpor@gmail.com
set WATER_LEVEL_EMAIL_PASS=your_app_password
```

**Windows PowerShell:**
```powershell
$env:NPDC_DB_HOST="localhost"
$env:NPDC_DB_PORT="5432"
$env:NPDC_DB_NAME="npdc_db"
$env:NPDC_DB_USER="postgres"
$env:NPDC_DB_PASSWORD="your_password"
$env:HIMANSH_EMAIL_USER="himanshncpor@gmail.com"
$env:HIMANSH_EMAIL_PASS="your_app_password"
$env:WATER_LEVEL_EMAIL_USER="pnsharmancpor@gmail.com"
$env:WATER_LEVEL_EMAIL_PASS="your_app_password"
```

**Linux/Mac (Bash):**
```bash
export NPDC_DB_HOST=localhost
export NPDC_DB_PORT=5432
export NPDC_DB_NAME=npdc_db
export NPDC_DB_USER=postgres
export NPDC_DB_PASSWORD=your_password
export HIMANSH_EMAIL_USER=himanshncpor@gmail.com
export HIMANSH_EMAIL_PASS=your_app_password
export WATER_LEVEL_EMAIL_USER=pnsharmancpor@gmail.com
export WATER_LEVEL_EMAIL_PASS=your_app_password
```

### Step 2: Verify Configuration
```bash
cd e:\NPDC\NPDC_PROJECT\stations
python -c "from config import *; ensure_directories_exist(); print('✓ Configuration OK')"
```

### Step 3: Prepare Input Data
Create the required directories and place your data files:
- **Maitri data**: `raw_data/Maitri/*.xlsx` (paired Excel files with (1) and (2) suffix)
- **Bharati data**: `raw_data/DCWIS_NEW/` (RW09*.xlsx and Wind*.xlsx files)
- **Himansh stations**: Configured via email (Himansh)
- **Water level**: Configured via email (Water level)
- **Himadri data**: `raw_data/Himadri/Radiometer/YYYY/MM/*.csv` files

---

## 2. Running Scripts

### Option 1: Run Individual Script
```bash
# Maitri Station
python stations/maitri_data_input.py

# Bharati Station (with auto-run for last 5 days)
python stations/last24HrsDataProcessing.py -r

# Himadri Station
python stations/himadri_data_process_radio_surface.py

# Himadri (alternative radiometer)
python stations/himadri_data_process_radio_surface_alt.py

# Himansh (via email)
python stations/email_process_himansh.py

# Himansh water level (via email)
python stations/himansh_data_process_water_level.py
```

### Option 2: Run All Scripts at Once
Create `run_all_stations.py`:

```python
import subprocess
import sys
from pathlib import Path

scripts = [
    'maitri_data_input.py',
    'last24HrsDataProcessing.py',
    'himadri_data_process_radio_surface.py',
    'himadri_data_process_radio_surface_alt.py',
    'email_process_himansh.py',
    'himansh_data_process_water_level.py'
]

stations_dir = Path(__file__).parent / 'stations'

for script in scripts:
    script_path = stations_dir / script
    print(f"\n{'='*60}")
    print(f"Running: {script}")
    print('='*60)
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(stations_dir.parent),
            check=True
        )
        print(f"✅ {script} completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ {script} failed with error code {e.returncode}")
    except Exception as e:
        print(f"❌ {script} failed: {e}")

print(f"\n{'='*60}")
print("All scripts completed!")
print('='*60)
```

Then run:
```bash
python run_all_stations.py
```

### Option 3: Schedule with Cron (Linux/Mac)
```bash
# Edit crontab
crontab -e

# Add these lines (every 12 hours):
0 */12 * * * cd /path/to/project && python stations/maitri_data_input.py >> logs/cron.log 2>&1
0 */12 * * * cd /path/to/project && python stations/last24HrsDataProcessing.py -r >> logs/cron.log 2>&1
30 */12 * * * cd /path/to/project && python stations/email_process_himansh.py >> logs/cron.log 2>&1
30 */12 * * * cd /path/to/project && python stations/himansh_data_process_water_level.py >> logs/cron.log 2>&1
45 */12 * * * cd /path/to/project && python stations/himadri_data_process_radio_surface.py >> logs/cron.log 2>&1
45 */12 * * * cd /path/to/project && python stations/himadri_data_process_radio_surface_alt.py >> logs/cron.log 2>&1
```

### Option 4: Schedule with Windows Task Scheduler
**Create a batch file** `run_stations.bat`:
```batch
@echo off
cd e:\NPDC\NPDC_PROJECT
python stations\maitri_data_input.py
python stations\last24HrsDataProcessing.py -r
python stations\email_process_himansh.py
python stations\himansh_data_process_water_level.py
python stations\himadri_data_process_radio_surface.py
python stations\himadri_data_process_radio_surface_alt.py
```

Then schedule with Task Scheduler to run every 12 hours.

---

## 3. Monitoring

### Check Logs
```bash
# View logs in real-time
tail -f logs/*.log

# Check last 100 lines of Maitri log
tail -100 logs/maitri_data_input.log

# Check for errors
grep ERROR logs/*.log
```

### Verify Data in Database
```bash
# Using Django shell
python manage.py shell

# Then:
from data_submission.models import DatasetSubmission
from users.models import *

# Check Maitri data
MaitriTemperature.objects.count()
MaitriTemperature.objects.latest('date').date

# Check Bharati data
BharatiTemperature.objects.count()

# Check Himansh data
HimanshTemperature.objects.count()

# Check Himadri data
HimadriTemperature.objects.count()
```

### Check Weather Display
1. Go to home page: http://localhost:8000/
2. Scroll to "Latest Weather at Polar Stations" section
3. You should see temperature cards for 4 stations
4. If not showing, check:
   - `logs/` directory for errors
   - Database has data: Run queries above
   - Django debug mode shows exceptions

---

## 4. Troubleshooting

### Issue: "No module named 'config'"
**Fix**: Ensure you're running from project root or stations directory has proper Python path:
```bash
cd e:\NPDC\NPDC_PROJECT
python -m stations.maitri_data_input
```

### Issue: "Connection refused" or "could not connect to database"
**Fix**: Check database connection:
```bash
python manage.py shell
from django.db import connection
connection.ensure_connection()
print("✓ Database OK")
```

### Issue: "Email not found" or "Gmail authentication failed"
**Fix**: Verify Gmail app password:
1. Go to https://myaccount.google.com/apppasswords
2. Create new app password (don't use regular password!)
3. Set environment variable correctly

### Issue: "File not found" or missing input files
**Fix**: Check raw data directories:
```bash
ls raw_data/Maitri/       # Should have .xlsx files
ls raw_data/DCWIS_NEW/    # Should have RW09*.xlsx and Wind*.xlsx
ls raw_data/Himadri/Radiometer/  # Should have YYYY/MM/*.csv
```

### Issue: Data not appearing in database
**Fix**: Check script logs:
```bash
grep -i error logs/maitri_data_input.log
grep -i error logs/last24HrsDataProcessing.log
```

---

## 5. Configuration Options

### Default Configuration (config.py)
All of these can be overridden with environment variables:

```python
DB_HOST = 'localhost'              # NPDC_DB_HOST
DB_PORT = '5432'                   # NPDC_DB_PORT
DB_NAME = 'npdc_db'                # NPDC_DB_NAME
DB_USER = 'postgres'               # NPDC_DB_USER
DB_PASSWORD = 'postgres'           # NPDC_DB_PASSWORD

HIMANSH_EMAIL_USER = 'himanshncpor@gmail.com'    # HIMANSH_EMAIL_USER
HIMANSH_EMAIL_PASS = 'default_app_password'      # HIMANSH_EMAIL_PASS

WATER_LEVEL_EMAIL_USER = 'pnsharmancpor@gmail.com'   # WATER_LEVEL_EMAIL_USER
WATER_LEVEL_EMAIL_PASS = 'default_app_password'      # WATER_LEVEL_EMAIL_PASS
```

### Edit Default Configuration
Edit `stations/config.py` line 12-32 to change default values.

---

## 6. Validation Checklist

- [ ] Environment variables set correctly
- [ ] Python dependencies installed: `pandas`, `sqlalchemy`, `psycopg2`, `openpyxl`
- [ ] Database connection working (test with Django shell)
- [ ] All directories exist in `raw_data/` and `process_data/`
- [ ] Input files placed in correct directories
- [ ] Gmail app passwords created (if using email sources)
- [ ] Logs directory accessible
- [ ] Scripts run without errors (check logs/)
- [ ] Data appears in database
- [ ] Weather cards appear on home page

---

## 7. Next: Deploy to Production

### For Linux Server:
```bash
# 1. Copy scripts to server
scp -r stations/ user@server:/path/to/project/

# 2. Set environment variables in systemd service or .env file
# 3. Test one script manually
python stations/maitri_data_input.py

# 4. Set up cron jobs (see Option 3 above)
crontab -e

# 5. Monitor logs
tail -f logs/*.log
```

### For Windows Server:
```powershell
# 1. Copy scripts to C:\path\to\project\stations\
# 2. Set system environment variables (Windows Settings)
# 3. Test one script in PowerShell
python stations\maitri_data_input.py

# 4. Create batch file (see Option 4 above)
# 5. Schedule with Task Scheduler
# 6. Verify runs appear in logs/
```

---

## 8. System Health Check Script

Create `check_station_health.py`:

```python
import subprocess
import sys
from pathlib import Path
from config import DB_CONNECTION_STRING, ensure_directories_exist

def check_database():
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(DB_CONNECTION_STRING)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection OK")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_directories():
    try:
        ensure_directories_exist()
        print("✅ Directories OK")
        return True
    except Exception as e:
        print(f"❌ Directory creation failed: {e}")
        return False

def check_tables():
    try:
        from sqlalchemy import create_engine, inspect
        engine = create_engine(DB_CONNECTION_STRING)
        inspector = inspect(engine)
        tables = [
            'maitri_maitri', 'imd_bharati', 
            'himansh_himansh', 'himadri_radiometer_surface'
        ]
        
        for table in tables:
            if table in inspector.get_table_names():
                count = inspector.get_columns(table).__len__()
                print(f"  ✅ {table} ({count} columns)")
            else:
                print(f"  ❌ {table} NOT FOUND")
        return True
    except Exception as e:
        print(f"❌ Table check failed: {e}")
        return False

if __name__ == '__main__':
    print("=== Station Data Processing Health Check ===\n")
    print("1. Database Connection:")
    check_database()
    print("\n2. Directories:")
    check_directories()
    print("\n3. Database Tables:")
    check_tables()
    print("\n=== End Health Check ===")
```

Run with:
```bash
python check_station_health.py
```

---

Good luck! Questions? Check the logs in `logs/` directory for detailed error messages. 🚀
