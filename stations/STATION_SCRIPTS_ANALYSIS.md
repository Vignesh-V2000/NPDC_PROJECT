# Station Data Processing Scripts - Analysis & Fixes

## Overview
Found 6 station data processing scripts in `e:\NPDC\NPDC_PROJECT\stations\`:
1. `maitri_data_input.py` - Maitri Station (Antarctica)
2. `last24HrsDataProcessing.py` - Bharati Station (Antarctica)  
3. `email_process_himansh.py` - Himansh Station (Himalaya) - email-based
4. `himansh_data_process_water_level.py` - Himansh Water Level
5. `himadri_data_process_radio_surface.py` - Himadri Station (Arctic)
6. `himadri_data_process_radio_surface_alt.py` - Himadri Alternative Radiometer

---

## Critical Issues Found

### ❌ Issue 1: Wrong Database Connection (MAJOR)
**Problem**: All scripts connect to `polardb` database, NOT `npdc_db`
- `maitri_data_input.py` (line 7): `'postgresql://postgres:postgres@localhost:5432/polardb'`
- `email_process_himansh.py` (line 56-62): `database="polardb"`
- `himansh_data_process_water_level.py` (line 32): `'postgresql://postgres:postgres@localhost:5432/polardb'`
- `himadri_data_process_radio_surface.py` (line 10): `database = "polardb"`
- `himadri_data_process_radio_surface_alt.py` (line 10): `database = "polardb"`
- `last24HrsDataProcessing.py` (line 98): `dbname='data_analysis'` (DIFFERENT DATABASE!)

**Impact**: 
- Data insertions fail silently or go to wrong database
- Tables are created/populated in wrong database
- Weather data never appears in NPDC system

**Fix**: Update all scripts to use correct NPDC database credentials

---

### ❌ Issue 2: Hard-coded Linux Paths (CRITICAL)
**Problem**: All scripts expect Linux paths that don't exist on Windows
- `maitri_data_input.py`: `'raw_data/Maitri/'`
- `last24HrsDataProcessing.py`: `'/opt/djangoProject/raw_data/DCWIS_NEW'`
- `email_process_himansh.py`: `'raw_data/Himansh'`
- `himansh_data_process_water_level.py`: `'raw_data/Himalaya/WaterLevel'`
- `himadri_data_process_radio_surface.py`: `'/opt/djangoProject/raw_data/Himadri/Radiometer/'`

**Impact**: 
- Scripts will fail when trying to read/write files
- Data directories don't exist
- Processing cannot complete

**Fix**: Make paths configurable or use proper project paths

---

### ❌ Issue 3: SQL Injection Vulnerabilities
**Location**: `email_process_himansh.py` (lines 103-104, 119)
```python
# VULNERABLE:
c.execute("SELECT * FROM himansh_email_headers WHERE email_id="+str(email_id))
c.execute("INSERT INTO himansh_email_headers (email_id, subject, date_time) VALUES ("+str(email_id)+", '"+subject+"', '"+date_time+"')")
```

**Impact**: 
- Subject line with quotes could break SQL
- Potential database attacks
- Crashes on certain email subjects

**Fix**: Use parameterized queries

---

### ❌ Issue 4: Hard-coded Email Credentials (SECURITY)
**Locations**:
- `email_process_himansh.py` (lines 60-62):
  ```python
  username = "himanshncpor@gmail.com"
  password = "xiozroyjxavbchiz"
  ```
- `himansh_data_process_water_level.py` (lines 14-15):
  ```python
  EMAIL_USER = "pnsharmancpor@gmail.com"
  EMAIL_PASS = "vqhxdcrvadojfyru"
  ```

**Impact**: 
- Credentials visible in source code
- Anyone with access can use these emails
- These seem to be app-specific passwords (not ideal)

**Fix**: Move to environment variables or settings file

---

### ❌ Issue 5: Hard-coded Database Credentials (SECURITY)
**All scripts** have hard-coded `postgres:postgres` credentials

**Fix**: Use Django database configuration instead

---

### ❌ Issue 6: Missing Data Directories
**Problem**: Scripts expect these directories to exist:
- `raw_data/Maitri/` - Maitri input files
- `raw_data/DCWIS_NEW/` - Bharati input files
- `raw_data/Himansh/` - Himansh email exports
- `raw_data/Himalaya/WaterLevel/` - Water level data
- `raw_data/Himadri/Radiometer/` - Himadri CSV data
- `process_data/Maitri/` - Output files
- `process_data/DCWIS/` - Output files
- `process_data/Himansh/` - Output files
- `process_data/Himalaya/WaterLevel/` - Output files
- `process_data/Himadri/Radiometer/` - Output files

**Fix**: Create these directories or make paths configurable

---

### ❌ Issue 7: Inconsistent Database Table Names
Some scripts use different column names:
- Maitri: `temp`, `dew_point`, `rh`, `ap`, `ws`, `wd`
- Bharati: `tempr`, `ap`, `ws`, `wd`, `rh` (no dew_point)
- Himansh: `air_temp`, `rh`, `ap`, `ws`, `wd`, `sur_temp`
- Himadri: `temperature`, `relative_humidity`, `air_pressure`

**Fix**: Standardize column names or document the differences

---

### ⚠️ Issue 8: No Error Handling
**Problem**: Scripts crash on errors with poor error messages
- `last24HrsDataProcessing.py`: Generic `except Exception as e: print(e)`
- No logging of which rows failed
- No rollback on partial failures

**Fix**: Add comprehensive error handling and logging

---

## Summary of Required Fixes

| Issue | Severity | Type | Fix |
|-------|----------|------|-----|
| Wrong database | **CRITICAL** | Config | Update all DB connections to use NPDC database |
| Linux paths | **CRITICAL** | Config | Make paths configurable or use project root |
| SQL injection | **HIGH** | Security | Use parameterized queries |
| Hard-coded credentials | **HIGH** | Security | Move to environment variables or Django settings |
| Missing directories | **HIGH** | Setup | Create data directories or make configurable |
| Inconsistent tables | **MEDIUM** | Config | Document or standardize column names |
| Error handling | **MEDIUM** | Quality | Add logging and error reporting |
| No logging | **MEDIUM** | Ops | Add comprehensive logging |

---

## Next Steps

1. ✅ Create fixed versions of all scripts
2. ✅ Update database configuration
3. ✅ Create required data directories
4. ✅ Remove hard-coded credentials
5. ✅ Add proper error handling
6. ⏳ Test with sample data
7. ⏳ Set up cron jobs for automated runs

---

## Scripts Status

### maitri_data_input.py
- **Purpose**: Read paired Excel files from Maitri station, merge weather data, insert into DB
- **Input**: `raw_data/Maitri/` (paired Excel files)
- **Output**: `maitri_maitri` table + CSV backup
- **Tables**: maitri_input_file (metadata), maitri_maitri (data)
- **Fix**: Changes needed ✅

### last24HrsDataProcessing.py
- **Purpose**: Process Bharati station DCWIS Excel files, convert to standard format
- **Input**: `raw_data/DCWIS_NEW/` (RW09 and Wind Excel files)
- **Output**: `last_24_hrs_data` and `imd_bharati` tables
- **Note**: Uses different database (`data_analysis`)!
- **Fix**: Changes needed ✅

### email_process_himansh.py
- **Purpose**: Fetch Himansh data from Gmail, extract CSV payload, insert into DB
- **Input**: Gmail IMAP
- **Output**: `himansh_himansh` table + CSV backup
- **Credentials**: Gmail app-specific password (secure but hard-coded)
- **Fix**: Changes needed ✅

### himansh_data_process_water_level.py
- **Purpose**: Fetch Himansh water level data from Gmail, process CSV
- **Input**: Gmail IMAP
- **Output**: `himansh_water_level` table
- **Fix**: Changes needed ✅

### himadri_data_process_radio_surface.py
- **Purpose**: Process Himadri radiometer CSV files, standardize format, insert into DB
- **Input**: `raw_data/Himadri/Radiometer/` (CSV files organized by year/month)
- **Output**: `himadri_radiometer_surface` table + monthly CSVs
- **Fix**: Changes needed ✅

### himadri_data_process_radio_surface_alt.py
- **Purpose**: Alternative Himadri radiometer processor (temperature altitude)
- **Input**: Same as above
- **Output**: `himadri_himadri_radiometer_temp_altitude` table
- **Fix**: Changes needed ✅

