"""
The settings for the ``xocto`` package. This acts as a proxy to
``django.conf.settings`` and provides a way for us to set accurate types and
defaults.
"""

import dataclasses
from typing import Any, List, Optional, Union, get_args, get_origin

from django.apps import AppConfig
from django.conf import settings as django_settings
from django.core import checks


@dataclasses.dataclass(frozen=True, init=False, repr=False)
class XoctoSettings:
    """Access this instance as ``xocto.conf.settings``"""

    BOTO_S3_CONNECT_TIMEOUT: Optional[Union[float, int]] = None
    """
    Connect timeout in seconds for S3. If the value is not ``None``, it's passed
    as the ``connect_timeout`` parameter to :py:class:`botocore.config.Config`,
    otherwise the default is used.
    """

    BOTO_S3_READ_TIMEOUT: Optional[Union[float, int]] = None
    """
    Read timeout in seconds for S3. If the value is not ``None``, it's passed
    as the ``read_timeout`` parameter to :py:class:`botocore.config.Config`,
    otherwise the default is used.
    """

    BOTO_S3_TOTAL_MAX_ATTEMPTS: Optional[int] = None
    """
    The total number of attempts to make for a particular request to S3,
    including the initial request.  If the value is not ``None``, it's passed as
    the value of the  ``"total_max_attempts"`` key of the ``retries`` parameter
    to :py:class:`botocore.config.Config`.
    """

    # TODO: these are the other settings that xocto refers to, go through them
    # and work out which ones are xocto-specific and add types and defaults as
    # needed:
    # - AWS_AUTO_SCALING_GROUP
    # - AWS_AVAILABILITY_ZONE
    # - AWS_INSTANCE_ID
    # - AWS_LOCAL_IP
    # - AWS_REGION
    # - AWS_S3_ENDPOINT_URL
    # - DOCUMENT_STORAGE_BACKEND
    # - EMAIL_STORAGE_BACKEND
    # - EMAIL_STORAGE_ROOT
    # - GIT_SHA
    # - INTEGRATION_FLOW_S3_OUTBOUND_BUCKET
    # - LINE_INBOUND_ATTACHMENTS_BUCKET
    # - MEDIA_ROOT
    # - MEDIA_URL
    # - S3_ARCHIVE_BUCKET
    # - S3_FILESERVER_BUCKET
    # - S3_PRODUCTION_FLOWS_OUTBOUND
    # - S3_SUPPORT_DOCUMENTS_BUCKET
    # - S3_USER_DOCUMENTS_BUCKET
    # - S3_USER_MEDIA_BUCKET
    # - S3_VOICE_AUDIO_BUCKET
    # - STORAGE_BACKEND

    def __getattribute__(self, name: str) -> Any:
        """
        If a setting is defined in the Django settings, return it from there.
        Otherwise, return the default value from this class.
        """
        if name in _setting_names:
            try:
                return getattr(django_settings, name)
            except AttributeError:
                pass
        return super().__getattribute__(name)


_setting_names = {f.name for f in dataclasses.fields(XoctoSettings)}


settings = XoctoSettings()


def check_settings(
    app_configs: Optional[List[AppConfig]], **kwargs: object
) -> List[checks.CheckMessage]:
    """
    A system check that ensures that the values of any Django settings
    referenced by xocto have the correct types.
    """
    messages: List[checks.CheckMessage] = []

    for field in dataclasses.fields(XoctoSettings):
        value = getattr(settings, field.name)

        if (origin := get_origin(field.type)) is not None:
            if origin is Union:
                value_types = get_args(field.type)
            else:
                raise TypeError("Unexpected origin type for generic settings field")
        else:
            value_types = (field.type,)

        if not isinstance(value, value_types):
            messages.append(
                checks.Error(
                    f"settings.{field.name} is the wrong type: expected {'/'.join(sorted(t.__name__ for t in value_types))}, got {type(value).__name__}",
                    hint="If the value is read from an environment variable as a string, ensure it's validated and converted to the correct type in the settings module",
                    id="xocto.E001",
                )
            )

    return messages
