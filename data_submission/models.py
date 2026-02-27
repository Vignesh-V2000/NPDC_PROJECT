from django.db import models
from django.contrib.auth.models import User
from django_countries.fields import CountryField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField

from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    RegexValidator
)
import datetime


# Create custom validators for letters-only fields
letter_validator = RegexValidator(
    r'^[A-Za-z\s\.\-]+$',
    'Only letters, spaces, dots, and hyphens allowed.'
)

phone_validator = RegexValidator(
    r'^[0-9+\-\s\(\)]+$',
    'Enter valid phone number'
)

postal_code_validator = RegexValidator(
    r'^\d{4,10}$',
    'Enter valid postal code (4-10 digits)'
)


class DatasetSubmission(models.Model):
    # ===============================
    # CONTROLLED VOCABULARIES (MATCHING JSP EXACTLY)
    # ===============================

    EXPEDITION_TYPES = [
        ('antarctic', 'Antarctic'),
        ('arctic', 'Arctic'),
        ('southern_ocean', 'Southern Ocean'),
        ('himalaya', 'Himalaya'),
    ]

    # Generate expedition years from 1981-2036 as in JSP
    @classmethod
    def get_expedition_year_choices(cls):
        current_year = datetime.date.today().year
        choices = []
        for year in range(2036, 1980, -1):
            choices.append((f"{year}-{year+1}", f"{year}-{year+1}"))
        return choices

    # JSP Categories (complete list)
    CATEGORY_CHOICES = [
        ('agriculture', 'Agriculture'),
        ('atmosphere', 'Atmosphere'),
        ('biological_classification', 'Biological Classification'),
        ('biosphere', 'Biosphere'),
        ('climate_indicators', 'Climate Indicators'),
        ('cryosphere', 'Cryosphere'),
        ('human_dimensions', 'Human Dimensions'),
        ('land_surface', 'Land Surface'),
        ('oceans', 'Oceans'),
        ('paleoclimate', 'Paleoclimate'),
        ('solid_earth', 'Solid Earth'),
        ('spectral_engineering', 'Spectral/Engineering'),
        ('sun_earth_interactions', 'Sun-Earth Interactions'),
        ('terrestrial_hydrosphere', 'Terrestrial Hydrosphere'),
        ('marine_science', 'Marine Science'),
        ('terrestrial_science', 'Terrestrial Science'),
        ('wind_profiler_radar', 'Wind Profiler Radar'),
        ('geotectonic_studies', 'Geotectonic Studies'),
        ('audio_signals', 'Audio Signals'),
    ]

    # JSP ISO Topic Categories
    ISO_TOPIC_CHOICES = [
        ('climatologyMeteorologyAtmosphere', 'Climatology/Meteorology/Atmosphere'),
        ('oceans', 'Oceans'),
        ('environment', 'Environment'),
        ('geoscientificInformation', 'Geoscientific Information'),
        ('imageryBaseMapsEarthCover', 'Imagery/Base Maps/Earth Cover'),
        ('inlandWaters', 'Inland Waters'),
        ('location', 'Location'),
        ('boundaries', 'Boundaries'),
        ('biota', 'Biota'),
        ('economy', 'Economy'),
        ('elevation', 'Elevation'),
        ('farming', 'Farming'),
        ('health', 'Health'),
        ('intelligenceMilitary', 'Intelligence/Military'),
        ('society', 'Society'),
        ('structure', 'Structure'),
        ('transportation', 'Transportation'),
        ('utilitiesCommunication', 'Utilities/Communication'),
    ]

    DATA_PROGRESS_CHOICES = [
        ('planned', 'Planned'),
        ('in_work', 'In Work'),
        ('complete', 'Complete'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('published', 'Published'),
    ]



    # ===============================
    # IDENTIFICATION (EXACT JSP LIMITS)
    # ===============================

    title = models.CharField(max_length=220)  # JSP: maxSize[220]
    abstract = models.TextField(max_length=1000)  # JSP: maxSize[1000]
    purpose = models.TextField(max_length=1000)  # JSP: maxSize[1000]
    version = models.CharField(max_length=50, default="1.0")

    keywords = models.TextField(
        max_length=1000,
        help_text="Comma separated keywords (GCMD recommended)"
    )

    topic = models.CharField(max_length=200)

    data_center = models.CharField(
        max_length=200,
        default="National Polar Data Center"
    )

    # ===============================
    # PROJECT INFO
    # ===============================

    expedition_type = models.CharField(max_length=30, choices=EXPEDITION_TYPES)
    expedition_year = models.CharField(max_length=9)  # Will set choices dynamically
    expedition_number = models.CharField(max_length=100, blank=True)

    project_number = models.CharField(max_length=100)
    project_name = models.CharField(max_length=300)

    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    iso_topic = models.CharField(max_length=100, choices=ISO_TOPIC_CHOICES, verbose_name="ISO Topic")

    data_set_progress = models.CharField(
        max_length=20,
        choices=DATA_PROGRESS_CHOICES,
        verbose_name="Dataset Progress"
    )

    # ===============================
    # TEMPORAL COVERAGE
    # ===============================

    temporal_start_date = models.DateField()
    temporal_end_date = models.DateField()

    # ===============================
    # SPATIAL COVERAGE (Bounding Box)
    # ===============================

    west_longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    east_longitude = models.FloatField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    south_latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    north_latitude = models.FloatField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )

    # ===============================
    # FILES (NEW FEATURE, NOT IN JSP)
    # ===============================

    data_file = models.FileField(upload_to='datasets/', blank=True)  # New in Django
    metadata_file = models.FileField(upload_to='metadata/', blank=True)  # New in Django
    readme_file = models.FileField(upload_to='readme/', blank=True)  # New in Django

    file_size_mb = models.FloatField(default=0)  # New in Django
    number_of_files = models.IntegerField(default=1)  # New in Django


    # ===============================
    # CONTACT
    # ===============================

    contact_person = models.CharField(max_length=200, validators=[letter_validator])

    contact_email = models.EmailField()
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        validators=[phone_validator]
    )

    # ===============================
    # SYSTEM TRACKING
    # ===============================

    submitter = models.ForeignKey(User, on_delete=models.CASCADE)
    submission_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    reviewer_notes = models.TextField(blank=True)

    # 🚀 AUDIT TRAIL FIELDS
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_datasets"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    status_updated_at = models.DateTimeField(auto_now=True)

    # ===============================
    # WORKFLOW STATE MACHINE
    # ===============================

    STATUS_TRANSITIONS = {
        "draft": ["submitted"],
        "submitted": ["published"],
        "published": [],
    }

    def can_transition(self, new_status):
        """Check if status transition is valid"""
        return new_status in self.STATUS_TRANSITIONS.get(self.status, [])

    # ===============================
    # MODEL BEHAVIOR
    # ===============================

    def save(self, *args, **kwargs):
        if self.data_file:
            self.file_size_mb = round(self.data_file.size / (1024 * 1024), 2)
        
        # Set expedition year choices dynamically
        if not self.expedition_year:
            current_year = datetime.date.today().year
            self.expedition_year = f"{current_year}-{current_year+1}"
        
        super().save(*args, **kwargs)

    def clean(self):
        """Cross-field validation"""
        errors = {}
        
        # Temporal validation
        if self.temporal_start_date and self.temporal_end_date:
            if self.temporal_start_date > self.temporal_end_date:
                errors['temporal_end_date'] = 'End date must be after start date'
        
        # Longitude validation
        if self.west_longitude is not None and self.east_longitude is not None:
            if self.west_longitude > self.east_longitude:
                errors['east_longitude'] = 'East longitude must be greater than west longitude'
        
        # Latitude validation
        if self.south_latitude is not None and self.north_latitude is not None:
            if self.south_latitude > self.north_latitude:
                errors['north_latitude'] = 'North latitude must be greater than south latitude'
        
        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)

    @property
    def keyword_list(self):
        return [k.strip() for k in self.keywords.split(',') if k.strip()]

    class Meta:
        ordering = ['-submission_date']
        indexes = [
            # GIN index for PostgreSQL Full Text Search
            GinIndex(
                name='dataset_fts_gin_idx',
                fields=['title', 'abstract', 'keywords'],
                opclasses=['gin_trgm_ops', 'gin_trgm_ops', 'gin_trgm_ops']
            ),
            # B-tree indexes for filter fields
            models.Index(fields=['expedition_type'], name='dataset_expedition_idx'),
            models.Index(fields=['category'], name='dataset_category_idx'),
            models.Index(fields=['status'], name='dataset_status_idx'),
            models.Index(fields=['expedition_year'], name='dataset_year_idx'),
            models.Index(fields=['iso_topic'], name='dataset_iso_idx'),
            # Temporal coverage index (for date range queries)
            models.Index(fields=['temporal_start_date', 'temporal_end_date'], name='dataset_temporal_idx'),
            # Spatial index (for bounding box queries)
            models.Index(fields=['west_longitude', 'east_longitude', 'south_latitude', 'north_latitude'], name='dataset_spatial_idx'),
            # Submission date index
            models.Index(fields=['-submission_date'], name='dataset_submitted_idx'),
        ]

    @property
    def was_updated(self):
        """Check if the dataset has been updated after initial submission."""
        # Allow a small buffer (e.g., 60 seconds) for initial save discrepancies
        delta = self.last_updated - self.submission_date
        return delta.total_seconds() > 60

    @property
    def can_be_updated(self):
        return self.status in ['published', 'submitted', 'revision_requested']

    def __str__(self):
        return f"{self.title} ({self.version})"


# =====================================================
# RELATED MODELS
# =====================================================

class DatasetCitation(models.Model):
    dataset = models.OneToOneField(
        DatasetSubmission,
        on_delete=models.CASCADE,
        related_name='citation'
    )

    creator = models.CharField(max_length=100, validators=[letter_validator])
    editor = models.CharField(max_length=100, validators=[letter_validator])
    title = models.CharField(max_length=200)
    series_name = models.CharField(max_length=200)
    release_date = models.DateField()
    release_place = models.CharField(max_length=100)
    version = models.CharField(max_length=50, blank=True)
    online_resource = models.URLField(blank=True)

    class Meta:
        verbose_name = "Dataset Citation"
        verbose_name_plural = "Dataset Citations"


class ScientistDetail(models.Model):
    dataset = models.ForeignKey(
        DatasetSubmission,
        on_delete=models.CASCADE,
        related_name='scientists'
    )

    role = models.CharField(max_length=100, validators=[letter_validator])
    title = models.CharField(max_length=10, validators=[letter_validator])

    first_name = models.CharField(max_length=50, validators=[letter_validator])
    middle_name = models.CharField(max_length=50, blank=True, validators=[letter_validator])
    last_name = models.CharField(max_length=50, validators=[letter_validator])

    email = models.EmailField()  # JSP: auto-filled from logged user, read-only

    phone = models.CharField(
        max_length=20,
        validators=[phone_validator]
    )

    mobile = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^[0-9]+$', 'Enter valid mobile number')]
    )

    institute = models.TextField(max_length=200)
    address = models.TextField(max_length=200)
    city = models.CharField(max_length=50)

    country = CountryField(blank_label='Select Country')
    state = models.CharField(max_length=100)


    postal_code = models.CharField(
        max_length=10,
        validators=[postal_code_validator]
    )

    class Meta:
        verbose_name = "Scientist Detail"
        verbose_name_plural = "Scientist Details"


class InstrumentMetadata(models.Model):
    dataset = models.ForeignKey(
        DatasetSubmission,
        on_delete=models.CASCADE,
        related_name='instruments'
    )

    short_name = models.CharField(max_length=100)
    long_name = models.CharField(max_length=200)

    class Meta:
        verbose_name = "Instrument Metadata"
        verbose_name_plural = "Instrument Metadata"


class PlatformMetadata(models.Model):
    dataset = models.OneToOneField(
        DatasetSubmission,
        on_delete=models.CASCADE,
        related_name='platform'
    )

    short_name = models.CharField(max_length=100)
    long_name = models.CharField(max_length=200)

    class Meta:
        verbose_name = "Platform Metadata"
        verbose_name_plural = "Platform Metadata"


class GPSMetadata(models.Model):
    dataset = models.OneToOneField(
        DatasetSubmission,
        on_delete=models.CASCADE,
        related_name='gps'
    )

    gps_used = models.BooleanField(default=False, verbose_name="GPS Used")

    # JSP: If GPS = YES → these fields are required
    minimum_altitude = models.CharField(max_length=50, blank=True)
    maximum_altitude = models.CharField(max_length=50, blank=True)
    minimum_depth = models.CharField(max_length=50, blank=True)
    maximum_depth = models.CharField(max_length=50, blank=True)

    def clean(self):
        """GPS-specific validation matching JSP rules"""
        if self.gps_used:
            errors = {}
            # JSP required all spatial fields when GPS was used
            if not self.minimum_altitude and not self.minimum_depth:
                errors['minimum_altitude'] = 'Either altitude or depth is required when GPS is used'
            if errors:
                from django.core.exceptions import ValidationError
                raise ValidationError(errors)

    class Meta:
        verbose_name = "GPS Metadata"
        verbose_name_plural = "GPS Metadata"


class LocationMetadata(models.Model):
    LOCATION_CATEGORY_CHOICES = [
        ('region', 'Region'),
        ('ocean', 'Ocean'),
    ]

    dataset = models.OneToOneField(
        DatasetSubmission,
        on_delete=models.CASCADE,
        related_name='location'
    )

    location_category = models.CharField(
        max_length=20,
        choices=LOCATION_CATEGORY_CHOICES
    )

    location_type = models.CharField(max_length=50)
    location_subregion = models.CharField(max_length=100)
    other_subregion = models.CharField(max_length=100, blank=True)

    def clean(self):
        """Location-specific validation matching JSP rules"""
        errors = {}
        
        # JSP rule: If subregion == 'others' → other_subregion required
        if self.location_subregion == 'others' and not self.other_subregion:
            errors['other_subregion'] = 'Specify other subregion'
        
        # Auto-set category based on expedition type (if dataset exists)
        if self.dataset_id:
            dataset = DatasetSubmission.objects.get(id=self.dataset_id)
            
            expedition_map = {
                "antarctic": ("region", "Antarctica"),
                "arctic": ("region", "Arctic"),
                "southern_ocean": ("ocean", "Southern Ocean"),
                "himalaya": ("region", "Himalaya"),
            }
            
            if dataset.expedition_type in expedition_map:
                category, loc_type = expedition_map[dataset.expedition_type]
                self.location_category = category
                self.location_type = loc_type
        
        if errors:
            from django.core.exceptions import ValidationError
            raise ValidationError(errors)

    class Meta:
        verbose_name = "Location Metadata"
        verbose_name_plural = "Location Metadata"


class DataResolutionMetadata(models.Model):
    dataset = models.OneToOneField(
        DatasetSubmission,
        on_delete=models.CASCADE,
        related_name='resolution'
    )

    latitude_resolution = models.CharField(max_length=50, blank=True)
    longitude_resolution = models.CharField(max_length=50, blank=True)

    horizontal_resolution_range = models.CharField(max_length=50, blank=True)

    vertical_resolution = models.CharField(max_length=50, blank=True)
    vertical_resolution_range = models.CharField(max_length=50, blank=True)

    temporal_resolution = models.CharField(max_length=50, blank=True)
    temporal_resolution_range = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "Data Resolution Metadata"
        verbose_name_plural = "Data Resolution Metadata"


class PaleoTemporalCoverage(models.Model):
    dataset = models.OneToOneField(
        DatasetSubmission,
        on_delete=models.CASCADE,
        related_name='paleo_temporal'
    )

    paleo_start_date = models.CharField(max_length=50, blank=True)
    paleo_stop_date = models.CharField(max_length=50, blank=True)

    chronostratigraphic_unit = models.CharField(max_length=100, blank=True)

    def clean(self):
        """Paleo temporal validation"""
        if self.paleo_start_date and self.paleo_stop_date:
            # Add validation logic here if needed
            pass

    class Meta:
        verbose_name = "Paleo Temporal Coverage"
        verbose_name_plural = "Paleo Temporal Coverage"

    def __str__(self):
        return f"Paleo coverage for {self.dataset.title}"


class State(models.Model):
    """Model to store states/provinces linked to country codes"""
    country_code = models.CharField(max_length=2)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name