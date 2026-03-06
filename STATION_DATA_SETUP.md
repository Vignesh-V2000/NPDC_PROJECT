# Station Weather Data Setup Guide

## Current Status
❌ **Station tables do NOT exist in the database**

The following tables are missing:
- `maitri_maitri`
- `imd_bharati`
- `himansh_himansh`
- `himadri_radiometer_surface`

## Solutions (Choose One)

### Option 1: Run Official Data Processing Scripts (RECOMMENDED)
The station data is populated by external Python scripts that fetch data from various sources.

**Scripts to run:**
```bash
# Maitri Station (Antarctica)
python scripts/maitri_data_input.py

# Bharati Station (Antarctica)
python scripts/last24HrsDataProcessing.py

# Himansh Station (Himalaya)
python scripts/email_process_himansh.py

# Himadri Station (Arctic)
python scripts/himadri_data_process_radio_surface.py
```

**These scripts need to be run:**
- When first setting up the system
- Periodically via cron jobs (e.g., every 12 hours or daily)
- After data sources are available

**Steps:**
1. Locate the data processing scripts on your server
2. Configure data source connections (email, API, files, database connections)
3. Run scripts to populate the tables
4. Set up cron jobs for automatic updates

---

### Option 2: Create Tables Manually with Sample Data
If you don't have access to the data processing scripts, create the tables manually.

```sql
-- Maitri Station
CREATE TABLE maitri_maitri (
    date TIMESTAMP PRIMARY KEY,
    temp FLOAT,
    dew_point FLOAT,
    rh FLOAT,
    ap FLOAT,
    ws FLOAT,
    wd FLOAT
);

-- Bharati Station
CREATE TABLE imd_bharati (
    obstime TIMESTAMP PRIMARY KEY,
    tempr FLOAT,
    ap FLOAT,
    ws FLOAT,
    wd FLOAT,
    rh FLOAT
);

-- Himansh Station
CREATE TABLE himansh_himansh (
    date TIMESTAMP PRIMARY KEY,
    air_temp FLOAT,
    rh FLOAT,
    ap FLOAT,
    ws FLOAT,
    wd FLOAT,
    sur_temp FLOAT
);

-- Himadri Station
CREATE TABLE himadri_radiometer_surface (
    date TIMESTAMP PRIMARY KEY,
    temperature FLOAT,
    relative_humidity FLOAT,
    air_pressure FLOAT,
    data_quality VARCHAR(50)
);

-- Insert sample data (optional)
INSERT INTO maitri_maitri VALUES 
  (NOW(), -25.5, -35.2, 65, 980, 15.3, 270);

INSERT INTO imd_bharati VALUES 
  (NOW(), -18.2, 975, 12.1, 260, 70);

INSERT INTO himansh_himansh VALUES 
  (NOW(), -12.3, 55, 650, 8.5, 300, -15.1);

INSERT INTO himadri_radiometer_surface VALUES 
  (NOW(), 268.5, 78, 1010, 'Good');
```

---

### Option 3: Set Up Secondary Database (polardb)
If station data is in a separate `polardb` database, configure Django to use it.

**Step 1: Update settings.py**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'npdc_db',
        'HOST': 'localhost',
        'PORT': '5432',
        'USER': 'npdc_user',
        'PASSWORD': 'password',
    },
    'polardb': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'polardb',
        'HOST': '172.27.11.202',  # Adjust to actual host
        'PORT': '5444',            # Adjust to actual port
        'USER': 'polardb_user',    # Adjust to actual user
        'PASSWORD': 'password',    # Adjust to actual password
    }
}
```

**Step 2: Update users/station_models.py**
```python
class MaitriTemperature(models.Model):
    # ... existing fields ...
    class Meta:
        managed = False
        db_table = 'maitri_maitri'
        app_label = 'users'
```

**Step 3: Update users/views.py get_station_temperatures()**
```python
from django.db import connections

def get_station_temperatures():
    # ... existing code ...
    results = []
    
    # Try polardb connection if available
    try:
        db_alias = 'polardb'
        connection = connections[db_alias]
        with connection.cursor() as cursor:
            # ... existing queries using this cursor ...
    except Exception as e:
        logger.error(f"Failed to connect to polardb: {e}")
        # Fallback to default database or return empty list
```

---

## Quick Diagnosis Commands

### Check if tables exist
```sql
-- In PostgreSQL
\dt maitri* imd* himansh* himadri*

-- Or via SQL
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('maitri_maitri', 'imd_bharati', 'himansh_himansh', 'himadri_radiometer_surface');
```

### Check table contents
```sql
SELECT COUNT(*) FROM maitri_maitri;
SELECT * FROM maitri_maitri ORDER BY date DESC LIMIT 5;
```

### Run Django diagnostic command
```bash
python manage.py check_weather_data
```

---

## Automated Solution (Recommended)

### Set up Cron Jobs
Add to crontab to run data scripts periodically:

```bash
# Every 12 hours - fetch latest weather data
0 */12 * * * cd /path/to/npdc_project && python scripts/maitri_data_input.py >> /var/log/maitri_data.log 2>&1
0 */12 * * * cd /path/to/npdc_project && python scripts/last24HrsDataProcessing.py >> /var/log/bharati_data.log 2>&1
0 */12 * * * cd /path/to/npdc_project && python scripts/email_process_himansh.py >> /var/log/himansh_data.log 2>&1
0 */12 * * * cd /path/to/npdc_project && python scripts/himadri_data_process_radio_surface.py >> /var/log/himadri_data.log 2>&1
```

### Monitor Data Freshness
Create a Django management command to alert if data is stale:

```bash
python manage.py check_data_freshness
```

---

## Current Workaround

✅ **Done:** The home page will gracefully handle missing weather data
- Weather section hidden if no data available
- No errors in logs
- Home page loads normally

**To enable weather display:**
1. Create the station tables
2. Populate with data
3. Restart Django app
4. Weather cards will appear automatically

---

## Files to Check

- **Models:** `users/station_models.py`
- **Data Fetching:** `users/views.py` → `get_station_temperatures()` function
- **Template:** `templates/home.html` → Weather section
- **Data Processing Scripts:** See instructions above

---

## Next Steps

1. ✅ Fallback applied (weather section hidden gracefully)
2. ⏳ **You need to:** Set up one of the three options above
3. ✅ Monitor with: `python manage.py check_weather_data`
