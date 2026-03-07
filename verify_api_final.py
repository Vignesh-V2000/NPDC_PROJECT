import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.test import Client
import json

client = Client()

print("=" * 100)
print("FINAL WEATHER API VERIFICATION")
print("=" * 100)

response = client.get('/weather/api/weather/')
data = response.json()

print(f"\nAPI Response Status: {response.status_code}")
print(f"Response Body:\n")
print(json.dumps(data, indent=2))

print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

if data.get('status') == 'success':
    for station, info in data.get('data', {}).items():
        print(f"\n{station.upper()}:")
        print(f"  ✓ Date: {info.get('formatted_date')}")
        print(f"  ✓ Temperature: {info.get('temperature')}°C")
