"""Static checks for the public storage file-content contract."""

from __future__ import annotations

import io
from typing import IO, Any

from botocore.response import StreamingBody

from xocto.storage import storage


class MinimalReadableBinaryFile:
    def read(self, size: int = -1) -> bytes:
        return b"contents"


def _verify_store_file_contents(store: storage.BaseS3FileStore) -> None:
    io_contents: IO[Any] = io.BytesIO(b"contents")
    readable_contents: storage.ReadableBinaryFile = MinimalReadableBinaryFile()

    store.store_file("namespace", "text.txt", "contents")
    store.store_file("namespace", "bytes.txt", b"contents")
    store.store_file("namespace", "io.txt", io_contents)
    store.store_file(
        "namespace",
        "streaming-body.txt",
        StreamingBody(io.BytesIO(b"contents"), 8),
    )
    store.store_file(
        "namespace",
        "readable-binary-file.txt",
        readable_contents,
    )


_verify_store_file_contents(storage.S3FileStore("some-bucket"))
_verify_store_file_contents(storage.S3SubdirectoryFileStore("s3://some-bucket/prefix"))
_verify_store_file_contents(storage.LocalFileStore("some-bucket"))
_verify_store_file_contents(storage.LocalEmailStore("some-bucket"))
_verify_store_file_contents(storage.LocalDocumentStorage("some-bucket"))
_verify_store_file_contents(storage.FileSystemFileStore("file:///tmp/some-bucket"))
_verify_store_file_contents(storage.MemoryFileStore("some-bucket"))
_verify_store_file_contents(storage.store("some-bucket"))
_verify_store_file_contents(storage.email_store("some-bucket"))
_verify_store_file_contents(storage.fileserver_store())
_verify_store_file_contents(storage.flows_outbound_store())
_verify_store_file_contents(storage.user_documents())
_verify_store_file_contents(storage.archive())
_verify_store_file_contents(storage.support_documents_store())
_verify_store_file_contents(storage.voice_audio_statics_store())
_verify_store_file_contents(storage.outbound_flow_store())
_verify_store_file_contents(storage.from_uri("s3://some-bucket/prefix"))
_verify_store_file_contents(storage.from_uri("file:///tmp/some-bucket"))
_verify_store_file_contents(storage.from_uri("memory://some-bucket"))
_verify_store_file_contents(storage.user_media_store())
_verify_store_file_contents(storage.line_file_store())
