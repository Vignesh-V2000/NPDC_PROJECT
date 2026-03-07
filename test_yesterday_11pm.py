import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.test import Client
import json

client = Client()

print("=" * 100)
print("TESTING YESTERDAY 11 PM DATA FILTER")
print("=" * 100)

response = client.get('/weather/api/weather/')
data = response.json()

print(f"\nAPI Response Status: {response.status_code}\n")

if data.get('status') == 'success':
    for station, info in data.get('data', {}).items():
        print(f"{station.upper()}:")
        print(f"  Date: {info.get('formatted_date')}")
        print(f"  Temperature: {info.get('temperature')}°C")
        print()
else:
    print(f"Status: {data.get('status')}")
    print(f"Error: {data.get('message')}")

print("=" * 100)
print("Expected: All stations showing 'yesterday at 11:00 PM' data")
print("=" * 100)
