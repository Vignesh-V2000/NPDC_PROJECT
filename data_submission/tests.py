from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core import mail
from django import forms

from .models import DatasetSubmission, DatasetRequest

# Test form without CAPTCHA for simplicity
class DatasetRequestFormNoCaptcha(forms.ModelForm):
    class Meta:
        model = DatasetRequest
        fields = [
            'first_name', 'last_name', 'email', 
            'institute', 'country', 'research_area', 'purpose',
            'agree_cite', 'agree_share'
        ]

class DataRequestEmailTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='requester', password='secret', email='rahul@example.com')
        self.admin = User.objects.create_superuser(username='admin', password='secret', email='admin@example.com')

        # create a minimal dataset submission with a small PDF file
        self.submission = DatasetSubmission.objects.create(
            title="Studies on Faunal Diversity During XVIII Indian Expedition to Antarctica, 1998-99",
            submitter=self.user,
            temporal_start_date='1998-01-01',
            temporal_end_date='1999-01-01',
            west_longitude=10, east_longitude=20,
            south_latitude=10, north_latitude=20,
            contact_email='contact@example.com'
        )
        # attach a fake PDF file so the email code has something to attach
        self.submission.data_file.save('ARTICLE+12.pdf', ContentFile(b"PDF-DATA"))
        self.submission.save()

        # log the user in for the request
        self.client.login(username='requester', password='secret')

    def test_request_triggers_email_and_logging(self):
        from unittest.mock import patch
        
        url = reverse('data_submission:get_data', args=[self.submission.metadata_id])
        
        post_data = {
            'first_name': 'Rahul',
            'last_name': 'Das',
            'email': 'rahul@example.com',
            'institute': 'NPDC',
            'country': 'India',
            'research_area': 'Polar research',
            'purpose': 'Test download',
            'agree_cite': True,
            'agree_share': True,
        }
        
        # Patch the forms module so DatasetRequestForm points to our no-CAPTCHA version
        # (CAPTCHA testing is complex; we test the core logic without it)
        with patch('data_submission.forms.DatasetRequestForm', DatasetRequestFormNoCaptcha):
            response = self.client.post(url, post_data)
        
        # Form submission should redirect on success
        self.assertEqual(response.status_code, 302)
        
        # The request object should exist and link back to submission  
        req = DatasetRequest.objects.get(email='rahul@example.com')
        self.assertEqual(req.dataset, self.submission)
        self.assertEqual(req.requester, self.user)

        # Email should be sent with cc to admin
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('Dataset Request', email.subject)
        self.assertIn('Rahul Das', email.body)
        self.assertIn('.pdf', email.body)  # Check for PDF in body
        self.assertEqual(email.to, ['rahul@example.com'])
        self.assertIn('admin@example.com', email.cc)
        # Attachment should be present (filename may vary due to Django's sanitization)
        self.assertTrue(any('.pdf' in att[0] for att in email.attachments))
