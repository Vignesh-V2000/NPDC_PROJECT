#!/usr/bin/env python
import time
import requests

print("\nWaiting for server to be ready...")
time.sleep(3)

try:
    response = requests.get('http://localhost:10000/weather/api/weather/', timeout=5)
    print(f"✓ Server is running! Status: {response.status_code}")
    print(f"\nAPI Response:")
    data = response.json()
    
    for station, info in data.get('data', {}).items():
        print(f"\n{station.upper()}:")
        print(f"  Temperature: {info.get('temperature')}°C")
        print(f"  Date: {info.get('formatted_date')}")
        
except requests.exceptions.ConnectionError:
    print("✗ Server is not responding - still starting up or failed")
except Exception as e:
    print(f"✗ Error: {e}")
