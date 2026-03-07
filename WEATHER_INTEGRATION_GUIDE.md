# Live Weather Station Integration Guide

## Overview
The new NPDC website has been integrated with live weather data from Indian polar research stations. This guide explains how to set up and use the system.

## Architecture

### Backend Components
1. **Django App**: `stations_weather` - Handles weather data models and API endpoints
2. **Models**: Read-only models for existing database tables:
   - `MaitriWeatherData` → `maitri_maitri` table
   - `BharatiWeatherData` → `imd_bharati` table
   - `HimadriWeatherData` → `himadri_radiometer_surface` table
   - `HimanshWaterLevel` → `himansh_water_level` table

3. **API Endpoints**:
   - `/weather/api/weather/` - Returns current data for all stations
   - `/weather/api/weather/<station_code>/` - Returns data for specific station

### Frontend Components
1. **HTML**: Weather cards with data attributes in `templates/home.html`
2. **JavaScript**: Fetch and display live data in `templates/base.html`
3. **Refresh Interval**: 30 minutes (configurable)

---

## Setup Instructions

### Step 1: Create Database Tables
The weather data tables must exist in your PostgreSQL database. The old website scripts populate these tables.

Run the following to create the tables (if they don't exist):

```sql
-- Maitri table
CREATE TABLE IF NOT EXISTS maitri_maitri (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP,
    temperature FLOAT,
    humidity FLOAT,
    pressure FLOAT,
    wind_speed FLOAT,
    wind_direction FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bharati table  
CREATE TABLE IF NOT EXISTS imd_bharati (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP,
    temperature FLOAT,
    humidity FLOAT,
    pressure FLOAT,
    wind_speed FLOAT,
    wind_direction FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Himadri table
CREATE TABLE IF NOT EXISTS himadri_radiometer_surface (
    id SERIAL PRIMARY KEY,
    date TIMESTAMP,
    temperature FLOAT,
    relative_humidity FLOAT,
    air_pressure FLOAT,
    data_quality INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Himansh table
CREATE TABLE IF NOT EXISTS himansh_water_level (
    id SERIAL PRIMARY KEY,
    date_time TIMESTAMP,
    water_level FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes for performance
CREATE INDEX idx_maitri_date ON maitri_maitri(date DESC);
CREATE INDEX idx_bharati_date ON imd_bharati(date DESC);
CREATE INDEX idx_himadri_date ON himadri_radiometer_surface(date DESC);
CREATE INDEX idx_himansh_datetime ON himansh_water_level(date_time DESC);
```

### Step 2: Populate Data Using Old Scripts
Use the scripts from the `stations/` folder to populate the tables:

```bash
# Process and insert Maitri data
python stations/maitri_data_input.py

# Process Himadri radiometer data
python stations/himadri_data_process_radio_surface.py

# Process Himansh water level data (email-based)
python stations/himansh_data_process_water_level.py

# Process last 24 hours data
python stations/last24HrsDataProcessing.py
```

### Step 3: Verify Django App
Check that the app is properly configured:

```bash
python manage.py check
```

All systems should come back with no errors.

### Step 4: Test the API

```bash
# Test the main weather endpoint
curl http://localhost:8000/weather/api/weather/

# Test individual station endpoint
curl http://localhost:8000/weather/api/weather/maitri/
curl http://localhost:8000/weather/api/weather/bharati/
curl http://localhost:8000/weather/api/weather/himadri/
curl http://localhost:8000/weather/api/weather/himansh/
```

### Step 5: View on Website
- Navigate to the homepage (`/`)
- The weather cards will auto-fetch and display live data
- Check browser console for any errors

---

## API Response Format

### Success Response
```json
{
  "status": "success",
  "data": {
    "maitri": {
      "name": "Antarctica - Maitri",
      "temperature": -3.9,
      "humidity": 85.2,
      "pressure": 1012.5,
      "wind_speed": 15.3,
      "wind_direction": 120.0,
      "date": "2026-03-06T11:00:00",
      "formatted_date": "06 Mar 2026 11:00 AM"
    },
    "bharati": { ... },
    "himadri": { ... },
    "himansh": { ... }
  },
  "timestamp": "2026-03-07T10:30:45.123456"
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Tables not yet populated"
}
```

---

## Customization

### Change Refresh Interval
Edit `templates/base.html` and change the interval in the weather script:

```javascript
// Change from 30 minutes (30 * 60 * 1000) to your desired interval
setInterval(fetchWeatherData, 60 * 60 * 1000); // 60 minutes
```

### Add New Station
1. Create a model in `stations_weather/models.py`
2. Add fetch logic in `stations_weather/views.py`
3. Update HTML card in `templates/home.html`
4. Add data-station attribute to the card

---

## Troubleshooting

### Issue: "Tables don't exist" Error
**Solution**: Run the database table creation SQL and populate with old scripts

### Issue: No Data Displays
**Solution**: 
1. Check API endpoint: `curl http://localhost:8000/weather/api/weather/`
2. Check browser developer console for JavaScript errors
3. Verify table has data: `SELECT COUNT(*) FROM maitri_maitri;`

### Issue: Data Stale for 30+ Minutes
**Solution**: The page refreshes every 30 minutes. To check current data manually, reload the page or adjust the refresh interval.

### Issue: CORS or Permission Errors
**Solution**: The API is configured with `@csrf_exempt` and should work from any endpoint. Check firewall rules.

---

## Files Modified/Created

### New Files
- `stations_weather/` - New Django app
  - `__init__.py`
  - `apps.py` 
  - `models.py`
  - `views.py`
  - `urls.py`

### Modified Files
- `npdc_site/settings.py` - Added `stations_weather` to INSTALLED_APPS
- `npdc_site/urls.py` - Added weather URL routing
- `templates/home.html` - Updated weather cards with data attributes
- `templates/base.html` - Added weather data fetching JavaScript

---

## Future Enhancements

1. **WebSocket Updates**: Real-time data push instead of polling
2. **Database Caching**: Cache frequently accessed data
3. **Mobile Optimization**: Smaller cards for mobile devices
4. **Historical Data**: Show temperature trends and graphs
5. **Alerts**: Notify when temperature exceeds thresholds

---

## Contact & Support

For issues or questions about the weather integration, contact the NPDC team.
