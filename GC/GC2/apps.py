from django.apps import AppConfig

class GC2Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'GC2'

    def ready(self):
        import GC2.signals