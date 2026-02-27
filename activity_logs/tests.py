from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from .models import ActivityLog
from data_submission.models import DatasetSubmission
from .middleware import ActivityLogMiddleware
import threading

class ActivityLogTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.admin = User.objects.create_superuser(username='admin', password='password')

    def test_create_log_on_login(self):
        # Login signal is hard to test without full client login, but we can verify signal connection
        # Using client to login
        self.client.login(username='testuser', password='password')
        # Check logs
        self.assertTrue(ActivityLog.objects.filter(actor=self.user, action_type='LOGIN').exists())

    def test_create_log_on_dataset_creation(self):
        # We need to simulate the middleware setting the request in thread locals
        request = self.factory.get('/')
        request.user = self.user
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        
        # Manually invoke middleware logic to set thread local
        middleware = ActivityLogMiddleware(lambda r: None)
        middleware(request)

        # Create dataset
        ds = DatasetSubmission.objects.create(
            title="Test Dataset",
            submitter=self.user,
            temporal_start_date='2022-01-01',
            temporal_end_date='2022-01-02',
            west_longitude=10, east_longitude=20,
            south_latitude=10, north_latitude=20,
            contact_email='test@example.com'
        )
        
        # Check logs
        log = ActivityLog.objects.filter(entity_name='DatasetSubmission', action_type='CREATE').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.user)
        self.assertIn("Test Dataset", log.remarks)

    def test_log_approval(self):
        # Setup request context
        request = self.factory.get('/')
        request.user = self.admin
        middleware = ActivityLogMiddleware(lambda r: None)
        middleware(request)

        ds = DatasetSubmission.objects.create(
            title="Dataset to Approve",
            submitter=self.user,
            temporal_start_date='2022-01-01',
            temporal_end_date='2022-01-02',
            west_longitude=10, east_longitude=20,
            south_latitude=10, north_latitude=20,
            contact_email='test@example.com',
            status='submitted'
        )
        
        # Approve it
        ds.status = 'approved'
        ds.save()
        
        # Check logs
        log = ActivityLog.objects.filter(entity_name='DatasetSubmission', action_type='APPROVE').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.actor, self.admin)
