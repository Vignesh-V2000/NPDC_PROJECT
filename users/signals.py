from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from .models import Profile


# -------------------------------------------------
# PROFILE AUTO CREATION (SAFE)
# -------------------------------------------------

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


# -------------------------------------------------
# ACCOUNT ACTIVATION EMAIL
# -------------------------------------------------

@receiver(pre_save, sender=User)
def send_activation_email(sender, instance, **kwargs):

    if not instance.pk:
        return

    try:
        old_user = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return

    if not old_user.is_active and instance.is_active:
        text_content = f"""
Dear {instance.first_name},

We are pleased to inform you that your account with the National Polar Data Center (NPDC) has been approved and activated.

You can now log in to the portal using your credentials to submit and access datasets.

Login URL: {settings.Login_URL if hasattr(settings, 'Login_URL') else 'https://npdc.ncpor.res.in/accounts/login/'}

If you encounter any issues, please do not hesitate to contact our support team.

Best Regards,
NPDC Data Team
National Polar Data Center
"""

        email = EmailMultiAlternatives(
            subject='[NPDC Portal] Account Approved and Activated',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[instance.email],
        )
        email.send()



