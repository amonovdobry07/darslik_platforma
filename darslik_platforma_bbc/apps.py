from django.apps import AppConfig


class DarslikPlatformaBbcConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'darslik_platforma_bbc'
    
    def ready(self):
        """Signal'larni ulash"""
        import darslik_platforma_bbc.signals