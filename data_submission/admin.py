from django.contrib import admin
from .models import (
    DatasetSubmission,
    DatasetCitation,
    ScientistDetail,
    InstrumentMetadata,
    PlatformMetadata,
    GPSMetadata,
    LocationMetadata,
    DataResolutionMetadata,
    State,
)

# ==============================
# INLINE ADMINS
# ==============================

class DatasetCitationInline(admin.StackedInline):
    model = DatasetCitation
    extra = 0


class ScientistDetailInline(admin.StackedInline):
    model = ScientistDetail
    extra = 0


class InstrumentMetadataInline(admin.StackedInline):
    model = InstrumentMetadata
    extra = 0


class PlatformMetadataInline(admin.StackedInline):
    model = PlatformMetadata
    extra = 0


class GPSMetadataInline(admin.StackedInline):
    model = GPSMetadata
    extra = 0


class LocationMetadataInline(admin.StackedInline):
    model = LocationMetadata
    extra = 0


class DataResolutionMetadataInline(admin.StackedInline):
    model = DataResolutionMetadata
    extra = 0


# ==============================
# MAIN DATASET ADMIN
# ==============================

@admin.register(DatasetSubmission)
class DatasetSubmissionAdmin(admin.ModelAdmin):

    list_display = (
        'title',
        'version',
        'submitter',
        'status',
        'submission_date',
    )

    list_filter = (
        'status',
        'submission_date',
        'expedition_type',
        'category',
        'iso_topic',
    )

    search_fields = (
        'title',
        'project_name',
        'keywords',
        'submitter__username',
    )

    readonly_fields = (
        'submitter',
        'submission_date',
        'last_updated',
        'file_size_mb',
    )

    inlines = [
        DatasetCitationInline,
        ScientistDetailInline,
        InstrumentMetadataInline,
        PlatformMetadataInline,
        GPSMetadataInline,
        LocationMetadataInline,
        DataResolutionMetadataInline,
    ]

    fieldsets = (
        ('Identification', {
            'fields': (
                'title',
                'version',
                'doi',
                'keywords',
                'data_center',
            )
        }),

        ('Project Information', {
            'fields': (
                'expedition_type',
                'expedition_year',
                'expedition_number',
                'project_number',
                'project_name',
                'category',
                'iso_topic',
            )
        }),

        ('Summary', {
            'fields': (
                'abstract',
                'purpose',
            )
        }),

        ('Temporal Coverage', {
            'fields': (
                'temporal_start_date',
                'temporal_end_date',
            )
        }),

        ('Spatial Coverage', {
            'fields': (
                'west_longitude',
                'east_longitude',
                'south_latitude',
                'north_latitude',
            )
        }),

        ('Files', {
            'fields': (
                'data_file',
                'metadata_file',
                'readme_file',
                'file_size_mb',
                'number_of_files',
            )
        }),

        ('Access & Contact', {
            'fields': (
                'contact_person',
                'contact_email',
                'contact_phone',
            )
        }),

        ('Workflow', {
            'fields': (
                'status',
                'reviewer_notes',
                'submitter',
                'submission_date',
                'last_updated',
            )
        }),
    )


# ==============================
# STATE ADMIN
# ==============================

@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ('name', 'country_code')
    list_filter = ('country_code',)
    search_fields = ('name', 'country_code')
    ordering = ('country_code', 'name')
