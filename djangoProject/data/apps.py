from django.apps import AppConfig


class DataConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'data'
    verbose_name = '外部数据同步'

    def ready(self):
        pass
