import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.test import RequestFactory
from stations_weather.views import weather_api
import json

factory = RequestFactory()
request = factory.get('/weather/api/weather/')
response = weather_api(request)

if response.status_code == 200:
    data = json.loads(response.content)
    print("API Response:")
    print(json.dumps(data, indent=2))
else:
    print(f"Error: {response.status_code}")
    print(response.content)
