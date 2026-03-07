import os
import django
import json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.test import Client
from django.urls import reverse

client = Client()

print("=" * 100)
print("WEATHER API RESPONSE")
print("=" * 100)

# Get the weather API response
response = client.get('/weather/api/weather/')

print(f"\nStatus Code: {response.status_code}")
print(f"\nResponse JSON:")
data = response.json()
print(json.dumps(data, indent=2))

# Show what's being returned for each station
if data.get('status') == 'success':
    print("\n" + "=" * 100)
    print("EXTRACTED STATION DATES")
    print("=" * 100)
    
    for station, info in data.get('data', {}).items():
        if info.get('formatted_date'):
            print(f"\n{station.upper()}:")
            print(f"  Raw date: {info.get('date')}")
            print(f"  Formatted: {info.get('formatted_date')}")
            print(f"  Temperature: {info.get('temperature')}°C")
