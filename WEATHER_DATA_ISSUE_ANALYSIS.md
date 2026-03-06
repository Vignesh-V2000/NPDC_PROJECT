# Weather Data Issue - Analysis & Solutions

## Problem
Weather and temperature data at polar stations (Maitri, Bharati, Himansh, Himadri) are displaying as **zero or missing** on the home page instead of showing actual temperature readings.

## Current Architecture

### Data Flow
```
Station Data Processing Scripts (external)
    ↓
PostgreSQL Tables (polardb or separate DB)
    ↓
Django Unmanaged Models (users/station_models.py)
    ↓
get_station_temperatures() function (users/views.py)
    ↓
home.html template (displays weather cards)
```

### Station Tables

| Station | Table | Temp Column | Date Column | Source |
|---------|-------|------------|-------------|--------|
| Maitri (Antarctic) | `maitri_maitri` | `temp` | `date` | maitri_data_input.py |
| Bharati (Antarctic) | `imd_bharati` | `tempr` | `obstime` | last24HrsDataProcessing.py |
| Himansh (Himalaya) | `himansh_himansh` | `air_temp` | `date` | email_process_himansh.py |
| Himadri (Arctic) | `himadri_radiometer_surface` | `temperature` | `date` | himadri_data_process_radio_surface.py |

## Root Cause Analysis

### Possible Issues (in order of likelihood)

#### 1. ❌ Station Tables Don't Exist
**Symptom**: `get_station_temperatures()` returns None for all stations
**Cause**: The station data tables were never created or are in a different database
**Fix**: 
- Run the official NPDC station data processing scripts
- Check if tables exist: `\dt` in psql
- Verify database connection in settings.py

#### 2. ❌ Station Tables Are Empty
**Symptom**: Tables exist but have 0 rows
**Cause**: Data processing scripts haven't run or cron jobs are disabled
**Fix**:
- Check cron logs: `/var/log/cron` on production
- Run data processing scripts manually
- Verify data source feeds (email, API, files)

#### 3. ❌ Silent Exception in get_station_temperatures()
**Symptom**: Function catches all exceptions but logs nothing visible
**Cause**: The function has `except Exception as e: pass` which silently fails
**Fix**: Add better error logging (see solution below)

#### 4. ❌ Column Name Mismatch
**Symptom**: Table exists but columns don't match model definitions
**Cause**: schema mismatch between station_models.py and actual database
**Fix**: Verify column names in actual database match model definitions

#### 5. ❌ Wrong Database Connection
**Symptom**: Django is connecting to wrong database or polardb is unreachable
**Cause**: Connection string in settings.py is incorrect
**Fix**: Verify DATABASES configuration

#### 6. ❌ Data is Sentinel Values (-999)
**Symptom**: Tables have data but all values are -999 (missing data code)
**Cause**: Stations aren't reporting data, or data quality check failed
**Fix**: This is expected, handle in template to show "No Data" instead of -999

## How to Diagnose

### Step 1: Run Diagnostic Script
```bash
cd /path/to/npdc_project
python manage.py shell < check_station_weather_data.py
```

This will show:
- ✓ Which tables exist
- ✓ If they have data
- ✓ Latest temperature values
- ✓ Any sentinel values (-999)
- ✓ Temperature statistics

### Step 2: Check Database Directly
```sql
-- Check if tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('maitri_maitri', 'imd_bharati', 'himansh_himansh', 'himadri_radiometer_surface');

-- Count rows in each
SELECT COUNT(*) FROM maitri_maitri;
SELECT COUNT(*) FROM imd_bharati;
SELECT COUNT(*) FROM himansh_himansh;
SELECT COUNT(*) FROM himadri_radiometer_surface;

-- Get latest data
SELECT * FROM maitri_maitri ORDER BY date DESC LIMIT 1;
SELECT * FROM imd_bharati ORDER BY obstime DESC LIMIT 1;
SELECT * FROM himansh_himansh ORDER BY date DESC LIMIT 1;
SELECT * FROM himadri_radiometer_surface ORDER BY date DESC LIMIT 1;
```

### Step 3: Check Django Connection
```python
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT * FROM maitri_maitri LIMIT 1;")
    print(cursor.fetchall())
```

## Solutions

### Solution 1: Improve Error Logging (IMMEDIATE)
Update [users/views.py](e:\NPDC\NPDC_PROJECT\users\views.py) `get_station_temperatures()` function to log actual errors:

```python
import logging
logger = logging.getLogger('station_weather')

def get_station_temperatures():
    # ... existing code ...
    
    for station in stations:
        try:
            with connection.cursor() as cursor:
                cursor.execute(...)  # existing query
        except Exception as e:
            # Instead of: pass
            # Add logging:
            logger.error(
                f"Station {station['name']}: Failed to fetch from {station['table']} - {str(e)}"
            )
            # Check if table exists
            try:
                with connection.cursor() as test_cursor:
                    test_cursor.execute(
                        "SELECT 1 FROM information_schema.tables WHERE table_name = %s",
                        [station['table']]
                    )
                    exists = test_cursor.fetchone()[0]
                    logger.warning(f"  → Table '{station['table']}' exists: {bool(exists)}")
            except:
                pass
```

### Solution 2: Handle Sentinel Values (MEDIUM)
Update [templates/home.html](e:\NPDC\NPDC_PROJECT\templates\home.html) to properly display missing data:

```html
{% if st.temperature is not None and st.temperature > -999 %}
    <div class="temperature-display my-1">
        <i class="fas fa-thermometer-half me-2"></i>
        <span class="fw-temp {% if st.temperature < 0 %}temp-negative{% else %}temp-positive{% endif %}">
            {{ st.temperature }}&deg; C
        </span>
    </div>
{% else %}
    <div class="temperature-display my-1 text-muted" style="font-size: 0.85rem;">
        <i class="fas fa-ban me-2"></i>No data available
    </div>
{% endif %}
```

### Solution 3: Create Fallback to Alternative Database (ADVANCED)
If station data is in a separate `polardb` database, configure Django to use it:

In [npdc_site/settings.py](e:\NPDC\NPDC_PROJECT\npdc_site\settings.py):
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'npdc_db',
        'HOST': '127.0.0.1',
        'PORT': '5432',
        # ... other settings
    },
    'polardb': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'polardb',
        'HOST': '127.0.0.1',
        'PORT': '5432',
        # ... other settings
    }
}
```

Then update model routing to use 'polardb' for station models.

### Solution 4: Implement Caching (PERFORMANCE)
Cache station temperatures to reduce database queries:

```python
from django.core.cache import cache

def get_station_temperatures():
    # Check cache first
    cached = cache.get('station_temperatures')
    if cached:
        return cached
    
    # Fetch fresh data...
    results = [...]
    
    # Cache for 30 minutes
    cache.set('station_temperatures', results, 60 * 30)
    
    return results
```

### Solution 5: Add Manual Data Entry Admin Interface (FALLBACK)
Create Django admin interface to manually update station temperatures if automated data feed fails:

```python
# In users/admin.py
from .station_models import MaitriTemperature, BharatiTemperature

class StationTemperatureAdmin(admin.ModelAdmin):
    list_display = ['date', 'temp', 'rh', 'ws']
    list_filter = ['date']
    search_fields = ['date']

admin.site.register(MaitriTemperature, StationTemperatureAdmin)
admin.site.register(BharatiTemperature, StationTemperatureAdmin)
# ... repeat for other stations
```

## Next Steps

### Immediate (Today)
1. ✅ Run the diagnostic script: `check_station_weather_data.py`
2. ✅ Share diagnostic output
3. ✅ Check if station tables exist in database

### Short-term (This Week)
1. Improve error logging in `get_station_temperatures()`
2. Update template to handle missing data better
3. Identify if data processing scripts are running

### Medium-term (This Month)
1. Verify data sources and processing scripts
2. Fix any database connection issues
3. Set up monitoring for data freshness

### Long-term (Architecture)
1. Create admin interface for manual data entry fallback
2. Implement caching for performance
3. Add data quality checks
4. Set up alerts for stale data

## Commands to Run

### Check Station Weather Data
```bash
cd /path/to/npdc_project
python manage.py shell < check_station_weather_data.py
```

### Check Database Tables Directly
```bash
psql -U npdc_user -d npdc_db
\dt maitri* imd* himansh* himadri*
SELECT COUNT(*) FROM maitri_maitri;
SELECT * FROM maitri_maitri ORDER BY date DESC LIMIT 1;
```

### Test in Django Shell
```bash
python manage.py shell
from users.views import get_station_temperatures
temps = get_station_temperatures()
for t in temps:
    print(f"{t['name']}: {t['temperature']}°C at {t['date']}")
```

## References

- [Station Models](users/station_models.py)
- [Temperature Fetching Function](users/views.py#L396)
- [Home Template Weather Section](templates/home.html#L1240)
- Data Processing Scripts:
  - maitri_data_input.py (external)
  - last24HrsDataProcessing.py (external)
  - email_process_himansh.py (external)
  - himadri_data_process_radio_surface.py (external)
