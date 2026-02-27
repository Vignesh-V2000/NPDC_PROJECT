from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_submission', '0005_remove_datasetsubmission_access_type_and_more'),
    ]

    operations = [
        TrigramExtension(),
    ]
