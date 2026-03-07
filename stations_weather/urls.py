from django.urls import path
from . import views

app_name = 'stations_weather'

urlpatterns = [
    path('api/weather/', views.weather_api, name='weather_api'),
    path('api/weather/<str:station_code>/', views.weather_station, name='weather_station'),
]
