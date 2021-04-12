from django.apps import AppConfig


class TsunamiNotifyAppConfig(AppConfig):
    """
    Django app config for the tsunami-notify app.
    """
    name = 'tsunami_notify'

    # By default, use bigints for the id field
    default_auto_field = 'django.db.models.BigAutoField'
