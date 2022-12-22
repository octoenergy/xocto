from __future__ import annotations

import abc
import base64
import dataclasses
import hashlib
import io
import os
import random
import re
import shutil
import urllib.parse
import uuid
from collections import defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    AnyStr,
    BinaryIO,
    Iterable,
    Iterator,
    Protocol,
    TextIO,
    cast,
    runtime_checkable,
)

import boto3
import magic
from botocore import exceptions as botocore_exceptions
from botocore.response import StreamingBody
from django.conf import settings
from django.urls import reverse
from django.utils.module_loading import import_string

from xocto import events, localtime

from . import files, s3_select

if TYPE_CHECKING:
    from _typeshed import WriteableBuffer
    from mypy_boto3_s3 import service_resource
    from mypy_boto3_s3.client import S3Client


StorageFile = StreamingBody

# This URL is returned from `fetch_url()` in cases where a legitimate URL
# cannot be returned. For example, a legitimate URL cannot be returned
# for files stored in the `MemoryFileStore` during testing.
TEST_FETCH_URL = "http://www.example.com/file.txt"

TEMP_FOLDER = "/tmp"  # nosec

# The maximum length allowed for an S3 key
MAX_KEY_LENGTH = 1024

# S3 select can have a max size of 1 MB.
MAX_S3_SELECT_SIZE_RANGE = 1_048_576

# Regex for s3 URLs in the "virtual hosted" format
S3_VIRTUAL_HOSTED_URL_RE = re.compile(
    r"https://(?P<bucket>.+).s3.((?P<region>.*).)?amazonaws.com/(?P<key>.+)"
)


def _should_raise_error_on_existing_files() -> bool:
    """
    Check if we should error when a file is being overwritten without explicit overwrite=True.
    """
    return False


def _log_existing_file_returned(filename: str) -> None:
    events.publish("storage.file.existing-returned", params={"filename": filename})


class FileExists(Exception):
    pass


class KeyDoesNotExist(Exception):
    pass


class BucketNotVersioned(Exception):
    pass


class S3SelectUnexpectedResponse(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class PreSignedPost:
    """
    Pre-signed post url.

    For more details see:
    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3-presigned-urls.html#generating-a-presigned-url-to-upload-a-file
    """

    url: str
    key: str
    fields: dict[str, Any]


@dataclasses.dataclass(frozen=True)
class S3Object:
    bucket_name: str
    key: str
    version_id: str | None = None


@runtime_checkable
class Clearable(Protocol):
    def clear(self) -> None:
        ...


class ReadableBinaryFile(Protocol):
    def read(self, size: int = ...) -> bytes:
        ...


class StreamingBodyIOAdapter(io.RawIOBase):
    """
    Wrapper to adapt a boto3 S3 object to a standard Python "file-like" object

    Boto3 returns S3 files as instances as of botocore.response.StreamingBody. These have a `read`
    method but are otherwise not quite "file-like" enough to be drop in equivalents of anything in
    the normal Python IO hierarchy.

    This class is an subclass of io.RawIOBase which works by wrapping a boto StreamingBody. The
    storage module uses it so that it can return normal looking Python file objects and hide
    whether the backing store is S3 or not.
    """

    def __init__(self, streaming_body: StreamingBody) -> None:
        self.streaming_body = streaming_body

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: WriteableBuffer) -> int:
        """
        Read bytes into a pre-allocated, writable buffer-like object

        Mutates `buffer` and returns the number of bytes read.
        """
        # buffer has to be typed as `buffer: WriteableBuffer` because that's how the superclass is
        # typed. However, WriteableBuffer is a Union of several Python buffer-like objects, not all
        # of which support __len__ or __set_item__ in the way needed by our implementation of this
        # method. This assert exists to make mypy pass but isn't totally satisfying because in
        # theory there might be a way that this method is called with one of the weirder buffer
        # classes in the Union, like pickle.PickleBuffer.
        # See https://github.com/python/typeshed/blob/master/stdlib/_typeshed/__init__.pyi for the
        # definition of WriteableBuffer.
        assert isinstance(buffer, bytearray | memoryview)

        requested_size = len(buffer)
        data = self.streaming_body.read(requested_size)
        data_size = len(data)
        buffer[:data_size] = data
        return data_size

    def close(self) -> None:
        self.streaming_body.close()
        super().close()


class BaseS3FileStore(abc.ABC):
    # Define the interface for subclasses

    def __init__(
        self,
        bucket_name: str,
        use_date_in_key_path: bool = True,
        set_acl_bucket_owner: bool = False,
    ) -> None:
        self.bucket_name = bucket_name
        self.date_in_key_path = use_date_in_key_path
        self.set_acl_bucket_owner = set_acl_bucket_owner

    @abc.abstractmethod
    def store_file(
        self,
        namespace: str,
        filename: str,
        contents: AnyStr | ReadableBinaryFile,
        content_type: str = "",
        overwrite: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        """
        Store a file in S3 given its filename and contents. Contents should be UTF-8 encoded.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def store_versioned_file(
        self,
        key_path: str,
        contents: AnyStr | io.BytesIO,
        content_type: str = "",
    ) -> tuple[str, str, str]:
        """
        Store a file in S3 given its filename and contents. Contents should be UTF-8 encoded.

        The bucket must have versioning enabled.
        If the key is not known, `make_key_path` should be called to generate it.

        :raises BucketNotVersioned: if the bucket does not have versioning enabled.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def store_filepath(
        self, namespace: str, filepath: str, overwrite: bool = False, dest_filepath: str = ""
    ) -> tuple[str, str]:
        raise NotImplementedError()

    def make_key_path(self, *, namespace: str = "", filepath: str) -> str:
        """
        Return the full file (key) path given a namespace and filepath.

        This is normally just `{namespace}/{filepath}` except when `self.use_date_in_key_path` is
        true, in which case today's date is inserted in between:

            `{namespace}/2021/07/20/{filepath}`

        Use this to determine the key path that would be returned by the `store_file*` functions
        for the same namespace and filepath.
        """
        if namespace:
            # Remove trailing slash to avoid creating a "directory" named "/" in the path.
            namespace = namespace.rstrip("/")

        if self.date_in_key_path:
            today = localtime.today()
            parts = [v for v in [namespace, today.strftime("%Y/%m/%d"), filepath] if v]
        else:
            parts = [v for v in [namespace, filepath] if v]

        key_path = os.path.join(*parts)
        if len(key_path) > MAX_KEY_LENGTH:
            raise RuntimeError(
                f"Generated `key_path` must not exceed {MAX_KEY_LENGTH} characters in length"
            )

        return key_path

    @abc.abstractmethod
    def get_key(self, key_path: str, version_id: str | None = None) -> S3Object:
        raise NotImplementedError()

    def get_key_or_store_file(
        self,
        *,
        namespace: str = "",
        filepath: str,
        contents: bytes,
        content_type: str = "",
    ) -> tuple[tuple[str, str], bool]:
        """
        Return the full key for `namespace` and `filepath`, writing `contents` if there's nothing
        already at that key path.

        Warning: this is open to race conditions for certain storage backends (S3) because there's
        no way to transactionally create an object at a key. E.g.:

            * Process 1 does get_key_or_store_file
            * Process 1 sees there's no file
            * Before process 1 can create the file at the key
            * Process 2 does get_key_or_store_file
            * Process 2 also sees there's no file
            * Whichever process finishes the writing to the key last wins
        """
        key_path = self.make_key_path(namespace=namespace, filepath=filepath)

        if self.exists(key_path):
            return (self.bucket_name, key_path), False

        self.store_file(
            namespace=namespace, filename=filepath, contents=contents, content_type=content_type
        )
        return (self.bucket_name, key_path), True

    @abc.abstractmethod
    def get_file_type(self, key_path: str) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def fetch_file(self, key_path: str, version_id: str | None = None) -> StorageFile:
        raise NotImplementedError()

    @abc.abstractmethod
    def fetch_file_contents(self, key_path: str, version_id: str | None = None) -> bytes:
        raise NotImplementedError()

    def fetch_text_file(
        self, key_path: str, encoding: str | None = None, errors: str | None = None
    ) -> TextIO:
        """
        Return a file from storage as a TextIO "file-like" object.
        """
        streaming_body = self.fetch_file(key_path)
        raw_io = StreamingBodyIOAdapter(streaming_body)
        buffered_io = io.BufferedReader(raw_io)
        return io.TextIOWrapper(buffered_io, encoding=encoding, errors=errors)

    @abc.abstractmethod
    def fetch_url(
        self,
        key_path: str,
        expires_in: int = 60,
        response_headers: dict[str, str] | None = None,
        version_id: str | None = None,
    ) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def generate_presigned_post(self, *, key_path: str, expires_in: int = 60) -> PreSignedPost:
        raise NotImplementedError

    @abc.abstractmethod
    def exists(self, key_path: str, as_file: bool = False) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def list_s3_keys(self, namespace: str = "") -> Iterable[S3Object]:
        raise NotImplementedError()

    def list_s3_keys_page(  # nosec B107
        self,
        namespace: str = "",
        *,
        next_token: str = "",
        max_keys: int = 100,
    ) -> tuple[Iterable[S3Object], str]:
        """Pass-thru to list_s3_keys"""
        return self.list_s3_keys(namespace), ""

    @abc.abstractmethod
    def list_files(self, namespace: str = "") -> Iterable[str]:
        raise NotImplementedError()

    def download_file(self, key_path: str) -> BinaryIO:
        filepath = self._build_download_filepath(key_path)
        _create_parent_directories(filepath)
        with open(filepath, "wb") as f:
            f.write(self.fetch_file_contents(key_path))
        return f

    def download_to_file(self, key_path: str, file_path: str) -> None:
        with open(file_path, "wb") as f:
            f.write(self.fetch_file_contents(key_path))

    @abc.abstractmethod
    def get_size_in_bytes(self, *, s3_object: S3Object) -> int:
        raise NotImplementedError()

    @abc.abstractmethod
    def copy(self, *, s3_object: S3Object, destination: str) -> S3Object:
        raise NotImplementedError()

    @abc.abstractmethod
    def rename(self, *, s3_object: S3Object, destination: str) -> S3Object:
        """
        Rename an S3 object.

        The behaviour in a versioned bucket is undefined.
        It should be defined once a clear use case has been identified.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def delete(self, *, s3_object: S3Object) -> None:
        """
        Delete an object from S3.

        If the bucket is versioned, this will only delete the specified object version.
        """
        raise NotImplementedError()

    def _build_download_filepath(self, key_path: str) -> str:
        """
        Assemble the full filename to create when downloading a file.

        Args:
            key_path (string): the S3 key of the file that will be downloaded.
        """
        return os.path.join(TEMP_FOLDER, self.bucket_name, key_path)


class S3FileStore(BaseS3FileStore):
    ACL_BUCKET_OWNER_FULL_CONTROL = "bucket-owner-full-control"

    def __init__(
        self,
        bucket_name: str,
        use_date_in_key_path: bool = True,
        set_acl_bucket_owner: bool = False,
    ) -> None:
        if not (3 <= len(bucket_name) <= 63):
            raise ValueError(
                f"`bucket_name` must be between 3 and 63 characters in length: {bucket_name}"
            )
        super().__init__(
            bucket_name,
            use_date_in_key_path=use_date_in_key_path,
            set_acl_bucket_owner=set_acl_bucket_owner,
        )

    def __str__(self) -> str:
        return f"S3 FileStore for bucket {self.bucket_name}"

    def store_file(
        self,
        namespace: str,
        filename: str,
        contents: AnyStr | ReadableBinaryFile,
        content_type: str = "",
        overwrite: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        """
        Store a file in S3 given its filename and contents. Contents should be UTF-8 encoded.

        :raises FileExists: if a file with the given name already exists in the bucket and
        raising an exception is enabled via an env var.
        """
        key_path = self.make_key_path(namespace=namespace, filepath=filename)

        if not overwrite:
            try:
                existing_boto_object = self._get_boto_object_for_key(key=key_path)
            except KeyDoesNotExist:
                pass
            else:
                if _should_raise_error_on_existing_files():
                    raise FileExists(
                        "A file with this name already exists. Pass overwrite=True if you're sure "
                        "it's safe to overwrite the contents of the existing file."
                    )
                _log_existing_file_returned(key_path)
                return self.bucket_name, existing_boto_object.key

        readable = _to_stream(contents=contents)

        # `boto_client.upload_fileobj` is type annotated with `Fileobj: BinaryIO`. However, in
        # practice the only file-like method it needs is `read(size=...)`. This cast allows us to
        # use `upload_fileobj` with any Fileobj that implements the `ReadableBinaryFile` protocol
        # but not the whole of BinaryIO. This includes, importantly, Django's `UploadedFile`.
        file_obj = cast(BinaryIO, readable)

        extra_args: dict[str, Any] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if policy := self._get_policy():
            extra_args["ACL"] = policy
        if metadata:
            extra_args["Metadata"] = metadata

        boto_client = self._get_boto_client()
        boto_client.upload_fileobj(
            Fileobj=file_obj, Bucket=self.bucket_name, Key=key_path, ExtraArgs=extra_args
        )

        return self.bucket_name, key_path

    def store_versioned_file(
        self,
        key_path: str,
        contents: AnyStr | io.BytesIO,
        content_type: str = "",
    ) -> tuple[str, str, str]:
        if not self._bucket_is_versioned():
            raise BucketNotVersioned()

        file_obj = _to_stream(contents=contents)

        extra_args: dict[str, str] = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if policy := self._get_policy():
            extra_args["ACL"] = policy

        boto_client = self._get_boto_client()
        boto_response = boto_client.put_object(
            Body=file_obj, Bucket=self.bucket_name, Key=key_path, **extra_args  # type: ignore[arg-type]
        )
        version_id = boto_response["VersionId"]

        return self.bucket_name, key_path, version_id

    def store_filepath(
        self, namespace: str, filepath: str, overwrite: bool = False, dest_filepath: str = ""
    ) -> tuple[str, str]:
        """
        Store a file in S3 given its local filepath.
        """
        if not dest_filepath:
            dest_filepath = os.path.basename(filepath)

        key_path = self.make_key_path(namespace=namespace, filepath=dest_filepath)

        if not overwrite:
            try:
                existing_boto_object = self._get_boto_object_for_key(key=key_path)
            except KeyDoesNotExist:
                pass
            else:
                if _should_raise_error_on_existing_files():
                    raise FileExists(
                        "A file with this name already exists. Pass overwrite=True if you're sure "
                        "it's safe to overwrite the contents of the existing file."
                    )
                _log_existing_file_returned(key_path)
                return self.bucket_name, existing_boto_object.key

        extra_args = {}
        if policy := self._get_policy():
            extra_args["ACL"] = policy

        boto_client = self._get_boto_client()
        boto_client.upload_file(
            Filename=filepath, Bucket=self.bucket_name, Key=key_path, ExtraArgs=extra_args
        )

        return self.bucket_name, key_path

    def get_key(self, key_path: str, version_id: str | None = None) -> S3Object:
        return S3Object(bucket_name=self.bucket_name, key=key_path, version_id=version_id)

    def get_file_type(self, key_path: str) -> str:
        return self._get_boto_object_for_key(key=key_path).content_type

    def fetch_file(self, key_path: str, version_id: str | None = None) -> StorageFile:
        boto_object = self._get_boto_object_for_key(key=key_path, version_id=version_id)
        return boto_object.get()["Body"]

    def fetch_file_contents(self, key_path: str, version_id: str | None = None) -> bytes:
        return self.fetch_file(key_path, version_id).read()

    def fetch_file_contents_using_s3_select(
        self,
        key_path: str,
        raw_sql: str,
        input_serializer: s3_select.CSVInputSerializer,
        output_serializer: s3_select.CSVOutputSerializer | s3_select.JSONOutputSerializer,
        compression_type: s3_select.CompressionType,
        scan_range: s3_select.ScanRange | None = None,
        chunk_size: int | None = None,
    ) -> Iterator[str]:
        """
        Reads a CSV file from S3 using the given SQL statement.
        Reference: https://dev.to/idrisrampurawala/efficiently-streaming-a-large-aws-s3-file-via-s3-select-4on
        """

        boto_client = self._get_boto_client()
        serialization = s3_select.get_serializers_for_csv_file(
            input_serializer=input_serializer,
            compression_type=compression_type,
            output_serializer=output_serializer,
            scan_range=scan_range,
        )

        select_object_content_parameters = dict(
            Bucket=self.bucket_name,
            Key=key_path,
            ExpressionType="SQL",
            Expression=raw_sql,
            InputSerialization=serialization["input_serialization"],
            OutputSerialization=serialization["output_serialization"],
        )

        if scan_range:
            yield from self._select_object_content_using_scan_range(
                boto_client=boto_client,
                select_object_content_parameters=select_object_content_parameters,
                key_path=key_path,
                scan_range=scan_range,
                chunk_size=chunk_size,
            )
        else:
            yield from self._select_object_content(
                boto_client=boto_client,
                select_object_content_parameters=select_object_content_parameters,
            )

    def fetch_url(
        self,
        key_path: str,
        expires_in: int = 60,
        response_headers: dict[str, str] | None = None,
        version_id: str | None = None,
    ) -> str:
        """
        Return a presigned URL that grants public access to an object. A presigned URL remains
        valid for a limited period of time which is specified with `expires_in` in seconds.
        Additional response headers can be provided with `response_headers`, using keys such as
        `"ResponseContentType"` or `"ResponseContentDisposition"`.
        """
        params = response_headers or {}
        # Ensure these values take precedence if the keys were ever, incorrectly, already in
        # the `response_headers` dictionary.
        params.update({"Bucket": self.bucket_name, "Key": key_path})
        if version_id:
            params.update({"VersionId": version_id})
        boto_client = self._get_boto_client()
        return boto_client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )

    def generate_presigned_post(self, *, key_path: str, expires_in: int = 60) -> PreSignedPost:
        boto_client = self._get_boto_client()
        presigned_post = boto_client.generate_presigned_post(
            Bucket=self.bucket_name, Key=key_path, ExpiresIn=expires_in
        )
        return PreSignedPost(
            url=presigned_post["url"],
            fields=presigned_post["fields"],
            key=presigned_post["fields"]["key"],
        )

    def exists(self, key_path: str, as_file: bool = False) -> bool:
        try:
            boto_object = self._get_boto_object_for_key(key=key_path)
        except KeyDoesNotExist:
            return False
        return not (as_file and boto_object.content_length == 0)

    def list_s3_keys(self, namespace: str = "") -> Iterable[S3Object]:
        boto_bucket = self._get_boto_bucket()
        for object_summary in boto_bucket.objects.filter(Prefix=namespace):
            yield S3Object(bucket_name=self.bucket_name, key=object_summary.key)

    def list_s3_keys_page(  # nosec B107
        self,
        namespace: str = "",
        *,
        next_token: str = "",
        max_keys: int = 100,
    ) -> tuple[Iterable[S3Object], str]:
        """
        Lists subset of files in the S3 bucket, optionally limited to only those within a given
        namespace. S3 keys ending with a forward slash are excluded, on the assumption that they
        are folders, not files.

        :param namespace: Limits keys to only those with this prefix
        :param next_token: next_token supplied from the last returned result
        :param max_keys: the number of keys to request from the bucket (<1000)
        :return: Tuple of generator of key names, and next token for next page
        """
        client = self._get_boto_client()
        # Not using ContinuationToken as ContinuationToken is tied to a specific client
        response = client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix=namespace,
            MaxKeys=max_keys,
            StartAfter=next_token,
        )
        keys = [item["Key"] for item in response.get("Contents") or []]
        next_token = keys[-1] if response["IsTruncated"] else ""
        keys = [key for key in keys if not key.endswith("/")]
        objects = [S3Object(bucket_name=self.bucket_name, key=key) for key in keys]
        return objects, next_token

    def list_files(self, namespace: str = "") -> Iterable[str]:
        """
        Lists all files in the S3 bucket, optionally limited to only those within a given
        namespace. S3 keys ending with a forward slash are excluded, on the assumption that they
        are folders, not files.

        :param namespace: Limits keys to only those with this prefix
        :return: Generator of key names
        """
        boto_bucket = self._get_boto_bucket()
        for object_summary in boto_bucket.objects.filter(Prefix=namespace):
            if not object_summary.key.endswith("/"):  # filter out folders
                yield object_summary.key

    def download_file(self, key_path: str) -> BinaryIO:
        """
        A more efficient version of the superclass's method.
        """
        boto_object = self._get_boto_object_for_key(key=key_path)
        filepath = self._build_download_filepath(key_path)
        _create_parent_directories(filepath)
        with open(filepath, "wb") as f:
            boto_object.download_fileobj(Fileobj=f)
        return f

    def download_to_file(self, key_path: str, file_path: str) -> None:
        boto_object = self._get_boto_object_for_key(key=key_path)
        boto_object.download_file(Filename=file_path)

    def get_size_in_bytes(self, *, s3_object: S3Object) -> int:
        boto_object = self._get_boto_object(s3_object=s3_object)
        return boto_object.content_length

    def copy(self, *, s3_object: S3Object, destination: str) -> S3Object:
        extra_args = {}
        if policy := self._get_policy():
            extra_args["ACL"] = policy
        dest_boto_object = self._get_boto_bucket().Object(destination)
        dest_boto_object.copy(
            CopySource={"Bucket": s3_object.bucket_name, "Key": s3_object.key},
            ExtraArgs=extra_args,
        )
        return S3Object(bucket_name=self.bucket_name, key=destination)

    def rename(self, *, s3_object: S3Object, destination: str) -> S3Object:
        src_boto_object = self._get_boto_object(s3_object=s3_object)
        extra_args = {}
        if policy := self._get_policy():
            extra_args["ACL"] = policy
        dest_boto_object = self._get_boto_bucket().Object(destination)
        dest_boto_object.copy(
            CopySource={"Bucket": s3_object.bucket_name, "Key": s3_object.key},
            ExtraArgs=extra_args,
        )
        if src_boto_object.key != dest_boto_object.key:
            # Only delete the old file if the source and destination are different. Otherwise
            # renaming a file to its own path would delete it.
            src_boto_object.delete()
        return S3Object(bucket_name=self.bucket_name, key=destination)

    def delete(self, *, s3_object: S3Object) -> None:
        boto_object = self._get_boto_object(s3_object=s3_object)
        boto_object.delete()

    # Private

    def _get_policy(self) -> str | None:
        if self.set_acl_bucket_owner:
            # If the storage class is configured to, we will set the ACL of keys that we
            # set content on to have the policy "bucket-owner-full-control".
            # This is useful when writing to a bucket where the owner is an external AWS account.
            # NB: You will need PutObjectAcl permissions on the bucket in order to set the ACL.
            return self.ACL_BUCKET_OWNER_FULL_CONTROL
        return None

    def _get_boto_client(self) -> S3Client:
        return boto3.client(
            "s3", region_name=settings.AWS_REGION, endpoint_url=settings.AWS_S3_ENDPOINT_URL
        )

    def _get_boto_bucket(self) -> service_resource.Bucket:
        boto_resource = boto3.resource("s3", region_name=settings.AWS_REGION)
        return boto_resource.Bucket(self.bucket_name)

    def _bucket_is_versioned(self) -> bool:
        boto_client = self._get_boto_client()
        versioning_info = boto_client.get_bucket_versioning(Bucket=self.bucket_name)
        return versioning_info["Status"] == "Enabled"

    def _get_boto_object(self, *, s3_object: S3Object) -> service_resource.Object:
        assert s3_object.bucket_name == self.bucket_name, (
            f"Expected an S3Object from the '{self.bucket_name}' store, "
            f"but it's from the '{s3_object.bucket_name}' store"
        )
        boto_object = self._get_boto_bucket().Object(key=s3_object.key)
        if s3_object.version_id:
            if not self._bucket_is_versioned():
                raise BucketNotVersioned()
            boto_object.version_id = s3_object.version_id

        try:
            # Calls `S3.Client.head_object()` to fetch the object's attributes; e.g. its size.
            boto_object.load()
        except botocore_exceptions.ClientError as error:
            if error.response.get("Error", {}).get("Code", "") == "404":
                raise KeyDoesNotExist("Key with path %s was not found" % s3_object.key)
            raise
        return boto_object

    def _get_boto_object_for_key(
        self, *, key: str, version_id: str | None = None
    ) -> service_resource.Object:
        # Note: It looks like it can be DRYed up with a call to self.get_key().
        # *This is not safe.* It cannot be DRYed like this.
        # It'd cause the S3SubdirectoryFileStore to add the subdir to the path, which is
        # not safe since the key may have come from somewhere that already includes this.
        return self._get_boto_object(
            s3_object=S3Object(bucket_name=self.bucket_name, key=key, version_id=version_id)
        )

    def _select_object_content(
        self,
        *,
        boto_client: S3Client,
        select_object_content_parameters: dict[str, Any],
    ) -> Iterator[str]:

        # Error codes reference: https://docs.aws.amazon.com/AmazonS3/latest/API/ErrorResponses.html#SelectObjectContentErrorCodeList
        invalid_response_statuses = [400, 401, 403, 500]

        try:
            response = boto_client.select_object_content(
                **select_object_content_parameters,
            )
        except botocore_exceptions.ClientError as error:
            if (
                error.response.get("Error", {}).get("HTTPStatusCode", None)
                in invalid_response_statuses
            ):
                raise S3SelectUnexpectedResponse("Received invalid response from S3 Select")
            raise

        if response["ResponseMetadata"]["HTTPStatusCode"] in invalid_response_statuses:
            raise S3SelectUnexpectedResponse("Received invalid response from S3 Select")

        for event_stream in response["Payload"]:
            if records := event_stream.get("Records"):  # type:ignore [attr-defined]
                yield records["Payload"].decode("utf-8")

    def _select_object_content_using_scan_range(
        self,
        *,
        boto_client: S3Client,
        select_object_content_parameters: dict[str, Any],
        key_path: str,
        scan_range: s3_select.ScanRange,
        chunk_size: int | None = None,
    ) -> Iterator[str]:
        """
        Performs SQL queries on S3 objects (CSV/JSON) using the given offsets (Scan Range)
        """
        file_size = self.get_size_in_bytes(
            s3_object=S3Object(bucket_name=self.bucket_name, key=key_path)
        )

        start_range = scan_range.Start if scan_range.Start else 0

        if chunk_size:
            chunk_size = min(chunk_size, MAX_S3_SELECT_SIZE_RANGE)
            end_range = scan_range.End if scan_range.End else min(chunk_size, file_size)

            while start_range < file_size:
                yield from self._select_object_content(
                    boto_client=boto_client,
                    select_object_content_parameters=dict(
                        **select_object_content_parameters,
                        ScanRange=dataclasses.asdict(
                            s3_select.ScanRange(Start=start_range, End=end_range)
                        ),
                    ),
                )
                start_range = end_range
                end_range = end_range + min(chunk_size, file_size - end_range)
        else:
            end_range = scan_range.End if scan_range.End else file_size

            if (end_range - start_range) > MAX_S3_SELECT_SIZE_RANGE:
                raise ValueError(
                    f"The difference between the start range and end range should be less than 1 MB ({MAX_S3_SELECT_SIZE_RANGE} bytes)."
                )

            yield from self._select_object_content(
                boto_client=boto_client,
                select_object_content_parameters=dict(
                    **select_object_content_parameters,
                    ScanRange=dataclasses.asdict(
                        s3_select.ScanRange(Start=start_range, End=end_range)
                    ),
                ),
            )


class S3SubdirectoryFileStore(S3FileStore):
    """
    A S3FileStore which can expose just a given subdirectory rather than a whole bucket.
    """

    def __init__(self, uri: str) -> None:
        parsed_url = urllib.parse.urlparse(uri)
        if parsed_url.scheme != "s3":
            raise ValueError(f"Expected URL starting 's3://'. Got {uri!r}")
        if not parsed_url.netloc:
            raise ValueError(f"Expected S3 URL including a bucket name. Got {uri!r}")

        set_acl_bucket_owner = "set_acl_bucket_owner" in parsed_url.query
        use_date_in_key_path = "use_date_in_key_path" in parsed_url.query

        self.bucket_name = parsed_url.netloc
        self.path = parsed_url.path.strip("/")
        super().__init__(
            self.bucket_name,
            use_date_in_key_path=use_date_in_key_path,
            set_acl_bucket_owner=set_acl_bucket_owner,
        )

    def make_key_path(self, *, namespace: str = "", filepath: str) -> str:
        if self.path:
            namespace = os.path.join(self.path, namespace) if namespace else self.path
        return super().make_key_path(namespace=namespace, filepath=filepath)

    def get_key(self, key_path: str, version_id: str | None = None) -> S3Object:
        if self.path:
            key_path = os.path.join(self.path, key_path)
        return super().get_key(key_path, version_id)

    def fetch_url(
        self,
        key_path: str,
        expires_in: int = 60,
        response_headers: dict[str, str] | None = None,
        version_id: str | None = None,
    ) -> str:
        if self.path:
            key_path = os.path.join(self.path, key_path)
        return super().fetch_url(
            key_path=key_path,
            expires_in=expires_in,
            response_headers=response_headers,
            version_id=version_id,
        )

    def list_s3_keys(self, namespace: str = "") -> Iterable[S3Object]:
        if self.path:
            namespace = os.path.join(self.path, namespace)
        return super().list_s3_keys(namespace)

    def list_s3_keys_page(
        self,
        namespace: str = "",
        *,
        next_token: str = "",
        max_keys: int = 100,
    ) -> tuple[Iterable[S3Object], str]:
        if self.path:
            namespace = os.path.join(self.path, namespace)
        objects, next_token = super().list_s3_keys_page(
            namespace, next_token=next_token, max_keys=max_keys
        )
        if self.path:
            objects = [
                dataclasses.replace(object, key=object.key[len(self.path) + 1 :])
                for object in objects
            ]
        return objects, next_token

    def list_files(self, namespace: str = "") -> Iterable[str]:
        if self.path:
            namespace = os.path.join(self.path, namespace)
        full_paths = super().list_files(namespace)
        yield from (path[len(self.path) + 1 :] for path in full_paths)

    def copy(self, *, s3_object: S3Object, destination: str) -> S3Object:
        if self.path:
            destination = os.path.join(self.path, destination)
        return super().copy(s3_object=s3_object, destination=destination)

    def rename(self, *, s3_object: S3Object, destination: str) -> S3Object:
        if self.path:
            destination = os.path.join(self.path, destination)
        return super().rename(s3_object=s3_object, destination=destination)

    # Private

    def _get_boto_object_for_key(
        self, *, key: str, version_id: str | None = None
    ) -> service_resource.Object:
        if self.path and not key.startswith(self.path):
            key = os.path.join(self.path, key)
        return super()._get_boto_object_for_key(key=key, version_id=version_id)


class LocalStorageBucket:
    """
    S3 bucket for local development.
    """

    document_url_base = "/static/support/sample-files/sample-documents"
    document_filenames = ["sample.pdf"]


class LocalFileStore(BaseS3FileStore):
    """
    For local development.
    """

    def __init__(
        self,
        bucket_name: str,
        storage_root: str = "",
        use_date_in_key_path: bool = True,
        set_acl_bucket_owner: bool = False,
    ) -> None:
        # This is taken from https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucketnamingrules.html
        if not (3 <= len(bucket_name) <= 63):
            raise ValueError(
                f"`bucket_name` must be between 3 and 63 characters in length: {bucket_name}"
            )

        # N.B. Overriding the storage root will mean that fetch_url won't work.
        self.storage_root = storage_root or settings.MEDIA_ROOT or "/tmp"  # nosec B108
        super().__init__(
            bucket_name,
            use_date_in_key_path=use_date_in_key_path,
            set_acl_bucket_owner=set_acl_bucket_owner,
        )

    def __str__(self) -> str:
        return f"Local FileStore for bucket {self.bucket_name} with root {self.storage_root}"

    def store_file(
        self,
        namespace: str,
        filename: str,
        contents: AnyStr | ReadableBinaryFile,
        content_type: str = "",
        overwrite: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        filepath = self._filepath(namespace, filename)
        if os.path.exists(filepath) and not overwrite:
            raise FileExists(
                f"A file with this name, {filename} already exists. Pass overwrite=True if you're sure "
                "it's safe to overwrite the contents of the existing file."
            )

        with open(filepath, "wb") as f:
            f.write(_to_bytes(contents=contents))

        return self.bucket_name, filepath

    def store_versioned_file(
        self,
        key_path: str,
        contents: AnyStr | io.BytesIO,
        content_type: str = "",
    ) -> tuple[str, str, str]:
        version = str(uuid.uuid4())
        key_components = os.path.split(key_path)
        versioned_key = os.path.join(key_components[0], version, key_components[1])
        versioned_filepath = self._filepath_for_key_path(versioned_key)

        filepath = self._filepath_for_key_path(key_path)

        with open(versioned_filepath, "wb") as f:
            f.write(_to_bytes(contents=contents))
        with open(filepath, "wb") as f:
            f.write(_to_bytes(contents=contents))

        return self.bucket_name, filepath, version

    def _build_download_filepath(self, key_path: str) -> str:
        # When uploading a file locally, the filepath we upload to is identical to the location
        # we then attempt to download to. To avoid overwriting the file, we "download" to a
        # separate "downloaded" bucket
        key_path = key_path.replace(self.bucket_name, f"{self.bucket_name}-downloaded")
        return os.path.join(self.storage_root, key_path)

    def store_filepath(
        self, namespace: str, filepath: str, overwrite: bool = False, dest_filepath: str = ""
    ) -> tuple[str, str]:
        if not dest_filepath:
            dest_filepath = os.path.basename(filepath)

        store_filepath = self._filepath(namespace, dest_filepath)
        if os.path.exists(store_filepath) and not overwrite:
            raise FileExists(
                "A file with this name already exists. Pass overwrite=True if you're sure "
                "it's safe to overwrite the contents of the existing file."
            )

        shutil.copyfile(filepath, store_filepath)
        return self.bucket_name, store_filepath

    def get_key(self, key_path: str, version_id: str | None = None) -> S3Object:
        return S3Object(bucket_name=self.bucket_name, key=key_path, version_id=version_id)

    def get_file_type(self, key_path: str) -> str:
        mime = magic.Magic(mime=True)
        return mime.from_buffer(self.fetch_file_contents(key_path))

    def fetch_file(self, key_path: str, version_id: str | None = None) -> StorageFile:
        # If given an absolute path, use that, otherwise combine with the root and bucket. When
        # fetching an object from a path, we don't need to interpolate the date or namespace.
        if version_id:
            path_components = os.path.split(key_path)
            file_path = os.path.join(
                self.storage_root,
                self.bucket_name,
                path_components[0],
                version_id,
                path_components[1],
            )
        else:
            file_path = os.path.join(self.storage_root, self.bucket_name, key_path)
        if not os.path.exists(file_path):
            raise KeyDoesNotExist(f"Key {key_path} was not found at {file_path}")
        with open(file_path, "rb") as f:
            raw_stream = io.BytesIO(f.read())
        return StreamingBody(raw_stream=raw_stream, content_length=files.size(raw_stream))

    def fetch_file_contents(self, key_path: str, version_id: str | None = None) -> bytes:
        return self.fetch_file(key_path, version_id).read()

    def fetch_url(
        self,
        key_path: str,
        expires_in: int = 60,
        response_headers: dict[str, str] | None = None,
        version_id: str | None = None,
    ) -> str:
        # N.B. This is a bit brittle, and will only work if the following things are also in place:
        # - settings.MEDIA_ROOT and settings.MEDIA_URL need to be set.
        # - Django must be configured to serve locally uploaded file as per these instructions:
        #   https://docs.djangoproject.com/en/2.2/howto/static-files/#serving-files-uploaded-by-a-user-during-development
        # - A custom storage_root is not passed to the LocalFileStore constructor.
        if key_path.startswith(self.storage_root):
            url_path = key_path.split(self.storage_root)[1]
            # Remove the bucket name from the url path, because it's already going to be added
            # to the fetch URL.
            url_path = url_path.replace(self.bucket_name, "")
        else:
            # This won't give a working url, but at least it won't raise an exception.
            url_path = key_path

        if version_id:
            path_components = os.path.split(url_path)
            url_path = os.path.join(path_components[0], version_id, path_components[1])

        return f"{settings.MEDIA_URL}{self.bucket_name}/{url_path}"

    def generate_presigned_post(self, *, key_path: str, expires_in: int = 60) -> PreSignedPost:
        return PreSignedPost(
            # Resolves to a localdev/storage url
            url=reverse("fake-presigned-post-upload"),
            key=key_path,
            # These fields should be passed in the body of the upload POST request by clients that wish to upload a file
            # In production, they contain the signature used by AWS to verify the upload.
            # Locally, however, we return the bucket name and key path so that when the upload request is made
            # we know where to store the file.
            fields={"key_path": key_path, "bucket_name": self.bucket_name},
        )

    def exists(self, key_path: str, as_file: bool = False) -> bool:
        file_path = os.path.join(self.storage_root, self.bucket_name, key_path)
        if as_file:
            return os.path.isfile(file_path)
        else:
            return os.path.exists(file_path)

    def list_s3_keys(self, namespace: str = "") -> Iterable[S3Object]:
        for filename in self.list_files(namespace):
            yield S3Object(bucket_name=self.bucket_name, key=filename)

    def list_files(self, namespace: str = "") -> Iterable[str]:
        """
        Return a generator that lists all files in the tree below the given directory.

        `namespace`:                   the directory whose contents we want to list .

        Note the following two ways in which the output of this function *differs* from the unix
        `ls` command, in order to mimic the S3 `list` output:

        1. It recurses down through subdirectories.
        2. It returns the namespace with the result.

        So given a directory structure /tmp/my-bucket/a/b/c.pdf, we could expect the following
        session:
        >>>> store = LocalFileStore('my-bucket')
        >>>> store.list_files('a')
        ['a/b/c.pdf']
        """
        prefix = os.path.join(self.storage_root, self.bucket_name, namespace)
        if not self.exists(prefix):
            return []
        else:
            return self._list_files(prefix)

    def get_size_in_bytes(self, *, s3_object: S3Object) -> int:
        filepath = os.path.join(self.storage_root, s3_object.bucket_name, s3_object.key)
        file_stats = os.stat(filepath)
        return file_stats.st_size

    def copy(self, *, s3_object: S3Object, destination: str) -> S3Object:
        shutil.copyfile(src=self._filepath("", s3_object.key), dst=self._filepath("", destination))
        return S3Object(bucket_name=self.bucket_name, key=destination)

    def rename(self, *, s3_object: S3Object, destination: str) -> S3Object:
        os.rename(src=self._filepath("", s3_object.key), dst=self._filepath("", destination))
        return S3Object(bucket_name=self.bucket_name, key=destination)

    def delete(self, *, s3_object: S3Object) -> None:
        os.remove(self._filepath("", s3_object.key))

    def _filepath(self, namespace: str, filepath: str) -> str:
        key_path = self.make_key_path(namespace=namespace, filepath=filepath)
        filepath = self._filepath_for_key_path(key_path)
        return filepath

    def _filepath_for_key_path(self, key_path: str) -> str:
        filepath = os.path.join(self.storage_root, self.bucket_name, key_path)
        _create_parent_directories(filepath)
        return filepath

    def _list_files(self, root_dir: str) -> Iterable[str]:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                # Chop off the storage root + bucket_name + /, so that the path we return starts
                # with the namespace. This keeps it compatible with the S3 store. (The empty
                # string as the final argument to `join` ensures we get a trailing slash)
                bucket_prefix = os.path.join(self.storage_root, self.bucket_name, "")
                yield os.path.join(dirpath[len(bucket_prefix) :], filename)

    def _bucket(self) -> LocalStorageBucket:
        return LocalStorageBucket()


class LocalEmailStore(LocalFileStore):
    """
    This is similar to the LocalFileStore class but returns a randomly
    selected HTML email file.
    """

    email_keys = [
        "sample-emails/A-7D673F5A.html",
        "sample-emails/A-111D3A87.html",
        "sample-emails/A-B2250731.html",
        "sample-emails/A-FBC4EF61.html",
    ]

    def __init__(self, bucket_name: str = "", *args: Any, **kwargs: Any) -> None:
        super().__init__(bucket_name=bucket_name, storage_root=settings.EMAIL_STORAGE_ROOT)

    def fetch_file_contents(self, key_path: str, version_id: str | None = None) -> bytes:
        # Randomly select one of the fixture files
        key_path = random.choice(self.email_keys)
        return super().fetch_file_contents(key_path, version_id)


class LocalDocumentStorage(LocalFileStore):
    """
    This is similar to the LocalFileStore class but returns a randomly
    selected document file from the static folder.
    """

    def __init__(self, bucket_name: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(bucket_name, storage_root="")

    def fetch_url(
        self,
        key_path: str,
        expires_in: int = 60,
        response_headers: dict[str, str] | None = None,
        version_id: str | None = None,
    ) -> str:
        bucket = self._bucket()
        return os.path.join(bucket.document_url_base, key_path)

    def list_files(self, namespace: str = "") -> Iterable[str]:
        bucket = self._bucket()
        return bucket.document_filenames


class FileSystemFileStore(LocalFileStore):
    """
    A LocalFileStore which can be constructed using a URI.
    """

    def __init__(self, uri: str) -> None:
        parsed_url = urllib.parse.urlparse(uri)
        if parsed_url.scheme != "file":
            raise ValueError(f"Expected URL starting 'file://'. Got {uri!r}")
        if parsed_url.netloc:
            raise ValueError(f"Expected a file:// URL without a netloc. Got {uri!r}")

        path = parsed_url.path.rstrip("/")
        (storage_root, _, bucket_name) = path.rpartition("/")
        super().__init__(bucket_name, storage_root, use_date_in_key_path=False)


class MemoryFileStore(BaseS3FileStore, Clearable):
    """
    For testing.
    """

    # Use a class-level dict so all instances share the same store.
    buffers: dict[str, dict[str, bytes]] = {}
    versioned_buffers: dict[str, dict[str, dict[str, bytes]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(bytes))
    )

    def __init__(self, bucket_name: str, **kwargs: Any) -> None:
        super().__init__(bucket_name, **kwargs)
        if bucket_name not in self.buffers:
            self.buffers[self.bucket_name] = {}

    def store_file(
        self,
        namespace: str,
        filename: str,
        contents: AnyStr | ReadableBinaryFile,
        content_type: str = "",
        overwrite: bool = False,
        metadata: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        key_path = self.make_key_path(namespace=namespace, filepath=filename)
        if key_path not in self.buffers[self.bucket_name] or overwrite:
            self.buffers[self.bucket_name][key_path] = _to_bytes(contents=contents)
        return self.bucket_name, key_path

    def store_versioned_file(
        self,
        key_path: str,
        contents: AnyStr | io.BytesIO,
        content_type: str = "",
    ) -> tuple[str, str, str]:
        version = str(uuid.uuid4())
        self.versioned_buffers[self.bucket_name][key_path][version] = _to_bytes(contents=contents)
        self.buffers[self.bucket_name][key_path] = _to_bytes(contents=contents)
        return self.bucket_name, key_path, version

    def store_filepath(
        self, namespace: str, filepath: str, overwrite: bool = False, dest_filepath: str = ""
    ) -> tuple[str, str]:
        with open(filepath, "rb") as f:
            if not dest_filepath:
                dest_filepath = os.path.basename(filepath)
            return self.store_file(namespace, dest_filepath, f.read(), overwrite=overwrite)

    def fetch_file_contents(self, key_path: str, version_id: str | None = None) -> bytes:
        if version_id:
            versioned_bucket = self.versioned_buffers[self.bucket_name]
            if key_path not in versioned_bucket or version_id not in versioned_bucket[key_path]:
                raise KeyDoesNotExist(
                    "Key with path %s and version %s was not found" % key_path % version_id
                )
            return versioned_bucket[key_path][version_id]
        else:
            bucket = self.buffers[self.bucket_name]
            if key_path not in bucket:
                raise KeyDoesNotExist("Key with path %s was not found" % key_path)
            return bucket[key_path]

    def get_key(self, key_path: str, version_id: str | None = None) -> S3Object:
        return S3Object(bucket_name=self.bucket_name, key=key_path, version_id=version_id)

    def get_file_type(self, key_path: str) -> str:
        mime = magic.Magic(mime=True)
        return mime.from_buffer(self.fetch_file_contents(key_path))

    def fetch_file(self, key_path: str, version_id: str | None = None) -> StorageFile:
        raw_stream = io.BytesIO(self.fetch_file_contents(key_path, version_id))
        return StreamingBody(raw_stream=raw_stream, content_length=files.size(raw_stream))

    def fetch_url(
        self,
        key_path: str,
        expires_in: int = 60,
        response_headers: dict[str, str] | None = None,
        version_id: str | None = None,
    ) -> str:
        return TEST_FETCH_URL

    def exists(self, key_path: str, as_file: bool = False) -> bool:
        # as_file is defined to match the interface of the other Stores, but is not obviously
        # applicable for keys in this medium
        bucket = self.buffers[self.bucket_name]
        return key_path in bucket

    def list_files(self, namespace: str = "") -> Iterable[str]:
        bucket = self.buffers[self.bucket_name]
        if not namespace:
            return bucket.keys()
        prefix = namespace
        if not prefix.endswith("/"):
            prefix += "/"

        # Using a list comprehension here makes a copy of the keys, which stops a RuntimeError
        # being thrown if the caller modifies something in the bucket.
        return [key for key in bucket if key.startswith(prefix)]

    def list_s3_keys(self, namespace: str = "") -> Iterable[S3Object]:
        return [self.get_key(path) for path in self.list_files(namespace=namespace)]

    def copy(self, *, s3_object: S3Object, destination: str) -> S3Object:
        bucket = self.buffers[self.bucket_name]
        bucket[destination] = bucket[s3_object.key]
        return S3Object(bucket_name=self.bucket_name, key=destination)

    def rename(self, *, s3_object: S3Object, destination: str) -> S3Object:
        assert s3_object.bucket_name == self.bucket_name
        bucket = self.buffers[self.bucket_name]
        if s3_object.key not in bucket:
            raise KeyDoesNotExist("Key with path %s was not found" % s3_object.key)
        if destination == s3_object.key:
            return s3_object  # No rename required
        bucket[destination] = bucket[s3_object.key]
        del bucket[s3_object.key]
        return S3Object(bucket_name=self.bucket_name, key=destination)

    def delete(self, *, s3_object: S3Object) -> None:
        bucket = self.buffers[self.bucket_name]
        del bucket[s3_object.key]

    def clear(self) -> None:
        """
        Deletes all files from all buckets, across all MemoryFileStore instances.
        """
        for bucket in self.buffers.values():
            bucket.clear()

    def generate_presigned_post(self, *, key_path: str, expires_in: int = 60) -> PreSignedPost:
        return PreSignedPost(
            # Resolves to a localdev/storage url
            url=reverse("fake-presigned-post-upload"),
            key=key_path,
            # These fields should be passed in the body of the upload POST request by clients that wish to upload a file
            # In production, they contain the signature used by AWS to verify the upload.
            # Locally, however, we return the bucket name and key path so that when the upload request is made
            # we know where to store the file.
            fields={"key_path": key_path, "bucket_name": self.bucket_name},
        )

    def get_size_in_bytes(self, *, s3_object: S3Object) -> int:
        assert s3_object.bucket_name == self.bucket_name
        return len(self.fetch_file_contents(s3_object.key))


def store(
    bucket_name: str, use_date_in_key_path: bool = True, set_acl_bucket_owner: bool = False
) -> BaseS3FileStore:
    """
    Return the appropriate storage instance for a given bucket.
    """
    storage_class = import_string(settings.STORAGE_BACKEND)
    return storage_class(
        bucket_name=bucket_name,
        use_date_in_key_path=use_date_in_key_path,
        set_acl_bucket_owner=set_acl_bucket_owner,
    )


def email_store(bucket_name: str) -> BaseS3FileStore:
    """
    Return the storage instance for email content.
    """
    store_class = import_string(settings.EMAIL_STORAGE_BACKEND)
    return store_class(bucket_name)


def fileserver_store(use_date_in_key_path: bool = True) -> BaseS3FileStore:
    return store(settings.S3_FILESERVER_BUCKET, use_date_in_key_path)


def flows_outbound_store() -> BaseS3FileStore:
    return store(settings.S3_PRODUCTION_FLOWS_OUTBOUND)


def user_documents(use_date_in_key_path: bool = True) -> BaseS3FileStore:
    """
    Return the user documents store.
    """
    return store(settings.S3_USER_DOCUMENTS_BUCKET, use_date_in_key_path=use_date_in_key_path)


def archive(use_date_in_key_path: bool = True) -> BaseS3FileStore:
    """
    Return the file archive store.
    """
    return store(settings.S3_ARCHIVE_BUCKET, use_date_in_key_path)


def support_documents_store() -> BaseS3FileStore:
    """
    Return the complaint related documents store.
    """
    store_class = import_string(settings.DOCUMENT_STORAGE_BACKEND)
    return store_class(settings.S3_SUPPORT_DOCUMENTS_BUCKET)


def voice_audio_statics_store() -> BaseS3FileStore:
    return store(settings.S3_VOICE_AUDIO_BUCKET, use_date_in_key_path=False)


def store_file_attachment(attachment: BinaryIO, namespace: str) -> tuple[str, str]:
    attachment_store = support_documents_store()
    contents = attachment.read()
    contents_hash = base64.urlsafe_b64encode(
        hashlib.blake2b(contents, digest_size=33).digest()
    ).decode("utf8")
    s3_bucket, s3_key = attachment_store.store_file(
        namespace=namespace,
        filename=os.path.join(contents_hash, attachment.name),
        contents=contents,
        overwrite=True,
    )
    return s3_bucket, s3_key


def outbound_flow_store() -> BaseS3FileStore:
    storage_class = import_string(settings.STORAGE_BACKEND)
    if storage_class == S3FileStore:
        return storage_class(
            bucket_name=settings.INTEGRATION_FLOW_S3_OUTBOUND_BUCKET, use_date_in_key_path=False
        )
    else:
        return storage_class(bucket_name=settings.INTEGRATION_FLOW_S3_OUTBOUND_BUCKET)


def from_uri(uri: str) -> FileSystemFileStore | S3SubdirectoryFileStore | MemoryFileStore:
    """
    :raises ValueError: if the URI does not contain a scheme for a supported storage system.
    """
    scheme = urllib.parse.urlparse(uri).scheme
    if scheme == "file":
        return FileSystemFileStore(uri)
    elif scheme == "s3":
        return S3SubdirectoryFileStore(uri)
    elif scheme == "memory":
        return MemoryFileStore(uri)
    else:
        raise ValueError(f"Expected a URL for a supported storage system. Got {uri!r}")


def user_media_store() -> BaseS3FileStore:
    """
    Returns the store where Kraken users can upload media such as audio files.
    """
    return store(settings.S3_USER_MEDIA_BUCKET)


def line_file_store() -> BaseS3FileStore:
    """
    Returns the store for inbound attachments from LINE (Ink).
    """
    return store(settings.LINE_INBOUND_ATTACHMENTS_BUCKET)


# Private


def _create_parent_directories(filepath: str) -> None:
    os.makedirs(os.path.dirname(filepath), mode=0o755, exist_ok=True)


def _to_stream(*, contents: AnyStr | ReadableBinaryFile) -> ReadableBinaryFile:
    """
    Return the given object expressed as an IO stream object.
    """
    if isinstance(contents, str):
        return io.BytesIO(contents.encode())
    elif isinstance(contents, bytes):
        return io.BytesIO(contents)
    return contents


def _to_bytes(*, contents: AnyStr | ReadableBinaryFile) -> bytes:
    """
    Return the given object expressed as a bytes object.
    """
    if isinstance(contents, str):
        return contents.encode()
    elif isinstance(contents, bytes):
        return contents
    return contents.read()
