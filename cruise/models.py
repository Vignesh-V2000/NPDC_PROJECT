from django.db import models
from django.core.validators import RegexValidator
import os


class Cruise(models.Model):
    """
    Model to store cruise information
    """
    CRUISE_STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]

    ship_name = models.CharField(
        max_length=255,
        help_text="Name of the research vessel/ship",
        validators=[RegexValidator(
            r'^[A-Za-z0-9\s\.\-\&]+$',
            'Only letters, numbers, spaces, dots, hyphens, and ampersands allowed.'
        )]
    )
    
    cruise_no = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique cruise number/identifier",
        validators=[RegexValidator(
            r'^[A-Za-z0-9\-]+$',
            'Only letters, numbers, and hyphens allowed.'
        )]
    )
    
    cruise_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Official name of the cruise"
    )
    
    period_from = models.DateField(
        help_text="Cruise start date",
        null=True,
        blank=True
    )
    
    period_to = models.DateField(
        help_text="Cruise end date",
        null=True,
        blank=True
    )
    
    chief_scientist_name = models.CharField(
        max_length=255,
        help_text="Name of the chief scientist",
        validators=[RegexValidator(
            r'^[A-Za-z\s\.\-]+$',
            'Only letters, spaces, dots, and hyphens allowed.'
        )]
    )
    
    area = models.CharField(
        max_length=255,
        help_text="Geographic area/region of the cruise"
    )
    
    objective = models.TextField(
        help_text="Scientific objectives of the cruise"
    )
    
    status = models.CharField(
        max_length=20,
        choices=CRUISE_STATUS_CHOICES,
        default='completed',
        help_text="Current status of the cruise"
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Additional details about the cruise"
    )
    
    files_link = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Path or link to associated cruise files"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_from']
        indexes = [
            models.Index(fields=['ship_name']),
            models.Index(fields=['cruise_no']),
            models.Index(fields=['chief_scientist_name']),
            models.Index(fields=['area']),
            models.Index(fields=['-period_from']),
        ]
        verbose_name = "Cruise"
        verbose_name_plural = "Cruises"

    def __str__(self):
        return f"{self.cruise_no} - {self.ship_name}"

    def get_display_info(self):
        """Return a dictionary of cruise information for display"""
        return {
            'ship_name': self.ship_name,
            'cruise_no': self.cruise_no,
            'cruise_name': self.cruise_name,
            'period_from': self.period_from,
            'period_to': self.period_to,
            'chief_scientist_name': self.chief_scientist_name,
            'area': self.area,
            'objective': self.objective,
            'status': self.get_status_display(),
            'description': self.description,
            'files_link': self.files_link,
        }


class CruiseFile(models.Model):
    """
    Model to store files associated with cruises
    """
    FILE_TYPE_CHOICES = [
        ('report', 'Report'),
        ('data', 'Data'),
        ('document', 'Document'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('other', 'Other'),
    ]

    cruise = models.ForeignKey(
        Cruise,
        on_delete=models.CASCADE,
        related_name='files'
    )
    
    file_name = models.CharField(max_length=500)
    file_type = models.CharField(
        max_length=20,
        choices=FILE_TYPE_CHOICES,
        default='other'
    )
    
    file_path = models.CharField(
        max_length=500,
        help_text="Relative path to the file in downloads folder"
    )
    
    file_size = models.BigIntegerField(
        help_text="Size in bytes",
        null=True,
        blank=True
    )
    
    description = models.TextField(
        blank=True,
        null=True
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['file_name']
        indexes = [
            models.Index(fields=['cruise']),
            models.Index(fields=['file_type']),
        ]
        verbose_name = "Cruise File"
        verbose_name_plural = "Cruise Files"

    def __str__(self):
        return f"{self.file_name} - {self.cruise.cruise_no}"

    def get_file_extension(self):
        """Get the file extension"""
        return os.path.splitext(self.file_name)[1].lower()

    def is_pdf(self):
        """Check if file is PDF"""
        return self.get_file_extension() == '.pdf'
