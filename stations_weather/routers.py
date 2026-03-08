class WeatherDatabaseRouter:
    """
    A router to control all database operations on models in the
    stations_weather application.
    """
    route_app_labels = {'stations_weather'}

    def db_for_read(self, model, **hints):
        """
        Attempts to read stations_weather models go to data_analysis.
        """
        if model._meta.app_label in self.route_app_labels:
            from django.conf import settings
            if 'data_analysis' in settings.DATABASES:
                return 'data_analysis'
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write stations_weather models go to data_analysis.
        """
        if model._meta.app_label in self.route_app_labels:
            from django.conf import settings
            if 'data_analysis' in settings.DATABASES:
                return 'data_analysis'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the stations_weather app is involved.
        """
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the stations_weather app only appears in the
        'data_analysis' database.
        """
        if app_label in self.route_app_labels:
            return db == 'data_analysis'
        return None
