SECRET_KEY = "x"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3"}}
INSTALLED_APPS = ["xocto", "django.contrib.auth", "django.contrib.contenttypes"]
USE_DEPRECATED_PYTZ = True
USE_TZ = True
TIME_ZONE = "Europe/London"
STORAGE_BACKEND = "xocto.storage.storage.MemoryFileStore"
RAISE_ERROR_ON_EXISTING_S3_KEYS = False
