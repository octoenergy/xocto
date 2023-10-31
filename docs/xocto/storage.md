# Storage

## AWS S3 communication utility

Storage is an AWS S3 communication utility. It also includes a helper for file-like objects. It's been used for years at Kraken Tech, comes with extensive tests, and a growing set of documentation.

## Basic Usage

```python
import typing
from xocto.storage import storage


def upload_file(
        bucket: str,
        namespace: str,
        filename: str,
        contents: str|typing.IO) -> str:
    """
        Files can either be string or IO file buffers,
        returns the key path
    """
    file_store = storage.store(bucket, use_date_in_key_path=False)
    file_store.store_file(
        namespace=namespace, filename=filename, contents=contents
    )
    return f"{namespace}/{filename}"

def download_file(
        bucket: str,
        namespace: str,
        filename: str) -> bytes:
    file_store = storage.store(bucket, use_date_in_key_path=False)
    return file_store.fetch_file_contents(
        key_path=f"{namespace}/{filename}"
    )
```

## API Reference

```{eval-rst}
.. module:: xocto.types

.. automodule:: xocto.storage.storage
   :members:
   :undoc-members:
   :show-inheritance:
```
