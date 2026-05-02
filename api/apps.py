from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "api"

    def ready(self):
        # FuelOptimizer is instantiated at module level in views.py which
        # triggers FuelDataLoader singleton initialisation at startup.
        # Importing views here ensures the singleton is loaded before
        # the first request arrives.
        from api import views  # noqa: F401
