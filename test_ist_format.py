import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from datetime import datetime
from pytz import timezone as pytz_timezone
from stations_weather.views import convert_to_ist, format_date_ist

IST = pytz_timezone('Asia/Kolkata')

print("=" * 100)
print("TESTING CORRECTED TIMEZONE CONVERSION")
print("=" * 100)

# Test with time that would appear as March 5 11:00 PM IST
print("\nTest: Database stores 2026-03-05 23:00:00 (which is already IST)")
db_value = datetime(2026, 3, 5, 23, 0, 0)  # This is 11:00 PM IST
print(f"  Input (naive, stored as IST): {db_value}")
converted = convert_to_ist(db_value)
print(f"  After convert_to_ist: {converted}")
formatted = format_date_ist(db_value)
print(f"  Formatted: {formatted}")
print(f"  ✓ Should show '05 Mar 2026 11:00 PM'")

print("\n" + "=" * 100)
print("If you're seeing this correct format on the live server,")
print("the timezone fix is working properly!")
print("=" * 100)
