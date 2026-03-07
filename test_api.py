import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.test import Client

client = Client()
response = client.get('/weather/api/weather/')
data = response.json()

print("=" * 80)
print("WEATHER API TEST")
print("=" * 80)

if data.get('status') == 'success':
    print("\nStatus: SUCCESS\n")
    for station, info in data.get('data', {}).items():
        print(f"{station.upper()}")
        print(f"  Date: {info.get('formatted_date')}")
        print(f"  Temperature: {info.get('temperature')}°C")
        print()
else:
    print(f"\nStatus: {data.get('status')}")
    print(f"Error: {data.get('message')}")
