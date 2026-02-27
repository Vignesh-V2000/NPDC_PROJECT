from django.apps import AppConfig


class DatasetSearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'npdc_search'
    
    def ready(self):
        # Import signals to register them
        from . import signals  # noqa
