from django.apps import AppConfig


class StudentappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'StudentApp'

class StudentappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'StudentApp'

    # --- ADD THIS FUNCTION ---
    def ready(self):
        import StudentApp.signals