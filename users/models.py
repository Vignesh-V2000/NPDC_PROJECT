from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    TITLE_CHOICES = [
        ('Mr', 'Mr'),
        ('Ms', 'Ms'),
        ('Dr', 'Dr'),
        ('Prof', 'Prof'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    title = models.CharField(max_length=10, choices=TITLE_CHOICES)
    preferred_name = models.CharField(max_length=100, blank=True)

    organisation = models.CharField(max_length=255)
    organisation_url = models.URLField(max_length=255)
    profile_url = models.URLField(max_length=255, blank=True)
    designation = models.CharField(max_length=100, blank=True)

    phone = models.CharField(max_length=10, blank=True)
    whatsapp_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    alternate_email = models.EmailField(blank=True)

    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    EXPEDITION_TYPES = [
        ('antarctic', 'Antarctic'),
        ('arctic', 'Arctic'),
        ('southern_ocean', 'Southern Ocean'),
        ('himalaya', 'Himalaya'),
    ]

    expedition_admin_type = models.CharField(
        max_length=30,
        choices=EXPEDITION_TYPES,
        blank=True,
        null=True,
        verbose_name="Admin for Expedition Type"
    )

    def __str__(self):
        return f"{self.user.email} Profile"


class UserLogin(models.Model):
    """
    Unmanaged model mapped to the legacy 'user_login' table.
    This table was imported from the old NPDC (EnterpriseDB) system.
    """
    id = models.IntegerField(primary_key=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    user_id = models.CharField(max_length=255, unique=True)  # email / login ID
    user_password = models.CharField(max_length=255)
    user_role = models.CharField(max_length=30, blank=True, null=True)
    account_status = models.CharField(max_length=15, blank=True, null=True)
    created_by = models.CharField(max_length=255, blank=True, null=True)
    created_ts = models.CharField(max_length=255, blank=True, null=True)
    updated_by = models.CharField(max_length=255, blank=True, null=True)
    updated_ts = models.CharField(max_length=255, blank=True, null=True)
    data_access_id = models.CharField(max_length=255, blank=True, null=True)
    designation = models.CharField(max_length=255, blank=True, null=True)
    organisation = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    e_mail = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=255, blank=True, null=True)
    emailvarified = models.CharField(max_length=255, blank=True, null=True)
    emailtoken = models.CharField(max_length=255, blank=True, null=True)
    url = models.CharField(max_length=100, blank=True, null=True)
    ppurl = models.CharField(max_length=100, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    known_as = models.CharField(max_length=255, blank=True, null=True)
    alt_mobile_no = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user_login'

    def __str__(self):
        return f"{self.user_id} - {self.user_name}"


