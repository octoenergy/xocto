# Storage

## AWS S3 communication utility

Storage is an AWS S3 communication utility. It also includes a helper for file-like objects. It's been used for years at Kraken Tech, comes with extensive tests, and a growing set of documentation.

## Basic Usage

```python
import typing
from xocto.storage import storage


def upload_file(
    bucket: str, namespace: str, filename: str, contents: str | typing.IO
) -> str:
    """
    Files can either be string or IO file buffers,
    returns the key path
    """
    file_store = storage.store(bucket, use_date_in_key_path=False)
    file_store.store_file(namespace=namespace, filename=filename, contents=contents)
    return f"{namespace}/{filename}"


def download_file(bucket: str, namespace: str, filename: str) -> bytes:
    file_store = storage.store(bucket, use_date_in_key_path=False)
    return file_store.fetch_file_contents(key_path=f"{namespace}/{filename}")
```

## Direct construction and connection overrides

When constructing `S3FileStore` or `S3SubdirectoryFileStore` directly, use the
keyword-only `region_name` and `endpoint_url` parameters to override the default S3
connection settings:

```python
from xocto.storage import storage

store = storage.S3FileStore(
    bucket_name="my-bucket",
    region_name="us-west-2",
    endpoint_url="https://s3.custom-domain.com",
)

subdirectory_store = storage.S3SubdirectoryFileStore(
    "s3://my-bucket/subpath",
    region_name="us-west-2",
    endpoint_url="https://s3.custom-domain.com",
)
```

Each parameter defaults to `None`. An omitted or `None` value independently falls back
to `settings.AWS_REGION` or `settings.AWS_S3_ENDPOINT_URL`, respectively. This is useful
when needing to access S3 in a region and/or URL different from the one configured via
the Django settings.

## API Reference

```{eval-rst}
.. module:: xocto.storage.storage

.. automodule:: xocto.storage.storage
   :members:
   :undoc-members:
   :show-inheritance:
```
