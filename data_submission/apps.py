from django.apps import AppConfig

class DataSubmissionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'data_submission'

    def ready(self):
        import data_submission.signals
