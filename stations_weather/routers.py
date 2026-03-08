class WeatherDatabaseRouter:
    """
    A router to control all database operations on models in the
    stations_weather application, correctly routing between data_analysis
    and polardb.
    """
    route_app_labels = {'stations_weather'}
    
    # Models residing only in data_analysis
    data_analysis_models = {'bharatiweatherdata', 'last24hrsdata'}
    # Models residing in polardb
    polardb_models = {'maitriweatherdata', 'himanshweatherdata', 'himadriweatherdata', 'himanshwaterlevel'}

    def db_for_read(self, model, **hints):
        """
        Attempts to read stations_weather models go to their respective databases.
        """
        if model._meta.app_label in self.route_app_labels:
            from django.conf import settings
            model_name = model._meta.model_name
            
            if model_name in self.data_analysis_models and 'data_analysis' in settings.DATABASES:
                return 'data_analysis'
            elif model_name in self.polardb_models and 'polardb' in settings.DATABASES:
                return 'polardb'
            # If databases aren't configured in settings, fallback to None (default)
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write stations_weather models go to their respective databases.
        """
        if model._meta.app_label in self.route_app_labels:
            from django.conf import settings
            model_name = model._meta.model_name
            
            if model_name in self.data_analysis_models and 'data_analysis' in settings.DATABASES:
                return 'data_analysis'
            elif model_name in self.polardb_models and 'polardb' in settings.DATABASES:
                return 'polardb'
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
        Make sure the stations_weather app models migrate to the correct databases
        if we ever managed them. 
        """
        if app_label in self.route_app_labels:
            if model_name in self.data_analysis_models:
                return db == 'data_analysis'
            elif model_name in self.polardb_models:
                return db == 'polardb'
        return None
