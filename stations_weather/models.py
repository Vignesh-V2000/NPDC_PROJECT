from django.db import models


class MaitriWeatherData(models.Model):
    """Antarctica - Maitri Station Weather Data"""
    date = models.DateTimeField(primary_key=True, db_index=True)
    temp = models.FloatField(null=True, blank=True)  # Celsius
    dew_point = models.FloatField(null=True, blank=True)
    rh = models.FloatField(null=True, blank=True)  # Relative Humidity %
    ap = models.FloatField(null=True, blank=True)  # Atmospheric Pressure
    ap_1 = models.FloatField(null=True, blank=True, db_column='ap_1')
    ap_2 = models.FloatField(null=True, blank=True, db_column='ap_2')
    ws = models.FloatField(null=True, blank=True)  # Wind Speed
    wd = models.FloatField(null=True, blank=True)  # Wind Direction

    class Meta:
        db_table = 'maitri_maitri'
        managed = False
        verbose_name = "Maitri Weather Data"
        verbose_name_plural = "Maitri Weather Data"
        ordering = ['-date']
        indexes = [
            models.Index(fields=['-date']),
        ]


class BharatiWeatherData(models.Model):
    """Antarctica - Bharati Station Weather Data"""
    obstime = models.DateTimeField(primary_key=True, db_index=True)
    tempr = models.FloatField(null=True, blank=True)
    ap = models.FloatField(null=True, blank=True)
    ws = models.FloatField(null=True, blank=True)
    wd = models.FloatField(null=True, blank=True)
    rh = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'imd_bharati'
        managed = False
        verbose_name = "Bharati Weather Data"
        verbose_name_plural = "Bharati Weather Data"
        ordering = ['-obstime']


class HimadriWeatherData(models.Model):
    """Arctic - Himadri Station (Radiometer Surface) Weather Data"""
    date = models.DateTimeField(primary_key=True, db_index=True)
    temperature = models.FloatField(null=True, blank=True)  # Kelvin (stored as is)
    relative_humidity = models.FloatField(null=True, blank=True)  # %
    air_pressure = models.FloatField(null=True, blank=True)  # mBar
    data_quality = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'himadri_radiometer_surface'
        managed = False
        verbose_name = "Himadri Weather Data"
        verbose_name_plural = "Himadri Weather Data"
        ordering = ['-date']

    @property
    def temperature_celsius(self):
        """Convert Kelvin to Celsius"""
        if self.temperature:
            return self.temperature - 273.15
        return None


class HimanshWaterLevel(models.Model):
    """Himalaya - Himansh Station Water Level Data"""
    date = models.DateTimeField(primary_key=True, db_index=True)
    water_level = models.FloatField(null=True, blank=True)  # meters

    class Meta:
        db_table = 'himansh_water_level'
        managed = False
        verbose_name = "Himansh Water Level Data"
        verbose_name_plural = "Himansh Water Level Data"
        ordering = ['-date']


class HimanshWeatherData(models.Model):
    """Himalaya - Himansh Station Weather Data"""
    date = models.DateTimeField(primary_key=True, db_index=True)
    air_temp = models.FloatField(null=True, blank=True)
    rh = models.FloatField(null=True, blank=True)
    ap = models.FloatField(null=True, blank=True)
    ws = models.FloatField(null=True, blank=True)
    wd = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = 'himansh_himansh'
        managed = False
        verbose_name = "Himansh Weather Data"
        verbose_name_plural = "Himansh Weather Data"
        ordering = ['-date']


class Last24HrsData(models.Model):
    """Antarctic last 24 hours weather data"""
    obstime = models.TimeField(null=True, blank=True)
    tempr = models.FloatField(null=True, blank=True)
    ap = models.FloatField(null=True, blank=True)
    ws = models.FloatField(null=True, blank=True)
    wd = models.FloatField(null=True, blank=True)
    rh = models.FloatField(null=True, blank=True)
    date = models.DateField(db_index=True)

    class Meta:
        db_table = 'last_24_hrs_data'
        managed = False
        verbose_name = "Last 24 Hours Data"
        verbose_name_plural = "Last 24 Hours Data"
        ordering = ['-date']
