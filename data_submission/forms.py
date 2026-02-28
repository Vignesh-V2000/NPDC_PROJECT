from django import forms
from django.core.exceptions import ValidationError

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Fieldset

from .models import (
    DatasetSubmission,
    DatasetCitation,
    ScientistDetail,
    InstrumentMetadata,
    PlatformMetadata,
    GPSMetadata,
    LocationMetadata,
    DataResolutionMetadata,
    PaleoTemporalCoverage,
)



# =====================================================
# MAIN DATASET FORM
# =====================================================

# =====================================================
# MAIN DATASET FORM
# =====================================================

# =====================================================
# MAIN DATASET FORM
# =====================================================

class DatasetSubmissionForm(forms.ModelForm):
    
    # Explicitly define fields to ensure correct widgets
    expedition_type = forms.ChoiceField(
        choices=DatasetSubmission.EXPEDITION_TYPES,
        widget=forms.RadioSelect,
        label='Expedition Type'
    )
    
    expedition_year = forms.ChoiceField(
        choices=DatasetSubmission.get_expedition_year_choices, # Django evaluates callable choices
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Expedition Year'
    )

    # Spatial Coverage Split Fields
    north_lat_deg = forms.CharField(label="North Lat Deg", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Deg'}))
    north_lat_min = forms.CharField(label="North Lat Min", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Min'}))
    north_lat_sec = forms.CharField(label="North Lat Sec", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Sec'}))

    south_lat_deg = forms.CharField(label="South Lat Deg", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Deg'}))
    south_lat_min = forms.CharField(label="South Lat Min", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Min'}))
    south_lat_sec = forms.CharField(label="South Lat Sec", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Sec'}))

    east_lon_deg = forms.CharField(label="East Lon Deg", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Deg'}))
    east_lon_min = forms.CharField(label="East Lon Min", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Min'}))
    east_lon_sec = forms.CharField(label="East Lon Sec", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Sec'}))

    west_lon_deg = forms.CharField(label="West Lon Deg", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Deg'}))
    west_lon_min = forms.CharField(label="West Lon Min", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Min'}))
    west_lon_sec = forms.CharField(label="West Lon Sec", required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': 'Sec'}))

    class Meta:
        model = DatasetSubmission
        fields = [
            # Identification
            'expedition_type',
            'title',
            'category',
            'keywords',
            'topic',
            'iso_topic',
            'expedition_year',
            'expedition_number',
            'project_number',
            'project_name',
            'abstract',
            'purpose',
            'version',
            # 'data_center', # Removed - uses model default

            # Temporal
            'temporal_start_date',
            'temporal_end_date',

            # Spatial (Hidden, populated via save method)
            # 'west_longitude', 'east_longitude', 'south_latitude', 'north_latitude',

            # Spatial (Hidden, populated via save method)
            # 'west_longitude', 'east_longitude', 'south_latitude', 'north_latitude',

            # Access - REMOVED PER USER REQUEST
            # 'access_type',
            # 'embargo_date',
            # 'license',
            # 'usage_restrictions',

            # Contact - REMOVED PER USER REQUEST
            # 'contact_person',
            # 'contact_email',
            # 'contact_phone',
            'data_set_progress',
            
        ]

        labels = {
            'title': 'Metadata Title',
            'category': 'Category',
            'keywords': 'Biological Classification',
            'topic': 'Topic',
            'iso_topic': 'ISO Topic',
            'expedition_number': 'Expedition No',
            'project_number': 'Project Number',
            'project_name': 'Project Name',
            'abstract': 'Abstract',
            'purpose': 'Purpose',
            'version': 'Version',
            'data_set_progress': 'Data Set Progress',
            
            # Others mapped
            'temporal_start_date': 'Start Date',
            'temporal_end_date': 'End Date',
        }

        widgets = {
            # Date pickers
            'temporal_start_date': forms.DateInput(attrs={'type': 'date'}),
            'temporal_end_date': forms.DateInput(attrs={'type': 'date'}),
            
            # Topic as Select (populated by JS)
            'topic': forms.Select(attrs={'id': 'id_topic'}),
            'category': forms.Select(attrs={'id': 'id_category'}),

            # Character Counters
            'title': forms.TextInput(attrs={'maxlength': '220', 'class': 'char-counter'}),
            'abstract': forms.Textarea(attrs={'maxlength': '1000', 'class': 'char-counter', 'rows': 4}),
            'purpose': forms.Textarea(attrs={'maxlength': '1000', 'class': 'char-counter', 'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['keywords'].required = False
        
        # Set default for data_center if not bound
        if 'data_center' in self.fields:
            self.fields['data_center'].initial = "National Polar Data Center"

        # Customize dropdowns to remove "---------"
        self.fields['category'].choices = [('', 'Select Category')] + DatasetSubmission.CATEGORY_CHOICES
        self.fields['iso_topic'].choices = [('', 'Select ISO Topic')] + DatasetSubmission.ISO_TOPIC_CHOICES
        self.fields['data_set_progress'].choices = [('', 'Select Progress')] + DatasetSubmission.DATA_PROGRESS_CHOICES
        self.fields['data_set_progress'].choices = [('', 'Select Progress')] + DatasetSubmission.DATA_PROGRESS_CHOICES
        
        # Expedition Year
        year_choices = DatasetSubmission.get_expedition_year_choices()
        self.fields['expedition_year'].choices = [('', 'Select Expedition Year')] + year_choices

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'

        # Populate DMS fields from instance decimal degrees
        if self.instance and self.instance.pk:
            self.fields['topic'].widget.attrs['data-initial'] = self.instance.topic
            self._populate_dms('north_lat', self.instance.north_latitude)
            self._populate_dms('south_lat', self.instance.south_latitude)
            self._populate_dms('east_lon', self.instance.east_longitude)
            self._populate_dms('west_lon', self.instance.west_longitude)

    def _populate_dms(self, prefix, value):
        """Helper to convert Decimal -> DMS and populate fields"""
        if value is not None:
            deg = int(value)
            temp = 60 * (abs(value) - abs(deg))
            min_val = int(temp)
            sec = round(60 * (temp - min_val), 2)
            
            self.fields[f'{prefix}_deg'].initial = deg
            self.fields[f'{prefix}_min'].initial = min_val
            self.fields[f'{prefix}_sec'].initial = sec

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Convert DMS -> Decimal for storage
        instance.north_latitude = self._dms_to_decimal('north_lat')
        instance.south_latitude = self._dms_to_decimal('south_lat')
        instance.east_longitude = self._dms_to_decimal('east_lon')
        instance.west_longitude = self._dms_to_decimal('west_lon')
        
        if commit:
            instance.save()
        return instance

    def _dms_to_decimal(self, prefix):
        """Helper to convert DMS fields -> Decimal"""
        try:
            d = float(self.cleaned_data.get(f'{prefix}_deg') or 0)
            m = float(self.cleaned_data.get(f'{prefix}_min') or 0)
            s = float(self.cleaned_data.get(f'{prefix}_sec') or 0)
            sign = 1 if d >= 0 else -1
            return sign * (abs(d) + (m / 60) + (s / 3600))
        except (ValueError, TypeError):
            return 0.0


class DatasetUploadForm(forms.ModelForm):
    """Separate form for file uploads after metadata submission"""
    class Meta:
        model = DatasetSubmission
        fields = ['data_file']
        labels = {
            'data_file': 'Add Actual\\Processed Dataset'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_file'].widget.attrs.update({'class': 'form-control'})

    def clean_data_file(self):
        file = self.cleaned_data.get('data_file')
        if file:
            # Security: Validate file extension
            try:
                ext = file.name.split('.')[-1].lower()
            except IndexError:
                ext = ""
            
            forbidden_exts = ['exe', 'sh', 'php', 'html', 'js', 'py', 'bat', 'cmd', 'dll', 'cgi', 'pl']
            if ext in forbidden_exts:
                raise ValidationError("For security reasons, this file type is not allowed.")
            
            # Limit size (e.g., 500MB)
            if file.size > 500 * 1024 * 1024:
                raise ValidationError("File size too large (Max 500MB).")
                
        return file


# =====================================================
# RELATED FORMS
# =====================================================

class DatasetCitationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('prefix', 'citation')
        super().__init__(*args, **kwargs)

    class Meta:
        model = DatasetCitation
        exclude = ('dataset',)
        labels = {
            'creator': 'Creator',
            'editor': 'Editor',
            'title': 'Title',
            'series_name': 'Series Name',
            'release_date': 'Release Date',
            'release_place': 'Release Place',
            'online_resource': 'Online Resource',
        }
        widgets = {
             'release_date': forms.DateInput(attrs={'type': 'date'}),
        }


class ScientistDetailForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['country'].widget.attrs.update({'id': 'id_country', 'class': 'country-select form-select'})
        self.fields['state'].widget.attrs.update({'id': 'id_state', 'class': 'state-select form-select'})
        self.fields['city'].widget.attrs.update({'class': 'city-select'})

        if self.instance and self.instance.pk:
             self.fields['state'].widget.attrs['data-initial'] = self.instance.state

    class Meta:
        model = ScientistDetail
        exclude = ('dataset',)
        labels = {
            'role': 'Role',
            'title': 'Title',
            'first_name': 'First Name',
            'middle_name': 'Middle Name',
            'last_name': 'Last Name',
            'email': 'E-mail',
            'phone': 'Phone',
            'mobile': 'Mobile Number',
            'institute': 'Institute/Organisation',
            'address': 'Address',
            'city': 'City',
            'country': 'Country',
            'state': 'State',
            'postal_code': 'Postal Code',
        }
        widgets = {
            'country': forms.Select(attrs={'id': 'id_country', 'class': 'country-select form-select'}),
            'state': forms.Select(attrs={'id': 'id_state', 'class': 'state-select form-select'}),
            # City reverted to default text input
        }


class InstrumentMetadataForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = InstrumentMetadata
        exclude = ('dataset',)
        labels = {
            'short_name': 'Short name',
            'long_name': 'Long name',
        }


class PlatformMetadataForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = PlatformMetadata
        exclude = ('dataset',)
        labels = {
            'short_name': 'Short name',
            'long_name': 'Long name',
        }


class GPSMetadataForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add '?' to label if not showing automatically
        self.fields['gps_used'].label = "Whether GPS is used for Data Collection ?"

    class Meta:
        model = GPSMetadata
        exclude = ('dataset',)
        labels = {
            'gps_used': 'Whether GPS is used for Data Collection ?',
        }

    def clean(self):
        cleaned = super().clean()

        gps_used = cleaned.get('gps_used')

        # If GPS not used, allow blank metadata
        if not gps_used:
            return cleaned

        # If GPS used, enforce at least altitude or depth info
        if not any([
            cleaned.get('minimum_altitude'),
            cleaned.get('maximum_altitude'),
            cleaned.get('minimum_depth'),
            cleaned.get('maximum_depth'),
        ]):
            raise ValidationError(
                "Provide altitude or depth information when GPS is used."
            )

        return cleaned


class LocationMetadataForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location_category'].choices = [('', 'Select Category')] + LocationMetadata.LOCATION_CATEGORY_CHOICES

    class Meta:
        model = LocationMetadata
        exclude = ('dataset',)
        labels = {
            'location_category': 'Category',
            'location_type': 'Type', # User list has "Region" then "Type", Mapping best effort
            'location_subregion': 'Subregion',
        }


class DataResolutionMetadataForm(forms.ModelForm):
    # Add split fields for Resolution - Labels removed for manual layout
    lat_res_deg = forms.CharField(label="", required=False)
    lat_res_min = forms.CharField(label="", required=False)
    lat_res_sec = forms.CharField(label="", required=False)
    
    lon_res_deg = forms.CharField(label="", required=False)
    lon_res_min = forms.CharField(label="", required=False)
    lon_res_sec = forms.CharField(label="", required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate split fields from model if instance exists
        if self.instance and self.instance.pk:
            self._split_resolution(self.instance.latitude_resolution, 'lat')
            self._split_resolution(self.instance.longitude_resolution, 'lon')

    def _split_resolution(self, value, prefix):
        """Helper to parse 'D M S' string into fields"""
        if value:
            parts = value.split()
            if len(parts) >= 3:
                self.fields[f'{prefix}_res_deg'].initial = parts[0]
                self.fields[f'{prefix}_res_min'].initial = parts[1]
                self.fields[f'{prefix}_res_sec'].initial = parts[2]

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Combine fields back
        lat_d = self.cleaned_data.get('lat_res_deg', '')
        lat_m = self.cleaned_data.get('lat_res_min', '')
        lat_s = self.cleaned_data.get('lat_res_sec', '')
        
        lon_d = self.cleaned_data.get('lon_res_deg', '')
        lon_m = self.cleaned_data.get('lon_res_min', '')
        lon_s = self.cleaned_data.get('lon_res_sec', '')
        
        instance.latitude_resolution = f"{lat_d} {lat_m} {lat_s}".strip()
        instance.longitude_resolution = f"{lon_d} {lon_m} {lon_s}".strip()
        
        if commit:
            instance.save()
        return instance

    class Meta:
        model = DataResolutionMetadata
        # Exclude actual model fields from form display
        exclude = ('dataset', 'latitude_resolution', 'longitude_resolution') 
        labels = {
            'horizontal_resolution_range': 'Horizontal Resolution Range',
            'vertical_resolution': 'Vertical Resolution',
            'vertical_resolution_range': 'Vertical Resolution Range',
            'temporal_resolution': 'Temporal Resolution',
            'temporal_resolution_range': 'Temporal Resolution Range',
        }

class PaleoTemporalCoverageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = PaleoTemporalCoverage
        exclude = ('dataset',)


class DatasetFilesForm(forms.ModelForm):
    class Meta:
        model = DatasetSubmission
        fields = [
            'data_file',
            'metadata_file',
            'readme_file',
            # 'number_of_files', # Removed per user request
        ]
        labels = {
            'data_file': 'Add Actual\\Processed Dataset',
            'metadata_file': 'Metadata File',
            'readme_file': 'README File',
            'number_of_files': 'Total Number of Files',
        }
        widgets = {
             'data_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
             'metadata_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
             'readme_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
             # 'number_of_files': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean_data_file(self):
        return self._validate_file('data_file')
        
    def clean_metadata_file(self):
        return self._validate_file('metadata_file')

    def clean_readme_file(self):
        return self._validate_file('readme_file')

    def _validate_file(self, field_name):
        file = self.cleaned_data.get(field_name)
        if file:
             # Security: Validate file extension
            try:
                ext = file.name.split('.')[-1].lower()
            except IndexError:
                ext = ""

            forbidden_exts = ['exe', 'sh', 'php', 'html', 'js', 'py', 'bat', 'cmd', 'dll', 'cgi', 'pl']
            if ext in forbidden_exts:
                raise ValidationError(f"File type '{ext}' is not allowed for security reasons.")
            
            # Limit size (e.g., 500MB)
            if file.size > 500 * 1024 * 1024:
                raise ValidationError("File size too large (Max 500MB).")
        return file

from captcha.fields import CaptchaField
from .models import DatasetRequest

class DatasetRequestForm(forms.ModelForm):
    captcha = CaptchaField()

    class Meta:
        model = DatasetRequest
        fields = [
            'first_name', 'last_name', 'email', 
            'institute', 'country', 'research_area', 'purpose',
            'agree_cite', 'agree_share'
        ]
