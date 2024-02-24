SECRET_KEY = "x"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "xocto-dev",
        "USER": "postgres",
        "HOST": "localhost",
    }
}
INSTALLED_APPS = ["xocto", "django.contrib.auth", "django.contrib.contenttypes"]
USE_TZ = True
TIME_ZONE = "Europe/London"
STORAGE_BACKEND = "xocto.storage.storage.MemoryFileStore"
RAISE_ERROR_ON_EXISTING_S3_KEYS = False
