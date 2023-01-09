import structlog
from django.conf import settings

logger = structlog.get_logger("events")

__all__ = ["publish"]

METADATA = {
    "release": "GIT_SHA",
    "aws_private_ip": "AWS_LOCAL_IP",
    "aws_instance_id": "AWS_INSTANCE_ID",
    "aws_availability_zone": "AWS_AVAILABILITY_ZONE",
    "aws_auto_scaling_group": "AWS_AUTO_SCALING_GROUP",
}


def publish(event, params=None, meta=None, account=None, request=None):
    """
    Publish an event.

    - `params` are values that were used to create the event (eg the path of a
      request)
    - `meta` are contextual values around the event (eg the IP address of the
      person making the request)

    Note, structlog will add a timestamp.
    """
    payload = {"event": event}
    if params is not None:
        payload["params"] = params
    if meta is None:
        meta = {}

    # If the event relates to a single account, we include its number so it's easy to filter down
    # to events that affect one account in Loggly.
    if account is not None:
        payload["account"] = account.number

    # Add static metadata from settings.
    for key, setting in METADATA.items():
        value = getattr(settings, setting, "")
        if value:
            meta[key] = value

    # Add metadata from request
    if request is not None:
        meta.update(_request_meta(request))

    payload["meta"] = meta

    _log(payload)


def _log(event):
    """
    Log the event.
    """
    event_ = event.copy()
    name = event_.pop("event")
    logger.info(name, **event_)


def _request_meta(request):
    """
    Extract relevant meta information from a request instance.
    """
    meta = {"ip_address": request.META["REMOTE_ADDR"]}
    if "HTTP_USER_AGENT" in request.META:
        meta["user_agent"] = request.META["HTTP_USER_AGENT"]
    if hasattr(request, "session") and request.session.session_key:
        meta["session"] = request.session.session_key
    return meta
