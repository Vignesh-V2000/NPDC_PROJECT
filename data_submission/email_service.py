from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import EmailLog


def send_dataset_email(dataset):

    template_map = {
        "approved": "emails/dataset_approved.html",
        "rejected": "emails/dataset_rejected.html",
        "needs_revision": "emails/dataset_revision.html",
        "under_review": "emails/dataset_under_review.html",
    }

    template = template_map.get(dataset.status)

    if not template:
        return

    html_content = render_to_string(template, {
        "dataset": dataset
    })

    # ⭐ Plain text fallback
    text_content = f"""
Dataset Status Update

Dataset Title: {dataset.title}
Status: {dataset.status}

Please login to NPDC portal for more details.
"""

    subject = f"Dataset Status Update - {dataset.title}"

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,   # ✅ FIXED
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[dataset.submitter.email],
    )

    email.attach_alternative(html_content, "text/html")
    email.send()

    # ⭐ Log Email
    EmailLog.objects.create(
        dataset=dataset,
        recipient=dataset.submitter.email,
        subject=subject,
        status=dataset.status
    )
