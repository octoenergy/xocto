from django.apps import AppConfig
from django.core import checks


class XoctoAppConfig(AppConfig):
    name = "xocto"

    def ready(self) -> None:
        from xocto.conf import check_settings

        checks.register(check_settings, "xocto", deploy=True)
