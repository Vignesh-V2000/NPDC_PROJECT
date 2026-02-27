from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator


class DatasetSubmission(models.Model):

    # =============================
    # EXPEDITION
    # =============================
    EXPEDITION_TYPES = [
        ('Antarctic', 'Antarctic'),
        ('Arctic', 'Arctic'),
        ('Ocean', 'Southern Ocean'),
        ('Himalaya', 'Himalaya'),
    ]

    expedition_type = models.CharField(max_length=20, choices=EXPEDITION_TYPES)
    expedition_year = models.CharField(max_length=9)
    expedition_number = models.CharField(max_length=50, blank=True)

    # =============================
    # BASIC METADATA
    # =============================
    title = models.CharField(max_length=220)

    category = models.CharField(max_length=50)
    topic = models.CharField(max_length=100)
    iso_topic = models.CharField(max_length=100)

    # =============================
    # PROJECT DETAILS
    # =============================
    project_number = models.CharField(max_length=50)
    project_name = models.CharField(max_length=200)

    # =============================
    # SUMMARY
    # =============================
    abstract = models.TextField(max_length=1000)
    purpose = models.TextField(max_length=1000)

    # =============================
    # DATASET CITATION
    # =============================
    citation_creator = models.CharField(max_length=100)
    citation_editor = models.CharField(max_length=100)
    citation_title = models.CharField(max_length=200)
    citation_series_name = models.CharField(max_length=200)
    citation_release_date = models.DateField()
    citation_release_place = models.CharField(max_length=100)
    citation_version = models.CharField(max_length=50, blank=True)
    citation_online_resource = models.URLField(blank=True)

    # =============================
    # SCIENTIST DETAILS
    # =============================
    scientist_title = models.CharField(max_length=10)
    scientist_first_name = models.CharField(max_length=50)
    scientist_middle_name = models.CharField(max_length=50, blank=True)
    scientist_last_name = models.CharField(max_length=50)
    scientist_role = models.CharField(max_length=100)

    scientist_email = models.EmailField()
    scientist_phone = models.CharField(max_length=20)
    scientist_mobile = models.CharField(max_length=15)

    scientist_institute = models.TextField(max_length=200)
    scientist_address = models.TextField(max_length=200)
    scientist_city = models.CharField(max_length=50)
    scientist_country = models.CharField(max_length=100)
    scientist_state = models.CharField(max_length=100)
    scientist_postal_code = models.CharField(max_length=10)

    # =============================
    # INSTRUMENT
    # =============================
    instrument_short_name = models.CharField(max_length=100)
    instrument_long_name = models.CharField(max_length=200)

    # =============================
    # GPS METADATA
    # =============================
    gps_used = models.BooleanField(default=False)

    temporal_start_date = models.DateField()
    temporal_end_date = models.DateField()

    paleo_start_date = models.CharField(max_length=50, blank=True)
    paleo_stop_date = models.CharField(max_length=50, blank=True)
    chronostratigraphic_unit = models.CharField(max_length=100, blank=True)

    # Bounding Box
    southern_lat_deg = models.IntegerField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        blank=True, null=True
    )
    northern_lat_deg = models.IntegerField(
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
        blank=True, null=True
    )
    western_lon_deg = models.IntegerField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        blank=True, null=True
    )
    eastern_lon_deg = models.IntegerField(
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        blank=True, null=True
    )

    minimum_altitude = models.CharField(max_length=50, blank=True)
    maximum_altitude = models.CharField(max_length=50, blank=True)
    minimum_depth = models.CharField(max_length=50, blank=True)
    maximum_depth = models.CharField(max_length=50, blank=True)

    # =============================
    # DATA SET PROGRESS
    # =============================
    PROGRESS_CHOICES = [
        ('Planned', 'Planned'),
        ('In Work', 'In Work'),
        ('Complete', 'Complete'),
    ]

    data_set_progress = models.CharField(max_length=20, choices=PROGRESS_CHOICES)

    # =============================
    # LOCATION
    # =============================
    location_type = models.CharField(max_length=50, editable=False)
    location_subregion = models.CharField(max_length=100)
    other_subregion = models.CharField(max_length=100, blank=True)

    # =============================
    # DATA RESOLUTION
    # =============================
    horizontal_resolution_range = models.CharField(max_length=50, blank=True)
    vertical_resolution = models.CharField(max_length=50, blank=True)
    temporal_resolution = models.CharField(max_length=50, blank=True)

    # =============================
    # PLATFORM
    # =============================
    platform_short_name = models.CharField(max_length=100)
    platform_long_name = models.CharField(max_length=200)

    # =============================
    # FILES
    # =============================
    data_file = models.FileField(upload_to='datasets/', blank=True)
    metadata_file = models.FileField(upload_to='metadata/', blank=True)
    readme_file = models.FileField(upload_to='readme/', blank=True)

    # =============================
    # ACCESS CONTROL
    # =============================
    access_type = models.CharField(
        max_length=20,
        choices=[
            ('open', 'Open Access'),
            ('restricted', 'Restricted Access'),
            ('embargoed', 'Embargoed')
        ],
        default='open'
    )

    embargo_date = models.DateField(null=True, blank=True)
    license = models.CharField(max_length=100, blank=True)
    usage_restrictions = models.TextField(blank=True)

    # =============================
    # CONTACT
    # =============================
    contact_person = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    # =============================
    # WORKFLOW
    # =============================
    submitter = models.ForeignKey(User, on_delete=models.CASCADE)

    submission_date = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('under_review', 'Under Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected')
        ],
        default='draft'
    )

    reviewer_notes = models.TextField(blank=True)

    # =============================
    # META CONFIG
    # =============================
    class Meta:
        ordering = ['-submission_date']

    def __str__(self):
        return f"{self.title} - {self.submitter.username}"

    def save(self, *args, **kwargs):
        if self.expedition_type == 'Ocean':
            self.location_type = 'Southern Ocean'
        else:
            self.location_type = self.expedition_type

        if self.data_file:
            self.file_size = self.data_file.size / (1024 * 1024)

        super().save(*args, **kwargs)
