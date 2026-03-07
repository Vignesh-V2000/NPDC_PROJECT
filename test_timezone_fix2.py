import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from datetime import datetime
from pytz import timezone as pytz_timezone
from stations_weather.views import convert_to_ist, format_date_ist

print("=" * 100)
print("TIMEZONE CONVERSION TEST")
print("=" * 100)

# Test with actual database values
# Database stored as: 2026-03-06 10:10:55 (which is actually UTC)
# Should convert to: 2026-03-06 15:40:55 IST

print("\nTest: Database value 2026-03-06 10:10:55 (UTC)")
db_value = datetime(2026, 3, 6, 10, 10, 55)  # This is naive but represents UTC
print(f"  Input (naive, interpreted as UTC): {db_value}")
converted = convert_to_ist(db_value)
print(f"  After convert_to_ist: {converted}")
formatted = format_date_ist(db_value)
print(f"  Formatted for display: {formatted}")
print(f"  ✓ Should show '06 Mar 2026 03:40 PM' in IST")

print("\nTest: Database value 2026-03-06 15:47:12 (UTC)")
db_value2 = datetime(2026, 3, 6, 15, 47, 12)  # UTC
print(f"  Input (naive, interpreted as UTC): {db_value2}")
converted2 = convert_to_ist(db_value2)
print(f"  After convert_to_ist: {converted2}")
formatted2 = format_date_ist(db_value2)
print(f"  Formatted for display: {formatted2}")
print(f"  ✓ Should show '06 Mar 2026 09:17 PM' in IST")

print("\n" + "=" * 100)
print("If the formatted dates above match expectations, the timezone fix is working!")
print("=" * 100)
