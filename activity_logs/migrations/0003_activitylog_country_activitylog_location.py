# Generated migration for country and location fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('activity_logs', '0002_sitehit_alter_activitylog_action_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitylog',
            name='country',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='activitylog',
            name='location',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
