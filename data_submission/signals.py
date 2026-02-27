from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from .models import DatasetSubmission


# -------------------------------------------------
# DATASET STATUS EMAIL SIGNAL
# -------------------------------------------------

@receiver(pre_save, sender=DatasetSubmission)
def send_dataset_status_email(sender, instance, **kwargs):

    if not instance.pk:
        return  # New dataset → no email

    try:
        old_dataset = DatasetSubmission.objects.get(pk=instance.pk)
    except DatasetSubmission.DoesNotExist:
        return

    if old_dataset.status != instance.status:

        html_content = render_to_string(
            'emails/dataset_status_update.html',
            {
                'title': instance.title,
                'status': instance.get_status_display(),
                'reviewer_notes': instance.reviewer_notes,
                'username': instance.submitter.username,
            }
        )

        text_content = f"""
Dear {instance.submitter.username},

The status of your dataset "{instance.title}" has been updated.

Current status: {instance.get_status_display()}

Regards,
NPDC Team
"""

        email = EmailMultiAlternatives(
            subject=f'Dataset Status Updated - {instance.title}',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[instance.submitter.email],
        )

        email.attach_alternative(html_content, "text/html")
        email.send()
