"""
Unmanaged Django models for station temperature data.

These models map to PostgreSQL tables created by the official NPDC station
data processing scripts. They are "unmanaged" (managed = False) so Django
will never create, modify, or delete these tables via migrations.

Each station has its own table with its own schema.
"""
from django.db import models


# ---------------------
# Maitri (Antarctic)
# Table: maitri_maitri
# Source script: maitri_data_input.py
# ---------------------
class MaitriTemperature(models.Model):
    date = models.DateTimeField(primary_key=True, db_column='date')
    temp = models.FloatField(null=True, blank=True, db_column='temp')
    dew_point = models.FloatField(null=True, blank=True, db_column='dew_point')
    rh = models.FloatField(null=True, blank=True, db_column='rh')
    ap = models.FloatField(null=True, blank=True, db_column='ap')
    ws = models.FloatField(null=True, blank=True, db_column='ws')
    wd = models.FloatField(null=True, blank=True, db_column='wd')

    class Meta:
        managed = False
        db_table = 'maitri_maitri'
        ordering = ['-date']


# ---------------------
# Bharati (Antarctic)
# Table: imd_bharati
# Source script: last24HrsDataProcessing.py
# ---------------------
class BharatiTemperature(models.Model):
    obstime = models.DateTimeField(primary_key=True, db_column='obstime')
    tempr = models.FloatField(null=True, blank=True, db_column='tempr')
    ap = models.FloatField(null=True, blank=True, db_column='ap')
    ws = models.FloatField(null=True, blank=True, db_column='ws')
    wd = models.FloatField(null=True, blank=True, db_column='wd')
    rh = models.FloatField(null=True, blank=True, db_column='rh')

    class Meta:
        managed = False
        db_table = 'imd_bharati'
        ordering = ['-obstime']


# ---------------------
# Himansh (Himalaya)
# Table: himansh_himansh
# Source script: email_process_himansh.py
# ---------------------
class HimanshTemperature(models.Model):
    date = models.DateTimeField(primary_key=True, db_column='date')
    air_temp = models.FloatField(null=True, blank=True, db_column='air_temp')
    rh = models.FloatField(null=True, blank=True, db_column='rh')
    ap = models.FloatField(null=True, blank=True, db_column='ap')
    ws = models.FloatField(null=True, blank=True, db_column='ws')
    wd = models.FloatField(null=True, blank=True, db_column='wd')
    sur_temp = models.FloatField(null=True, blank=True, db_column='sur_temp')

    class Meta:
        managed = False
        db_table = 'himansh_himansh'
        ordering = ['-date']


# ---------------------
# Himadri (Arctic)
# Table: himadri_radiometer_surface
# Source script: himadri_data_process_radio_surface.py
# Temperature is in Kelvin
# ---------------------
class HimadriTemperature(models.Model):
    date = models.DateTimeField(primary_key=True, db_column='date')
    temperature = models.FloatField(null=True, blank=True, db_column='temperature')
    relative_humidity = models.FloatField(null=True, blank=True, db_column='relative_humidity')
    air_pressure = models.FloatField(null=True, blank=True, db_column='air_pressure')
    data_quality = models.CharField(max_length=50, null=True, blank=True, db_column='data_quality')

    class Meta:
        managed = False
        db_table = 'himadri_radiometer_surface'
        ordering = ['-date']
