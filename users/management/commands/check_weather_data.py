"""
Django management command to check station weather data.

Usage:
    python manage.py check_weather_data
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Check station temperature data in database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 80))
        self.stdout.write(self.style.SUCCESS('STATION WEATHER DATA DIAGNOSTIC'))
        self.stdout.write(self.style.SUCCESS('=' * 80))

        stations = [
            {
                'key': 'maitri',
                'name': 'Maitri',
                'location': 'Antarctica - Maitri',
                'table': 'maitri_maitri',
                'temp_col': 'temp',
                'date_col': 'date',
            },
            {
                'key': 'bharati',
                'name': 'Bharati',
                'location': 'Antarctica - Bharati',
                'table': 'imd_bharati',
                'temp_col': 'tempr',
                'date_col': 'obstime',
            },
            {
                'key': 'himansh',
                'name': 'Himansh',
                'location': 'Himalaya - Himansh',
                'table': 'himansh_himansh',
                'temp_col': 'air_temp',
                'date_col': 'date',
            },
            {
                'key': 'himadri',
                'name': 'Himadri',
                'location': 'Arctic - Himadri',
                'table': 'himadri_radiometer_surface',
                'temp_col': 'temperature',
                'date_col': 'date',
            },
        ]

        for station in stations:
            self.stdout.write(f"\n{'-' * 80}")
            self.stdout.write(f"STATION: {station['name']} ({station['location']})")
            self.stdout.write(f"Table: {station['table']}")
            self.stdout.write(f"{'-' * 80}")

            try:
                with connection.cursor() as cursor:
                    # Check if table exists
                    cursor.execute(
                        "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = %s)",
                        [station['table']]
                    )
                    table_exists = cursor.fetchone()[0]

                    if not table_exists:
                        self.stdout.write(
                            self.style.ERROR(f"❌ TABLE DOES NOT EXIST: {station['table']}")
                        )
                        continue

                    self.stdout.write(self.style.SUCCESS(f"✓ Table exists"))

                    # Get column info
                    cursor.execute(
                        """
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = %s 
                        ORDER BY ordinal_position
                        """,
                        [station['table']]
                    )
                    columns = cursor.fetchall()
                    self.stdout.write(f"\nColumns ({len(columns)}):")
                    for col_name, col_type in columns:
                        self.stdout.write(f"  • {col_name}: {col_type}")

                    # Count rows
                    cursor.execute(f"SELECT COUNT(*) FROM {station['table']}")
                    total_rows = cursor.fetchone()[0]
                    self.stdout.write(f"\nTotal rows: {total_rows}")

                    if total_rows == 0:
                        self.stdout.write(
                            self.style.WARNING("⚠️  TABLE IS EMPTY - No data")
                        )
                        continue

                    # Check rows with temperature
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {station['table']} WHERE {station['temp_col']} IS NOT NULL"
                    )
                    rows_with_temp = cursor.fetchone()[0]
                    self.stdout.write(f"Rows with temperature: {rows_with_temp}")

                    # Temperature stats
                    cursor.execute(
                        f"""
                        SELECT 
                            MIN({station['temp_col']}) as min_temp,
                            MAX({station['temp_col']}) as max_temp,
                            AVG({station['temp_col']}) as avg_temp
                        FROM {station['table']} 
                        WHERE {station['temp_col']} IS NOT NULL
                        """
                    )
                    min_t, max_t, avg_t = cursor.fetchone()
                    self.stdout.write(f"\nTemperature Statistics:")
                    self.stdout.write(f"  Min: {min_t}")
                    self.stdout.write(f"  Max: {max_t}")
                    self.stdout.write(f"  Avg: {avg_t}")

                    # Latest records
                    self.stdout.write(f"\nLatest Records (Last 5):")
                    cursor.execute(
                        f"""
                        SELECT {station['date_col']}, {station['temp_col']}
                        FROM {station['table']}
                        WHERE {station['temp_col']} IS NOT NULL
                        ORDER BY {station['date_col']} DESC
                        LIMIT 5
                        """
                    )
                    latest = cursor.fetchall()
                    if latest:
                        for i, (date_val, temp_val) in enumerate(latest, 1):
                            self.stdout.write(f"  {i}. {date_val} → {temp_val}")
                    else:
                        self.stdout.write("  ❌ No records found with temperature data")

                    # Value distribution
                    cursor.execute(
                        f"""
                        SELECT {station['temp_col']}, COUNT(*) as count
                        FROM {station['table']}
                        GROUP BY {station['temp_col']}
                        ORDER BY count DESC
                        LIMIT 10
                        """
                    )
                    dist = cursor.fetchall()
                    self.stdout.write(f"\nTemperature Value Distribution (Top 10):")
                    for temp_val, count in dist:
                        if temp_val is None:
                            self.stdout.write(f"  NULL: {count} records")
                        elif temp_val <= -999:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"  {temp_val} (SENTINEL - Missing data): {count} records"
                                )
                            )
                        else:
                            self.stdout.write(f"  {temp_val}: {count} records")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ ERROR: {e}"))

        self.stdout.write(f"\n{self.style.SUCCESS('=' * 80)}")
        self.stdout.write(self.style.SUCCESS("DIAGNOSIS"))
        self.stdout.write(self.style.SUCCESS('=' * 80))
        
        self.stdout.write("""
If temperatures show as 0 or missing:

1. ❌ TABLE DOESN'T EXIST
   → Station data tables not created yet
   → Need to run data processing scripts

2. ❌ TABLE IS EMPTY  
   → Tables exist but have no data
   → Check if cron jobs are running

3. ❌ SENTINEL VALUES (-999)
   → Data exists but marked as invalid
   → Stations aren't reporting recent data

4. ❌ WRONG DATABASE
   → Django connecting to wrong database
   → Check settings.py DATABASES config

5. ❌ COLUMN MISMATCH
   → Column names don't match models
   → Update users/station_models.py
        """)
