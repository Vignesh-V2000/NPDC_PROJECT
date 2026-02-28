"""
Management command to migrate data from legacy PostgreSQL tables
(metadata_main_table, scientist_details, gps_data_collection, etc.)
into Django ORM models (DatasetSubmission + related models).
"""

import datetime
import re
from django.core.management.base import BaseCommand
from django.db import connection
from django.contrib.auth.models import User
from data_submission.models import (
    DatasetSubmission,
    DatasetCitation,
    ScientistDetail,
    InstrumentMetadata,
    PlatformMetadata,
    GPSMetadata,
    LocationMetadata,
    DataResolutionMetadata,
    PaleoTemporalCoverage,
    LegacyUser,
    DataCenter,
    Reference,
    NPDCMaster,
)


def safe_str(val, max_len=None, default=''):
    """Safely convert a value to string, truncating if needed."""
    if val is None:
        return default
    s = str(val).strip()
    if max_len:
        s = s[:max_len]
    return s if s else default


def safe_float(val, default=0.0):
    """Safely convert to float."""
    if val is None:
        return default
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default


def dms_to_decimal(deg, minutes, sec):
    """Convert DMS (degrees, minutes, seconds) to decimal degrees."""
    d = safe_float(deg, 0.0)
    m = safe_float(minutes, 0.0)
    s = safe_float(sec, 0.0)
    if d == 0.0 and m == 0.0 and s == 0.0:
        return None
    sign = -1 if d < 0 else 1
    return sign * (abs(d) + m / 60.0 + s / 3600.0)


def parse_date(date_str, default=None):
    """Try multiple date formats."""
    if not date_str or not str(date_str).strip():
        return default
    date_str = str(date_str).strip()
    formats = [
        '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y',
        '%Y/%m/%d', '%d %b %Y', '%d %B %Y', '%Y',
    ]
    for fmt in formats:
        try:
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    # Try extracting year
    year_match = re.search(r'(\d{4})', date_str)
    if year_match:
        try:
            return datetime.date(int(year_match.group(1)), 1, 1)
        except ValueError:
            pass
    return default


def map_expedition_type(location_type):
    """Map legacy location_type to Django expedition_type."""
    if not location_type:
        return 'antarctic'
    lt = location_type.strip().lower()
    mapping = {
        'antarctic': 'antarctic',
        'antarctica': 'antarctic',
        'arctic': 'arctic',
        'ocean': 'southern_ocean',
        'southern ocean': 'southern_ocean',
        'indian ocean sector': 'southern_ocean',
        'himalaya': 'himalaya',
    }
    return mapping.get(lt, 'antarctic')


def map_category(sci_key_category):
    """Map legacy category to Django category choice."""
    if not sci_key_category:
        return 'atmosphere'
    cat = sci_key_category.strip().lower()
    # Direct matches
    mapping = {
        'agriculture': 'agriculture',
        'atmosphere': 'atmosphere',
        'biological classification': 'biological_classification',
        'biosphere': 'biosphere',
        'climate indicators': 'climate_indicators',
        'cryosphere': 'cryosphere',
        'human dimensions': 'human_dimensions',
        'land surface': 'land_surface',
        'oceans': 'oceans',
        'paleoclimate': 'paleoclimate',
        'solid earth': 'solid_earth',
        'spectral/engineering': 'spectral_engineering',
        'sun-earth interactions': 'sun_earth_interactions',
        'terrestrial hydrosphere': 'terrestrial_hydrosphere',
        'marine science': 'marine_science',
        'terrestrial science': 'terrestrial_science',
        'wind profiler radar': 'wind_profiler_radar',
        'geotectonic studies': 'geotectonic_studies',
        'audio signals': 'audio_signals',
    }
    return mapping.get(cat, 'atmosphere')


def map_iso_topic(iso_topic):
    """Map legacy ISO topic to Django ISO topic choice."""
    if not iso_topic:
        return 'environment'
    iso = iso_topic.strip()
    # Try exact match first
    valid_values = [
        'climatologyMeteorologyAtmosphere', 'oceans', 'environment',
        'geoscientificInformation', 'imageryBaseMapsEarthCover',
        'inlandWaters', 'location', 'boundaries', 'biota',
        'economy', 'elevation', 'farming', 'health',
        'intelligenceMilitary', 'society', 'structure',
        'transportation', 'utilitiesCommunication',
    ]
    if iso in valid_values:
        return iso
    # Case-insensitive match
    iso_lower = iso.lower()
    for v in valid_values:
        if v.lower() == iso_lower:
            return v
    # Partial match
    keyword_map = {
        'climate': 'climatologyMeteorologyAtmosphere',
        'meteor': 'climatologyMeteorologyAtmosphere',
        'atmosphere': 'climatologyMeteorologyAtmosphere',
        'ocean': 'oceans',
        'biota': 'biota',
        'geo': 'geoscientificInformation',
        'water': 'inlandWaters',
        'elevation': 'elevation',
        'farm': 'farming',
        'image': 'imageryBaseMapsEarthCover',
    }
    for key, val in keyword_map.items():
        if key in iso_lower:
            return val
    return 'environment'


class Command(BaseCommand):
    help = 'Import data from legacy PostgreSQL tables into Django ORM models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate import without saving to DB',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of records to import (0 = all)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        self.stdout.write(self.style.NOTICE('Starting legacy data import...'))

        # Get or create a system user for submitter
        system_user, created = User.objects.get_or_create(
            username='legacy_import',
            defaults={
                'first_name': 'Legacy',
                'last_name': 'Import',
                'email': 'legacy@npdc.gov.in',
                'is_active': True,
            }
        )
        if created:
            system_user.set_unusable_password()
            system_user.save()
            self.stdout.write(f'  Created system user: {system_user.username}')

        # Fetch legacy data with JOINs
        query = """
            SELECT
                m.id,
                m.metadata_id,
                m.metadata_title,
                m.metadata_name,
                m.quality,
                m.access_constraints,
                m.use_constraints,
                m.distribution_media,
                m.distribution_size,
                m.distribution_format,
                m.distribution_fees,
                m.data_set_language,
                m.related_url_content_type,
                m.related_url,
                m.related_url_description,
                m.dif_revision_history,
                m.originating_center,
                m.multimedia_sample_url,
                m.multimedia_sample_format,
                m.parent_dif,
                m.internal_directory_name,
                m.dif_creation_date,
                m.last_dif_revision_date,
                m.future_dif_review_date,
                m.privacy_status,
                m.sci_key_category,
                m.sci_key_topic,
                m.expedition_year,
                m.iso_topic,
                m.summary_abstract,
                m.summary_purpose,
                m.instrument_short_name,
                m.instrument_long_name,
                m.platform_short_name,
                m.platform_long_name,
                m.location_category,
                m.location_type,
                m.location_subregion1,
                m.project_short_name,
                m.project_long_name,
                m.metadata_version,
                m.metadata_ts,
                m.data_set_progress,
                m.expedition_no,
                -- Scientist data
                s.sci_role,
                s.sci_title,
                s.sci_name,
                s.sci_middle_name,
                s.sci_last_name,
                s.sci_email,
                s.sci_phone,
                s.sci_mobile_number,
                s.sci_institute,
                s.sci_address1,
                s.sci_address2,
                s.sci_city,
                s.sci_state,
                s.sci_postal_code,
                s.sci_country,
                s.sci_fax,
                -- GPS data
                g.temporal_coverages_start_date,
                g.temporal_coverage_end_date,
                g.southernmost_latitude_deg,
                g.southernmost_latitude_min,
                g.southernmost_latitude_sec,
                g.northernmost_latitude_deg,
                g.northernmost_latitude_min,
                g.northernmost_latitude_sec,
                g.westernmost_longitude_deg,
                g.westernmost_longitude_min,
                g.westernmost_longitude_sec,
                g.easternmost_longitude_deg,
                g.easternmost_longitude_min,
                g.easternmost_longitude_sec,
                g.g_southernmost_latitude_deg, g.g_southernmost_latitude_min, g.g_southernmost_latitude_sec,
                g.g_northernmost_latitude_deg, g.g_northernmost_latitude_min, g.g_northernmost_latitude_sec,
                g.g_westernmost_longitude_deg, g.g_westernmost_longitude_min, g.g_westernmost_longitude_sec,
                g.g_easternmost_longitude_deg, g.g_easternmost_longitude_min, g.g_easternmost_longitude_sec,
                g.p_southernmost_latitude_deg, g.p_southernmost_latitude_min, g.p_southernmost_latitude_sec,
                g.p_northernmost_latitude_deg, g.p_northernmost_latitude_min, g.p_northernmost_latitude_sec,
                g.p_westernmost_longitude_deg, g.p_westernmost_longitude_min, g.p_westernmost_longitude_sec,
                g.p_easternmost_longitude_deg, g.p_easternmost_longitude_min, g.p_easternmost_longitude_sec,
                g.minimum_altitude,
                g.maximum_altitude,
                g.minimum_depth,
                g.maximum_depth,
                g.paleo_start_date,
                g.paleo_stop_date,
                g.chronostratigraphic_unit,
                -- Citation
                c.dsc_presentation_form,
                c.dsc_creator,
                c.dsc_editor,
                c.dsc_title,
                c.dsc_series_name,
                c.dsc_release_date,
                c.dsc_release_place,
                c.dsc_version,
                c.dsc_online_resource,
                -- Resolution
                r.latitude_resolution_deg,
                r.latitude_resolution_min,
                r.latitude_resolution_sec,
                r.longitude_resolution_deg,
                r.longitude_resolution_min,
                r.longitude_resolution_sec,
                r.horizontal_resolution_range,
                r.vertical_resolution,
                r.vertical_resolution_range,
                r.temporal_resolution,
                r.temporal_resolution_range
            FROM metadata_main_table m
            LEFT JOIN scientist_details s ON m.sci_id = s.sci_id
            LEFT JOIN gps_data_collection g ON m.gps_data_collection_id = g.gps_data_collection_id
            LEFT JOIN data_set_citation c ON m.dsc_id = c.dsc_id
            LEFT JOIN data_resolution r ON m.data_resolution_id = r.data_resolution_id
            WHERE m.metadata_title IS NOT NULL AND m.metadata_title != ''
            ORDER BY m.id
        """
        if limit > 0:
            query += f' LIMIT {limit}'

        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

        self.stdout.write(f'  Found {len(rows)} legacy records with titles')

        imported = 0
        skipped = 0
        errors = 0

        for row_data in rows:
            row = dict(zip(columns, row_data))
            try:
                metadata_id = safe_str(row['metadata_id'])

                # If dataset exists, delete it so we can re-import the full row
                DatasetSubmission.objects.filter(metadata_id=metadata_id).delete()


                title = safe_str(row['metadata_title'], 220, 'Untitled Dataset')
                abstract = safe_str(row['summary_abstract'], 1000, 'No abstract available.')
                purpose = safe_str(row['summary_purpose'], 1000, 'Not specified.')
                version = safe_str(row['metadata_version'], 50, '1.0')
                expedition_type = map_expedition_type(row['location_type'])
                expedition_year = safe_str(row['expedition_year'], 9, '')
                category = map_category(row['sci_key_category'])
                iso_topic = map_iso_topic(row['iso_topic'])
                topic = safe_str(row['sci_key_topic'], 200, category)
                project_number = safe_str(row['project_short_name'], 100, 'N/A')
                project_name = safe_str(row['project_long_name'], 300, title[:300])
                expedition_number = safe_str(row.get('expedition_no'), 100, '')

                # Build keywords from topic, category, location
                keywords_parts = []
                if row['sci_key_topic']:
                    keywords_parts.append(safe_str(row['sci_key_topic']))
                if row['sci_key_category']:
                    keywords_parts.append(safe_str(row['sci_key_category']))
                if row['location_type']:
                    keywords_parts.append(safe_str(row['location_type']))
                if row['location_subregion1']:
                    keywords_parts.append(safe_str(row['location_subregion1']))
                keywords_parts.append(f'legacy_id:{metadata_id}')
                keywords = ', '.join(keywords_parts)[:1000]

                # Data progress
                progress = safe_str(row.get('data_set_progress'), 20, 'complete').lower()
                if progress not in ('planned', 'in_work', 'complete'):
                    progress = 'complete'

                # Parse temporal dates
                start_date = parse_date(row['temporal_coverages_start_date'])
                end_date = parse_date(row['temporal_coverage_end_date'])

                # If no dates, try to derive from expedition_year
                if not start_date and expedition_year:
                    year_match = re.match(r'(\d{4})', expedition_year)
                    if year_match:
                        y = int(year_match.group(1))
                        start_date = datetime.date(y, 1, 1)
                        end_date = datetime.date(y, 12, 31)

                # Fallback dates
                if not start_date:
                    start_date = datetime.date(2000, 1, 1)
                if not end_date:
                    end_date = start_date + datetime.timedelta(days=365)
                if end_date < start_date:
                    end_date = start_date + datetime.timedelta(days=365)

                # Validate expedition_year format
                if not re.match(r'^\d{4}-\d{4}$', expedition_year):
                    if expedition_year:
                        year_match = re.match(r'(\d{4})', expedition_year)
                        if year_match:
                            y = int(year_match.group(1))
                            expedition_year = f'{y}-{y+1}'
                        else:
                            expedition_year = f'{start_date.year}-{start_date.year+1}'
                    else:
                        expedition_year = f'{start_date.year}-{start_date.year+1}'

                # Parse spatial coordinates (DMS to decimal)
                south_lat = dms_to_decimal(
                    row['southernmost_latitude_deg'],
                    row['southernmost_latitude_min'],
                    row['southernmost_latitude_sec']
                )
                north_lat = dms_to_decimal(
                    row['northernmost_latitude_deg'],
                    row['northernmost_latitude_min'],
                    row['northernmost_latitude_sec']
                )
                west_lon = dms_to_decimal(
                    row['westernmost_longitude_deg'],
                    row['westernmost_longitude_min'],
                    row['westernmost_longitude_sec']
                )
                east_lon = dms_to_decimal(
                    row['easternmost_longitude_deg'],
                    row['easternmost_longitude_min'],
                    row['easternmost_longitude_sec']
                )

                # Default coordinates based on expedition type if no GPS
                default_coords = {
                    'antarctic': (-75.0, -60.0, -180.0, 180.0),
                    'arctic': (66.0, 90.0, -180.0, 180.0),
                    'southern_ocean': (-60.0, -40.0, -180.0, 180.0),
                    'himalaya': (25.0, 35.0, 72.0, 92.0),
                }

                if south_lat is None:
                    defaults = default_coords.get(expedition_type, (-90, 90, -180, 180))
                    south_lat, north_lat, west_lon, east_lon = defaults

                # Clamp values
                south_lat = max(-90, min(90, south_lat or 0))
                north_lat = max(-90, min(90, north_lat or 0))
                west_lon = max(-180, min(180, west_lon or 0))
                east_lon = max(-180, min(180, east_lon or 0))
                if south_lat > north_lat:
                    south_lat, north_lat = north_lat, south_lat
                if west_lon > east_lon:
                    west_lon, east_lon = east_lon, west_lon

                # Scientist contact info
                contact_name = ' '.join(filter(None, [
                    safe_str(row.get('sci_name')),
                    safe_str(row.get('sci_last_name')),
                ])).strip() or 'Unknown'
                # Remove non-letter chars for the validator
                contact_name = re.sub(r'[^A-Za-z\s.\-]', '', contact_name) or 'Unknown'
                contact_email = safe_str(row.get('sci_email'), default='legacy@npdc.gov.in')
                if '@' not in contact_email:
                    contact_email = 'legacy@npdc.gov.in'
                contact_phone = safe_str(row.get('sci_phone'), 20, '')
                contact_phone = re.sub(r'[^0-9+\-\s()]', '', contact_phone)[:20]

                if dry_run:
                    self.stdout.write(f'  [DRY RUN] Would import: {title[:60]}...')
                    imported += 1
                    continue

                # Create DatasetSubmission
                dataset = DatasetSubmission(
                    metadata_id=metadata_id,
                    title=title,
                    abstract=abstract,
                    purpose=purpose,
                    version=version or '1.0',
                    keywords=keywords,
                    topic=topic,
                    data_center='National Polar Data Center',
                    expedition_type=expedition_type,
                    expedition_year=expedition_year,
                    expedition_number=expedition_number,
                    project_number=project_number,
                    project_name=project_name,
                    category=category,
                    iso_topic=iso_topic,
                    data_set_progress=progress,
                    temporal_start_date=start_date,
                    temporal_end_date=end_date,
                    west_longitude=west_lon,
                    east_longitude=east_lon,
                    south_latitude=south_lat,
                    north_latitude=north_lat,
                    contact_person=contact_name[:200],
                    contact_email=contact_email,
                    contact_phone=contact_phone,
                    submitter=system_user,
                    metadata_name=safe_str(row.get('metadata_name'), 500),
                    quality=safe_str(row.get('quality')),
                    access_constraints=safe_str(row.get('access_constraints')),
                    use_constraints=safe_str(row.get('use_constraints')),
                    distribution_media=safe_str(row.get('distribution_media'), 200),
                    distribution_size=safe_str(row.get('distribution_size'), 100),
                    distribution_format=safe_str(row.get('distribution_format'), 100),
                    distribution_fees=safe_str(row.get('distribution_fees'), 100),
                    data_set_language=safe_str(row.get('data_set_language'), 100),
                    related_url_content_type=safe_str(row.get('related_url_content_type'), 200),
                    related_url=safe_str(row.get('related_url'), 1000),
                    related_url_description=safe_str(row.get('related_url_description')),
                    dif_revision_history=safe_str(row.get('dif_revision_history')),
                    originating_center=safe_str(row.get('originating_center'), 200),
                    multimedia_sample_url=safe_str(row.get('multimedia_sample_url'), 1000),
                    multimedia_sample_format=safe_str(row.get('multimedia_sample_format'), 100),
                    parent_dif=safe_str(row.get('parent_dif'), 200),
                    internal_directory_name=safe_str(row.get('internal_directory_name'), 500),
                    dif_creation_date=safe_str(row.get('dif_creation_date'), 100),
                    last_dif_revision_date=safe_str(row.get('last_dif_revision_date'), 100),
                    future_dif_review_date=safe_str(row.get('future_dif_review_date'), 100),
                    privacy_status=safe_str(row.get('privacy_status'), 100),
                    status='published',
                )
                dataset.save()
                
                # Apply legacy submission date directly overriding auto_now_add
                if row.get('metadata_ts'):
                    DatasetSubmission.objects.filter(pk=dataset.pk).update(submission_date=row['metadata_ts'])

                # Create related: ScientistDetail
                if row.get('sci_name') or row.get('sci_last_name'):
                    first_name = safe_str(row.get('sci_name'), 50, 'Unknown')
                    first_name = re.sub(r'[^A-Za-z\s.\-]', '', first_name) or 'Unknown'
                    middle_name = safe_str(row.get('sci_middle_name'), 50, '')
                    middle_name = re.sub(r'[^A-Za-z\s.\-]', '', middle_name)
                    last_name = safe_str(row.get('sci_last_name'), 50, 'Unknown')
                    last_name = re.sub(r'[^A-Za-z\s.\-]', '', last_name) or 'Unknown'
                    role = safe_str(row.get('sci_role'), 100, 'Investigator')
                    role = re.sub(r'[^A-Za-z\s.\-]', '', role) or 'Investigator'
                    sci_title = safe_str(row.get('sci_title'), 10, 'Dr')
                    sci_title = re.sub(r'[^A-Za-z\s.\-]', '', sci_title) or 'Dr'
                    sci_email = contact_email
                    sci_phone = contact_phone or '0000000000'
                    sci_phone = re.sub(r'[^0-9+\-\s()]', '', sci_phone)[:20] or '0000000000'
                    sci_mobile = safe_str(row.get('sci_mobile_number'), 15, '0000000000')
                    sci_mobile = re.sub(r'[^0-9]', '', sci_mobile)[:15] or '0000000000'

                    try:
                        ScientistDetail.objects.create(
                            dataset=dataset,
                            role=role,
                            title=sci_title[:10],
                            first_name=first_name,
                            middle_name=middle_name,
                            last_name=last_name,
                            email=sci_email,
                            phone=sci_phone,
                            mobile=sci_mobile,
                            institute=safe_str(row.get('sci_institute'), 200, 'Not specified'),
                            address=safe_str(row.get('sci_address1'), 200, 'Not specified'),
                            address2=safe_str(row.get('sci_address2'), 200),
                            city=safe_str(row.get('sci_city'), 50, 'Not specified'),
                            country=None,  # Leave empty as django country code 'IN' was hardcoded, keep legacy in below
                            country_raw=safe_str(row.get('sci_country'), 100),
                            state=safe_str(row.get('sci_state'), 100, 'Not specified'),
                            fax=safe_str(row.get('sci_fax'), 50),
                            postal_code=re.sub(r'[^0-9]', '', safe_str(row.get('sci_postal_code'), 10, '000000'))[:10] or '000000',
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  Scientist error for {metadata_id}: {e}'))

                # Create related: InstrumentMetadata
                if row.get('instrument_short_name'):
                    try:
                        InstrumentMetadata.objects.create(
                            dataset=dataset,
                            short_name=safe_str(row['instrument_short_name'], 100, 'N/A'),
                            long_name=safe_str(row['instrument_long_name'], 200, ''),
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  Instrument error for {metadata_id}: {e}'))

                # Create related: PlatformMetadata
                if row.get('platform_short_name'):
                    try:
                        PlatformMetadata.objects.create(
                            dataset=dataset,
                            short_name=safe_str(row['platform_short_name'], 100, 'N/A'),
                            long_name=safe_str(row['platform_long_name'], 200, ''),
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  Platform error for {metadata_id}: {e}'))

                # Create related: GPSMetadata
                has_gps = any([
                    row.get('minimum_altitude'),
                    row.get('maximum_altitude'),
                    row.get('minimum_depth'),
                    row.get('maximum_depth'),
                ])
                try:
                    GPSMetadata.objects.create(
                        dataset=dataset,
                        gps_used=has_gps,
                        minimum_altitude=safe_str(row.get('minimum_altitude'), 50, ''),
                        maximum_altitude=safe_str(row.get('maximum_altitude'), 50, ''),
                        minimum_depth=safe_str(row.get('minimum_depth'), 50, ''),
                        maximum_depth=safe_str(row.get('maximum_depth'), 50, ''),
                        g_southernmost_latitude_deg=safe_str(row.get('g_southernmost_latitude_deg'), 50),
                        g_southernmost_latitude_min=safe_str(row.get('g_southernmost_latitude_min'), 50),
                        g_southernmost_latitude_sec=safe_str(row.get('g_southernmost_latitude_sec'), 50),
                        g_northernmost_latitude_deg=safe_str(row.get('g_northernmost_latitude_deg'), 50),
                        g_northernmost_latitude_min=safe_str(row.get('g_northernmost_latitude_min'), 50),
                        g_northernmost_latitude_sec=safe_str(row.get('g_northernmost_latitude_sec'), 50),
                        g_westernmost_longitude_deg=safe_str(row.get('g_westernmost_longitude_deg'), 50),
                        g_westernmost_longitude_min=safe_str(row.get('g_westernmost_longitude_min'), 50),
                        g_westernmost_longitude_sec=safe_str(row.get('g_westernmost_longitude_sec'), 50),
                        g_easternmost_longitude_deg=safe_str(row.get('g_easternmost_longitude_deg'), 50),
                        g_easternmost_longitude_min=safe_str(row.get('g_easternmost_longitude_min'), 50),
                        g_easternmost_longitude_sec=safe_str(row.get('g_easternmost_longitude_sec'), 50),
                        p_southernmost_latitude_deg=safe_str(row.get('p_southernmost_latitude_deg'), 50),
                        p_southernmost_latitude_min=safe_str(row.get('p_southernmost_latitude_min'), 50),
                        p_southernmost_latitude_sec=safe_str(row.get('p_southernmost_latitude_sec'), 50),
                        p_northernmost_latitude_deg=safe_str(row.get('p_northernmost_latitude_deg'), 50),
                        p_northernmost_latitude_min=safe_str(row.get('p_northernmost_latitude_min'), 50),
                        p_northernmost_latitude_sec=safe_str(row.get('p_northernmost_latitude_sec'), 50),
                        p_westernmost_longitude_deg=safe_str(row.get('p_westernmost_longitude_deg'), 50),
                        p_westernmost_longitude_min=safe_str(row.get('p_westernmost_longitude_min'), 50),
                        p_westernmost_longitude_sec=safe_str(row.get('p_westernmost_longitude_sec'), 50),
                        p_easternmost_longitude_deg=safe_str(row.get('p_easternmost_longitude_deg'), 50),
                        p_easternmost_longitude_min=safe_str(row.get('p_easternmost_longitude_min'), 50),
                        p_easternmost_longitude_sec=safe_str(row.get('p_easternmost_longitude_sec'), 50),
                    )
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  GPS error for {metadata_id}: {e}'))

                # Create related: LocationMetadata
                loc_cat = safe_str(row.get('location_category'), 20, '').lower()
                if loc_cat not in ('region', 'ocean'):
                    loc_cat = 'region' if expedition_type != 'southern_ocean' else 'ocean'
                try:
                    LocationMetadata.objects.create(
                        dataset=dataset,
                        location_category=loc_cat,
                        location_type=safe_str(row.get('location_type'), 50, expedition_type.title()),
                        location_subregion=safe_str(row.get('location_subregion1'), 100, ''),
                    )
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Location error for {metadata_id}: {e}'))

                # Create related: DataResolutionMetadata
                try:
                    DataResolutionMetadata.objects.create(
                        dataset=dataset,
                        latitude_resolution=safe_str(row.get('latitude_resolution_deg'), 50, ''),
                        latitude_resolution_min=safe_str(row.get('latitude_resolution_min'), 50, ''),
                        latitude_resolution_sec=safe_str(row.get('latitude_resolution_sec'), 50, ''),
                        longitude_resolution=safe_str(row.get('longitude_resolution_deg'), 50, ''),
                        longitude_resolution_min=safe_str(row.get('longitude_resolution_min'), 50, ''),
                        longitude_resolution_sec=safe_str(row.get('longitude_resolution_sec'), 50, ''),
                        horizontal_resolution_range=safe_str(row.get('horizontal_resolution_range'), 50, ''),
                        vertical_resolution=safe_str(row.get('vertical_resolution'), 50, ''),
                        vertical_resolution_range=safe_str(row.get('vertical_resolution_range'), 50, ''),
                        temporal_resolution=safe_str(row.get('temporal_resolution'), 50, ''),
                        temporal_resolution_range=safe_str(row.get('temporal_resolution_range'), 50, ''),
                    )
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  Resolution error for {metadata_id}: {e}'))

                # Create related: PaleoTemporalCoverage
                if row.get('paleo_start_date') or row.get('paleo_stop_date'):
                    try:
                        PaleoTemporalCoverage.objects.create(
                            dataset=dataset,
                            paleo_start_date=safe_str(row.get('paleo_start_date'), 50, ''),
                            paleo_stop_date=safe_str(row.get('paleo_stop_date'), 50, ''),
                            chronostratigraphic_unit=safe_str(row.get('chronostratigraphic_unit'), 100, ''),
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  Paleo error for {metadata_id}: {e}'))

                # Create related: DatasetCitation
                if row.get('dsc_creator') or row.get('dsc_title'):
                    creator = safe_str(row.get('dsc_creator'), 100, 'Unknown')
                    creator = re.sub(r'[^A-Za-z\s.\-]', '', creator) or 'Unknown'
                    editor = safe_str(row.get('dsc_editor'), 100, '')
                    editor = re.sub(r'[^A-Za-z\s.\-]', '', editor) or 'Unknown'
                    release_date = parse_date(row.get('dsc_release_date'), start_date)
                    try:
                        DatasetCitation.objects.create(
                            dataset=dataset,
                            creator=creator,
                            editor=editor,
                            title=safe_str(row.get('dsc_title'), 200, title[:200]),
                            series_name=safe_str(row.get('dsc_series_name'), 200, ''),
                            release_date=release_date,
                            release_place=safe_str(row.get('dsc_release_place'), 100, ''),
                            version=safe_str(row.get('dsc_version'), 50, '1.0'),
                            online_resource=safe_str(row.get('dsc_online_resource'), 200, ''),
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  Citation error for {metadata_id}: {e}'))

                imported += 1
                if imported % 50 == 0:
                    self.stdout.write(f'  Imported {imported}/{len(rows)}...')

            except Exception as e:
                errors += 1
                self.stdout.write(self.style.ERROR(
                    f'  ERROR importing {row.get("metadata_id", "?")}: {e}'
                ))


        # --- IMPORT LEGACY TABLES ---

        self.stdout.write(self.style.NOTICE('Importing legacy user accounts...'))
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT * FROM user_login")
                user_cols = [c[0] for c in cur.description]
                user_rows = cur.fetchall()
                
            new_users = 0
            for u in user_rows:
                ud = dict(zip(user_cols, u))
                legacy_user, created = LegacyUser.objects.get_or_create(
                    user_id=safe_str(ud.get('user_id'), 200),
                    defaults={
                        'user_name': safe_str(ud.get('user_name'), 200),
                        'user_password': safe_str(ud.get('user_password'), 200),
                        'user_role': safe_str(ud.get('user_role'), 50),
                        'account_status': safe_str(ud.get('account_status'), 50),
                        'created_by': safe_str(ud.get('created_by'), 200),
                        'created_ts': safe_str(ud.get('created_ts'), 100),
                        'updated_by': safe_str(ud.get('updated_by'), 200),
                        'updated_ts': safe_str(ud.get('updated_ts'), 100),
                        'data_access_id': safe_str(ud.get('data_access_id'), 200),
                        'designation': safe_str(ud.get('designation'), 200),
                        'organisation': safe_str(ud.get('organisation'), 200),
                        'address': safe_str(ud.get('address')),
                        'e_mail': safe_str(ud.get('e_mail'), 200),
                        'phone_number': safe_str(ud.get('phone_number'), 100),
                        'emailvarified': safe_str(ud.get('emailvarified'), 50),
                        'emailtoken': safe_str(ud.get('emailtoken'), 500),
                        'url': safe_str(ud.get('url'), 200),
                        'ppurl': safe_str(ud.get('ppurl'), 200),
                        'title': safe_str(ud.get('title'), 100),
                        'known_as': safe_str(ud.get('known_as'), 200),
                        'alt_mobile_no': safe_str(ud.get('alt_mobile_no'), 100),
                    }
                )
                if created: new_users += 1
            self.stdout.write(f'  Imported {new_users} legacy users')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Failed importing legacy users: {e}'))

        self.stdout.write(self.style.NOTICE('Importing DataCenter records...'))
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT m.metadata_title, d.* FROM data_center d JOIN metadata_main_table m ON d.dc_id = m.dc_id")
                dc_cols = [c[0] for c in cur.description]
                dc_rows = cur.fetchall()
            dc_count = 0
            for row in dc_rows:
                d = dict(zip(dc_cols, row))
                datasets = DatasetSubmission.objects.filter(title__iexact=d.get('metadata_title'))
                for ds in datasets:
                    DataCenter.objects.get_or_create(
                        dataset=ds,
                        defaults={
                            'dc_short_name': safe_str(d.get('dc_short_name'), 200),
                            'dc_long_name': safe_str(d.get('dc_long_name'), 500),
                            'dc_url': safe_str(d.get('dc_url'), 1000),
                            'dc_address1': safe_str(d.get('dc_address1')),
                            'dc_address2': safe_str(d.get('dc_address2')),
                            'dc_city': safe_str(d.get('dc_city'), 200),
                            'dc_state': safe_str(d.get('dc_state'), 200),
                            'dc_postal_code': safe_str(d.get('dc_postal_code'), 100),
                            'dc_country': safe_str(d.get('dc_country'), 200),
                            'dc_email': safe_str(d.get('dc_email'), 200),
                            'dc_phone': safe_str(d.get('dc_phone'), 100),
                            'dc_fax': safe_str(d.get('dc_fax'), 100),
                        }
                    )
                    dc_count += 1
            self.stdout.write(f'  Imported {dc_count} datacenter links')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'No data_center logic matched: {e}'))

        self.stdout.write(self.style.NOTICE('Importing Reference records...'))
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT m.metadata_title, r.* FROM references1 r JOIN metadata_main_table m ON r.ref_id = m.ref_id")
                ref_cols = [c[0] for c in cur.description]
                ref_rows = cur.fetchall()
            ref_count = 0
            for row in ref_rows:
                r = dict(zip(ref_cols, row))
                datasets = DatasetSubmission.objects.filter(title__iexact=r.get('metadata_title'))
                for ds in datasets:
                    Reference.objects.get_or_create(
                        dataset=ds,
                        defaults={
                            'ref_author': safe_str(r.get('ref_author')),
                            'ref_publication_date': safe_str(r.get('ref_publication_date'), 100),
                            'ref_title': safe_str(r.get('ref_title')),
                            'ref_series': safe_str(r.get('ref_series')),
                            'ref_report_number': safe_str(r.get('ref_report_number'), 200),
                            'ref_publication_place': safe_str(r.get('ref_publication_place'), 200),
                            'ref_publisher': safe_str(r.get('ref_publisher'), 200),
                            'ref_online_resource': safe_str(r.get('ref_online_resource')),
                        }
                    )
                    ref_count += 1
            self.stdout.write(f'  Imported {ref_count} references')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Reference logic err: {e}'))

        self.stdout.write(self.style.NOTICE('Importing NPDC Master records...'))
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT * FROM npdc_master")
                master_cols = [c[0] for c in cur.description]
                master_rows = cur.fetchall()
            master_count = 0
            for row in master_rows:
                m = dict(zip(master_cols, row))
                # npdc_master has `metadata_id`! This is a direct link.
                metadata_id = safe_str(m.get('metadata_id'))
                datasets = DatasetSubmission.objects.filter(metadata_id=metadata_id)
                for ds in datasets:
                    NPDCMaster.objects.get_or_create(
                        dataset=ds,
                        defaults={
                            'master_id': m.get('master_id'),
                            'fileinfo_id': safe_str(m.get('fileinfo_id'), 200),
                            'data_status': safe_str(m.get('data_status'), 100),
                            'data_ref_id': safe_str(m.get('data_ref_id'), 200),
                            'created_by': safe_str(m.get('created_by'), 200),
                            'updated_by': safe_str(m.get('updated_by'), 200),
                            'metadata_status': safe_str(m.get('metadata_status'), 100),
                        }
                    )
                    master_count += 1
            self.stdout.write(f'  Imported {master_count} NPDC Master records')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'NPDC Master logic err: {e}'))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Import complete!'))
        self.stdout.write(f'  Imported: {imported}')
        self.stdout.write(f'  Skipped (duplicates): {skipped}')
        self.stdout.write(f'  Errors: {errors}')
        self.stdout.write(f'  Total legacy records: {len(rows)}')
