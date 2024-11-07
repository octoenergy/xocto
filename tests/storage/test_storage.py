import builtins
import datetime
import os
import shutil
import tempfile
from unittest import mock

import boto3
import moto
import pandas as pd
import pyarrow
import pytest
import time_machine
from django.test import override_settings
from pyarrow import parquet

from xocto.storage import s3_select, storage


@pytest.fixture
def mock_s3_bucket(mocker):
    with moto.mock_s3():
        bucket = boto3.resource("s3", region_name="us-east-1").create_bucket(
            Bucket="some-bucket"
        )

        client = boto3.client("s3")
        mocker.patch.object(
            storage.S3FileStore, "_get_boto_client", return_value=client, autospec=True
        )
        mocker.patch.object(
            storage.S3FileStore, "_get_boto_bucket", return_value=bucket, autospec=True
        )

        yield bucket


@pytest.fixture
def sample_dataframe():
    data = {"Name": ["Alice", "Bob", "Charlie"], "Age": [25, 30, 35]}
    return pd.DataFrame(data)


def test_memory_storage_used_during_tests():
    store = storage.store("some-bucket")
    assert isinstance(store, storage.MemoryFileStore)


class TestS3SubdirectoryFileStore:
    def test_make_key_path_raises_error_when_exceeds_max_length(self):
        s3_file_store = storage.S3SubdirectoryFileStore("s3://some-bucket/folder")
        with pytest.raises(RuntimeError):
            s3_file_store.make_key_path(namespace="x", filepath=("y" * 1025))

    @time_machine.travel("2021-09-10", tick=False)
    @pytest.mark.parametrize(
        "namespace,filepath,expected",
        [
            ("", "file.txt", "folder/2021/09/10/file.txt"),
            ("namespace", "file.txt", "folder/namespace/2021/09/10/file.txt"),
            (
                "namespace/sub-namespace",
                "file.txt",
                "folder/namespace/sub-namespace/2021/09/10/file.txt",
            ),
        ],
    )
    def test_make_key_path_with_use_date_in_key_path(
        self, namespace, filepath, expected
    ):
        s3_file_store = storage.S3SubdirectoryFileStore(
            "s3://some-bucket/folder?use_date_in_key_path=1"
        )
        assert (
            s3_file_store.make_key_path(namespace=namespace, filepath=filepath)
            == expected
        )

    @time_machine.travel("2021-09-10", tick=False)
    @pytest.mark.parametrize(
        "namespace,filepath,expected",
        [
            ("", "file.txt", "folder/file.txt"),
            ("namespace", "file.txt", "folder/namespace/file.txt"),
            (
                "namespace/sub-namespace",
                "file.txt",
                "folder/namespace/sub-namespace/file.txt",
            ),
        ],
    )
    def test_make_key_path_without_use_date_in_key_path(
        self, namespace, filepath, expected
    ):
        s3_file_store = storage.S3SubdirectoryFileStore("s3://some-bucket/folder")
        assert (
            s3_file_store.make_key_path(namespace=namespace, filepath=filepath)
            == expected
        )

    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_fetch_url(self, get_boto_client):
        store = storage.S3SubdirectoryFileStore("s3://some-bucket/folder")

        store.fetch_url("a/b.txt")

        # Should be called including the subdirectory path.
        get_boto_client.return_value.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "some-bucket", "Key": "folder/a/b.txt"},
            ExpiresIn=mock.ANY,
        )

    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_fetch_url_with_version(self, get_boto_client):
        store = storage.S3SubdirectoryFileStore("s3://some-bucket/folder")

        store.fetch_url("a/b.txt", version_id="some-version")

        # Should be called including the subdirectory path.
        get_boto_client.return_value.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": "some-bucket",
                "Key": "folder/a/b.txt",
                "VersionId": "some-version",
            },
            ExpiresIn=mock.ANY,
        )

    def test_list_s3_keys_page(self, mock_s3_bucket):
        store = storage.S3FileStore("some-bucket", use_date_in_key_path=False)
        filenames = [f"file_{i:04}.pdf" for i in range(105)]
        for filename in filenames:
            store.store_file(
                namespace="some/path/",
                filename=filename,
                contents=f"{filename} content",
            )
        expected = [
            storage.S3Object("some-bucket", f"path/{filename}")
            for filename in filenames
        ]

        # "file_00" excludes file_0100.pdf and above
        store = storage.S3SubdirectoryFileStore("s3://some-bucket/some")
        keys, next_token = store.list_s3_keys_page("path/file_00", max_keys=50)
        assert keys == expected[:50]
        assert next_token
        keys, next_token = store.list_s3_keys_page(
            "path/file_00", max_keys=50, next_token=next_token
        )
        assert keys == expected[50:100]
        assert not next_token

    @mock.patch.object(storage.S3FileStore, "_get_boto_bucket")
    def test_list_files(self, get_boto_bucket):
        get_boto_bucket.return_value = mock.Mock(
            **{
                "objects.filter.return_value": [
                    mock.Mock(key="folder/a/b/"),
                    mock.Mock(key="folder/a/b/foo.txt"),
                    mock.Mock(key="folder/a/b/bar.txt"),
                ]
            }
        )
        store = storage.S3SubdirectoryFileStore("s3://some-bucket/folder")

        assert list(store.list_files("a/b")) == [
            "a/b/foo.txt",
            "a/b/bar.txt",
        ]
        # Should be called including the subdirectory path.
        get_boto_bucket.return_value.objects.filter.assert_called_once_with(
            Prefix="folder/a/b"
        )

    @mock.patch.object(storage.S3FileStore, "_get_boto_bucket")
    def test_list_files_no_path(self, get_boto_bucket):
        get_boto_bucket.return_value = mock.Mock(
            **{
                "objects.filter.return_value": [
                    mock.Mock(key="folder/a/b/"),
                    mock.Mock(key="folder/a/b/foo.txt"),
                    mock.Mock(key="folder/a/b/bar.txt"),
                ]
            }
        )
        store = storage.S3SubdirectoryFileStore("s3://some-bucket")

        assert list(store.list_files(namespace="folder/a/b")) == [
            "folder/a/b/foo.txt",
            "folder/a/b/bar.txt",
        ]
        # Should be called including the subdirectory path.
        get_boto_bucket.return_value.objects.filter.assert_called_once_with(
            Prefix="folder/a/b"
        )

    @mock.patch.object(storage.S3FileStore, "_get_boto_object")
    def test_fetch_file_fetches_given_path(self, get_boto_object):
        """Fetch file should act on the given path.

        It should not add the subdirectory to the start of the key.
        """
        bucket_name = "some-bucket"
        directory = "folder"
        store = storage.S3SubdirectoryFileStore(f"s3://{bucket_name}/{directory}")
        base_key = "my/file.txt"

        full_key = store.get_key(base_key).key
        assert full_key == os.path.join(directory, base_key)

        store.fetch_file(full_key)

        get_boto_object.assert_called_once_with(
            s3_object=storage.S3Object(bucket_name=bucket_name, key=full_key)
        )


@mock.patch.object(storage, "_should_raise_error_on_existing_files", new=lambda: True)
class TestS3FileStore:
    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_stores_file_that_does_not_exist(
        self, get_boto_client, get_boto_object_for_key
    ):
        get_boto_object_for_key.side_effect = storage.KeyDoesNotExist
        store = storage.S3FileStore("bucket")

        store.store_file(
            namespace="files", filename="file.pdf", contents="some-content"
        )

        s3_client = get_boto_client.return_value
        s3_client.upload_fileobj.assert_called_once()

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_overwrites_file_that_does_exist(
        self, get_boto_client, get_boto_object_for_key
    ):
        get_boto_object_for_key.return_value = mock.Mock()
        store = storage.S3FileStore("bucket")

        store.store_file(
            namespace="files",
            filename="file.pdf",
            contents="some-content",
            overwrite=True,
        )

        s3_client = get_boto_client.return_value
        s3_client.upload_fileobj.assert_called_once()

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_raises_error_for_file_that_does_exist(
        self, get_boto_client, get_boto_object_for_key
    ):
        get_boto_object_for_key.return_value = mock.Mock()
        store = storage.S3FileStore("bucket")

        with pytest.raises(storage.FileExists):
            store.store_file(
                namespace="files", filename="file.pdf", contents="some-content"
            )

    @mock.patch.object(storage.S3FileStore, "_bucket_is_versioned")
    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_stores_file_in_versioned_bucket(
        self, get_boto_client, get_bucket_is_versioned
    ):
        bucket_name = "bucket"
        namespace = "files"
        filename = "file.pdf"
        object_version = "some-object-version"
        boto_client = mock.Mock()
        boto_client.put_object.return_value = {"VersionId": object_version}
        get_boto_client.return_value = boto_client
        get_bucket_is_versioned.return_value = True
        store = storage.S3FileStore(bucket_name, use_date_in_key_path=False)

        key_path = store.make_key_path(namespace=namespace, filepath=filename)
        result = store.store_versioned_file(key_path=key_path, contents="some-content")

        s3_client = get_boto_client.return_value
        s3_client.upload_fileobj.assert_not_called()
        s3_client.put_object.assert_called_once()
        assert result == (bucket_name, key_path, object_version)

    @mock.patch.object(storage.S3FileStore, "_bucket_is_versioned")
    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_raises_error_for_unversioned_bucket(
        self, get_boto_client, get_bucket_is_versioned
    ):
        get_boto_client.return_value = mock.Mock()
        get_bucket_is_versioned.return_value = False
        store = storage.S3FileStore("bucket", use_date_in_key_path=False)

        with pytest.raises(storage.BucketNotVersioned):
            store.store_versioned_file(
                key_path="files/file.pdf", contents="some-content"
            )

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_stores_filepath_that_does_not_exist(
        self, get_boto_client, get_boto_object_for_key
    ):
        get_boto_object_for_key.side_effect = storage.KeyDoesNotExist
        store = storage.S3FileStore("bucket")

        store.store_filepath(namespace="files", filepath="file.pdf")

        s3_client = get_boto_client.return_value
        s3_client.upload_file.assert_called_once()

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_overwrites_filepath_that_does_exist(
        self, get_boto_client, get_boto_object_for_key
    ):
        get_boto_object_for_key.return_value = mock.Mock()
        store = storage.S3FileStore("bucket")

        store.store_filepath(namespace="files", filepath="file.pdf", overwrite=True)

        s3_client = get_boto_client.return_value
        s3_client.upload_file.assert_called_once()

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_adds_metadata(self, get_boto_client, get_boto_object_for_key):
        get_boto_object_for_key.side_effect = storage.KeyDoesNotExist
        store = storage.S3FileStore("bucket")
        metadata = {"some": "metadata"}

        store.store_file(
            namespace="files",
            filename="file.pdf",
            contents="some-content",
            metadata=metadata,
        )

        s3_client = get_boto_client.return_value
        s3_client.upload_fileobj.assert_called_once()
        _, kwargs = s3_client.upload_fileobj.call_args
        assert kwargs["ExtraArgs"]["Metadata"] == metadata

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    @mock.patch.object(storage.S3FileStore, "_get_boto_client")
    def test_raises_error_for_filepath_that_does_exist(
        self, get_boto_client, get_boto_object_for_key
    ):
        get_boto_object_for_key.return_value = mock.Mock()
        store = storage.S3FileStore("bucket")

        with pytest.raises(storage.FileExists):
            store.store_filepath(namespace="files", filepath="file.pdf")

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    def test_exists_for_existing_key(self, get_boto_object_for_key):
        get_boto_object_for_key.return_value = mock.Mock()
        store = storage.S3FileStore("bucket")

        assert store.exists("a/b/c.pdf") is True

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    def test_exists_for_missing_key(self, get_boto_object_for_key):
        get_boto_object_for_key.side_effect = storage.KeyDoesNotExist
        store = storage.S3FileStore("bucket")

        assert store.exists("a/b/c.pdf") is False

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    def test_exists_as_file_for_file_key(self, get_boto_object_for_key):
        get_boto_object_for_key.return_value = mock.Mock(content_length=5)
        store = storage.S3FileStore("bucket")

        assert store.exists("a/b/c.pdf", as_file=True) is True

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    def test_exists_as_file_for_directory_key(self, get_boto_object_for_key):
        get_boto_object_for_key.return_value = mock.Mock(content_length=0)
        store = storage.S3FileStore("bucket")

        assert store.exists("a/b/c.pdf", as_file=True) is False

    @mock.patch.object(storage.S3FileStore, "_get_boto_bucket")
    def test_list_files(self, get_boto_bucket):
        get_boto_bucket.return_value = mock.Mock(
            **{
                "objects.filter.return_value": [
                    mock.Mock(key="a/b/"),
                    mock.Mock(key="a/b/foo.txt"),
                    mock.Mock(key="a/b/bar.txt"),
                ]
            }
        )
        store = storage.S3FileStore("bucket")

        assert list(store.list_files("a/b")) == [
            "a/b/foo.txt",
            "a/b/bar.txt",
        ]

    def test_s3_file_store_bucket_length(self):
        with pytest.raises(ValueError):
            storage.S3FileStore("")
        with pytest.raises(ValueError):
            storage.S3FileStore("ab")
        with pytest.raises(ValueError):
            storage.S3FileStore(
                "loremlipsumdolorsitametconsecteturadipiscingelitnullamtinciduntu"
            )
        # Should not raise
        storage.S3FileStore("abc")
        # Should not raise
        storage.S3FileStore(
            "loremlipsumdolorsitametconsecteturadipiscingelitnullamtincidunt"
        )

    def test_make_key_path_raises_error_when_exceeds_max_length(self):
        s3_file_store = storage.S3FileStore("some-bucket")
        with pytest.raises(RuntimeError):
            s3_file_store.make_key_path(namespace="x", filepath=("y" * 1025))

    @time_machine.travel("2021-09-10", tick=False)
    @pytest.mark.parametrize(
        "namespace,filepath,expected",
        [
            ("", "file.txt", "2021/09/10/file.txt"),
            ("namespace", "file.txt", "namespace/2021/09/10/file.txt"),
            (
                "namespace/sub-namespace",
                "file.txt",
                "namespace/sub-namespace/2021/09/10/file.txt",
            ),
        ],
    )
    def test_make_key_path_with_use_date_in_key_path(
        self, namespace, filepath, expected
    ):
        s3_file_store = storage.S3FileStore("some-bucket", use_date_in_key_path=True)
        assert (
            s3_file_store.make_key_path(namespace=namespace, filepath=filepath)
            == expected
        )

    @time_machine.travel("2021-09-10", tick=False)
    @pytest.mark.parametrize(
        "namespace,filepath,expected",
        [
            ("", "file.txt", "file.txt"),
            ("/", "file.txt", "file.txt"),
            ("namespace", "file.txt", "namespace/file.txt"),
            ("namespace/", "file.txt", "namespace/file.txt"),
            ("namespace/sub-namespace", "file.txt", "namespace/sub-namespace/file.txt"),
            (
                "namespace/sub-namespace/",
                "file.txt",
                "namespace/sub-namespace/file.txt",
            ),
        ],
    )
    def test_make_key_path_without_use_date_in_key_path(
        self, namespace, filepath, expected
    ):
        s3_file_store = storage.S3FileStore("some-bucket", use_date_in_key_path=False)
        assert (
            s3_file_store.make_key_path(namespace=namespace, filepath=filepath)
            == expected
        )

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    @mock.patch.object(storage, "open", new_callable=mock.mock_open)
    def test_download_file(self, mocked_open, get_boto_object_for_key):
        key_ = mock.Mock()
        get_boto_object_for_key.return_value = key_
        store = storage.S3FileStore("bucket")

        store.download_file("a/b/c.pdf")

        # The function should:
        # 1. Get the key
        assert get_boto_object_for_key.called
        # 2. Call boto's download_fileobj
        mock_local_file_obj = mocked_open.return_value.__enter__.return_value
        key_.download_fileobj.assert_called_once_with(Fileobj=mock_local_file_obj)
        mocked_open.assert_called_with("/tmp/bucket/a/b/c.pdf", "wb")

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    def test_download_file_fails_if_key_does_not_exist(self, get_boto_object_for_key):
        get_boto_object_for_key.side_effect = storage.KeyDoesNotExist
        store = storage.S3FileStore("bucket")

        with pytest.raises(storage.KeyDoesNotExist):
            store.download_file("a/b/c.pdf")

    def test_fetch_file_contents_using_s3_select_and_expect_output_in_csv_format(self):
        store = storage.S3FileStore("some-bucket")

        # Moto doesn't support faking a response from `select_object_content` that's why
        # we need a stub that can return us a fake response.
        boto_client = mock.Mock()
        store._get_boto_client = mock.Mock(return_value=boto_client)

        # Mock a fake response from S3 Select.
        # Note: Response has been heavily trimmed for the sake of this test.
        boto_client.select_object_content.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            # Payload returns an EventStream iterator, therefore mock it using a list.
            "Payload": iter([{"Records": {"Payload": b"Foo\nBar"}}]),
        }

        assert list(
            store.fetch_file_contents_using_s3_select(
                key_path="some_file.csv",
                # LIMIT 1 means we want to fetch a single row.
                raw_sql="""SELECT * FROM s3Object LIMIT 1""",
                input_serializer=s3_select.CSVInputSerializer(
                    FileHeaderInfo=s3_select.FileHeaderInfo.NONE
                ),
                output_serializer=s3_select.CSVOutputSerializer(),
                compression_type=s3_select.CompressionType.NONE,
            )
        ) == ["Foo\nBar"]

        boto_client.select_object_content.assert_called_with(
            Bucket="some-bucket",
            Key="some_file.csv",
            ExpressionType="SQL",
            Expression="SELECT * FROM s3Object LIMIT 1",
            InputSerialization={
                "CSV": {
                    "FileHeaderInfo": s3_select.FileHeaderInfo.NONE.value,
                    "RecordDelimiter": "\n",
                    "FieldDelimiter": ",",
                },
                "CompressionType": "NONE",
            },
            OutputSerialization={
                "CSV": {"FieldDelimiter": ",", "RecordDelimiter": "\n"}
            },
        )

    @mock.patch.object(storage.S3FileStore, "_get_boto_object_for_key")
    def test_get_last_modified(self, get_boto_object_for_key):
        k = mock.Mock()
        k.last_modified = datetime.datetime(2023, 1, 1, 8, 0, 0, 0)
        get_boto_object_for_key.return_value = k
        store = storage.S3FileStore("bucket")

        last_modified = store.get_last_modified("a/b/c.pdf")
        assert get_boto_object_for_key.called
        assert last_modified == k.last_modified
        assert type(last_modified) == datetime.datetime

    def test_fetch_file_contents_using_s3_select_and_expect_output_in_json_format(self):
        store = storage.S3FileStore("some-bucket")

        # Moto doesn't support faking a response from `select_object_content` that's why
        # we need a stub that can return us a fake response.
        boto_client = mock.Mock()
        store._get_boto_client = mock.Mock(return_value=boto_client)

        # Mock a fake response from S3 Select.
        # Note: Response has been heavily trimmed for the sake of this test.
        boto_client.select_object_content.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            # Payload returns an EventStream iterator, therefore mock it using a list.
            "Payload": iter([{"Records": {"Payload": b"Foo\nBar"}}]),
        }

        assert list(
            store.fetch_file_contents_using_s3_select(
                key_path="some_file.csv",
                # LIMIT 1 means we want to fetch a single row.
                raw_sql="""SELECT * FROM s3Object LIMIT 1""",
                input_serializer=s3_select.CSVInputSerializer(
                    FileHeaderInfo=s3_select.FileHeaderInfo.NONE
                ),
                output_serializer=s3_select.JSONOutputSerializer(),
                compression_type=s3_select.CompressionType.NONE,
            )
        ) == ["Foo\nBar"]

        boto_client.select_object_content.assert_called_with(
            Bucket="some-bucket",
            Key="some_file.csv",
            ExpressionType="SQL",
            Expression="SELECT * FROM s3Object LIMIT 1",
            InputSerialization={
                "CSV": {
                    "FileHeaderInfo": s3_select.FileHeaderInfo.NONE.value,
                    "RecordDelimiter": "\n",
                    "FieldDelimiter": ",",
                },
                "CompressionType": "NONE",
            },
            OutputSerialization={"JSON": {"RecordDelimiter": "\n"}},
        )

    def test_fetch_file_contents_using_s3_select_with_parquet_as_input(self):
        store = storage.S3FileStore("some-bucket")

        # Moto doesn't support faking a response from `select_object_content` that's why
        # we need a stub that can return us a fake response.
        boto_client = mock.Mock()
        store._get_boto_client = mock.Mock(return_value=boto_client)

        # Mock a fake response from S3 Select.
        # Note: Response has been heavily trimmed for the sake of this test.
        boto_client.select_object_content.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            # Payload returns an EventStream iterator, therefore mock it using a list.
            "Payload": iter([{"Records": {"Payload": b"Foo\nBar"}}]),
        }

        assert list(
            store.fetch_file_contents_using_s3_select(
                key_path="some_file.parquet",
                # LIMIT 1 means we want to fetch a single row.
                raw_sql="""SELECT * FROM s3Object LIMIT 1""",
                input_serializer=s3_select.ParquetInputSerializer(),
                output_serializer=s3_select.JSONOutputSerializer(),
            )
        ) == ["Foo\nBar"]

        boto_client.select_object_content.assert_called_with(
            Bucket="some-bucket",
            Key="some_file.parquet",
            ExpressionType="SQL",
            Expression="SELECT * FROM s3Object LIMIT 1",
            InputSerialization={"Parquet": {}},
            OutputSerialization={"JSON": {"RecordDelimiter": "\n"}},
        )

    def test_fetch_file_contents_using_s3_select_with_parquet_fails_with_scan_range(
        self,
    ):
        store = storage.S3FileStore("some-bucket")

        # Moto doesn't support faking a response from `select_object_content` that's why
        # we need a stub that can return us a fake response.
        boto_client = mock.Mock()
        store._get_boto_client = mock.Mock(return_value=boto_client)

        # Mock a fake response from S3 Select.
        # Note: Response has been heavily trimmed for the sake of this test.
        boto_client.select_object_content.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
            # Payload returns an EventStream iterator, therefore mock it using a list.
            "Payload": iter([{"Records": {"Payload": b"Foo\nBar"}}]),
        }

        with pytest.raises(ValueError) as error:
            list(
                store.fetch_file_contents_using_s3_select(
                    key_path="some_file.parquet",
                    raw_sql="""SELECT * FROM s3Object LIMIT 1""",
                    input_serializer=s3_select.ParquetInputSerializer(),
                    output_serializer=s3_select.JSONOutputSerializer(),
                    scan_range=s3_select.ScanRange(0, 100),
                )
            )

        assert (
            str(error.value)
            == "The scan_range parameter is not supported for parquet files"
        )

    @pytest.mark.parametrize("expected_error_code", [400, 401, 403, 500])
    def test_fetch_file_contents_using_s3_select_raises_errors(
        self, expected_error_code
    ):
        store = storage.S3FileStore("some-bucket")

        boto_client = mock.Mock()
        store._get_boto_client = mock.Mock(return_value=boto_client)

        # Mock a fake error response from S3 Select.
        boto_client.select_object_content.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": expected_error_code},
        }

        with pytest.raises(
            storage.S3SelectUnexpectedResponse,
            match="Received invalid response from S3 Select",
        ):
            file_contents = list(
                store.fetch_file_contents_using_s3_select(
                    key_path="some_file.csv",
                    raw_sql="""SELECT * FROM s3Object LIMIT 1""",
                    input_serializer=s3_select.CSVInputSerializer(
                        FileHeaderInfo=s3_select.FileHeaderInfo.NONE
                    ),
                    output_serializer=s3_select.CSVOutputSerializer(),
                    compression_type=s3_select.CompressionType.NONE,
                )
            )
            assert len(file_contents) == 0


class TestMemoryFileStore:
    def setup_method(self):
        # Reset MemoryFileStore between test cases to keep them isolated
        self.store = storage.MemoryFileStore("bucket", use_date_in_key_path=False)
        self.store.clear()

    def test_store_and_fetch(self):
        __, path = self.store.store_file(
            namespace="x", filename="test.pdf", contents=b"test_store_and_fetch"
        )

        contents = self.store.fetch_file_contents(path)
        assert contents == b"test_store_and_fetch"

    def test_versioned_store_and_fetch(self):
        key_path = "x/test.pdf"
        __, path, first_version = self.store.store_versioned_file(
            key_path=key_path, contents="first"
        )
        __, path, latest_version = self.store.store_versioned_file(
            key_path=key_path, contents="last_contents"
        )

        contents = self.store.fetch_file_contents(path, first_version)
        assert contents == b"first"
        contents = self.store.fetch_file_contents(path, latest_version)
        assert contents == b"last_contents"
        contents = self.store.fetch_file_contents(path)
        assert contents == b"last_contents"

    @mock.patch.object(
        builtins, "open", mock.mock_open(read_data=b"test_store_filepath")
    )
    def test_store_filepath(self, *mocks):
        bucket_name, path = self.store.store_filepath(
            namespace="x", filepath="test.pdf"
        )

        assert bucket_name == "bucket"
        assert path == "x/test.pdf"
        contents = self.store.fetch_file_contents(path)
        assert contents == b"test_store_filepath"

    @mock.patch.object(
        builtins,
        "open",
        mock.mock_open(read_data=b"test_store_filepath_with_dest_filepath"),
    )
    def test_store_filepath_with_dest_filepath(self, *mocks):
        bucket_name, path = self.store.store_filepath(
            namespace="x",
            filepath="test.pdf",
            dest_filepath="foo.pdf",
        )

        assert bucket_name == "bucket"
        assert path == "x/foo.pdf"
        contents = self.store.fetch_file_contents(path)
        assert contents == b"test_store_filepath_with_dest_filepath"

    def test_fetch_nonexistent(self):
        with pytest.raises(storage.KeyDoesNotExist):
            self.store.fetch_file_contents("belleview/marshlands")

    def test_list_s3_keys_page(self):
        filenames = [f"file_{i:04}.pdf" for i in range(105)]
        for filename in filenames:
            self.store.store_file(
                namespace="", filename=filename, contents=f"{filename} content"
            )

        expected = [storage.S3Object("bucket", filename) for filename in filenames]

        # list_s3_keys_page wraps list_s3_keys by default so lists all keys so a next_token isn't
        # needed
        keys, next_token = self.store.list_s3_keys_page("")
        assert keys == expected
        assert not next_token

    def test_list_files(self):
        self.store.store_file(
            namespace="x", filename="test.pdf", contents=b"test_list_files_1"
        )
        self.store.store_file(
            namespace="x", filename="test2.pdf", contents=b"test_list_files_2"
        )
        self.store.store_file(
            namespace="y", filename="test3.pdf", contents=b"test_list_files_3"
        )

        listings = self.store.list_files(namespace="x")
        assert list(listings) == ["x/test.pdf", "x/test2.pdf"]

    def test_list_files_without_namespace(self):
        self.store.store_file(
            namespace="x", filename="test.pdf", contents=b"test_list_files_1"
        )
        self.store.store_file(
            namespace="x", filename="test2.pdf", contents=b"test_list_files_2"
        )
        self.store.store_file(
            namespace="y", filename="test3.pdf", contents=b"test_list_files_3"
        )

        listings = self.store.list_files()
        assert list(listings) == ["x/test.pdf", "x/test2.pdf", "y/test3.pdf"]

    def test_download_file(self):
        self.store.store_file(
            namespace="mem", filename="test.pdf", contents=b"test_download_file"
        )

        file = self.store.download_file("mem/test.pdf")
        assert file.name == "/tmp/bucket/mem/test.pdf"
        try:
            with open(file.name, "rb") as f:
                assert f.read() == b"test_download_file"
        finally:
            os.remove(file.name)


class TestLocalFileStore:
    @classmethod
    def setup_class(cls):
        cls.sample_dataframe = pd.DataFrame(
            {"Name": ["Alice", "Bob", "Charlie"], "Age": [25, 30, 35]}
        )

        cls.csv_data = """Name,Age
                        Alice,25
                        Bob,30
                        Charlie,35
                       """

    def test_store_and_fetch(self):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir, use_date_in_key_path=False)

            __, path = store.store_file(
                namespace="x", filename="test.pdf", contents="hello"
            )

            contents = store.fetch_file_contents(path)
            assert contents == b"hello"

            # Test that fetching with the key path returned from `make_key_path` works as expected
            path = store.make_key_path(namespace="x", filepath="test.pdf")
            assert store.fetch_file_contents(path) == b"hello"

    def test_versioned_store_and_fetch(self):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir, use_date_in_key_path=False)

            key_path = "x/test.pdf"
            __, path, first_version = store.store_versioned_file(
                key_path=key_path, contents="first"
            )
            __, path, latest_version = store.store_versioned_file(
                key_path=key_path, contents="last_contents"
            )

            contents = store.fetch_file_contents(path, first_version)
            assert contents == b"first"
            contents = store.fetch_file_contents(path, latest_version)
            assert contents == b"last_contents"
            contents = store.fetch_file_contents(path)
            assert contents == b"last_contents"

            # Test that fetching with the key path returned from `make_key_path` works as expected
            path = store.make_key_path(namespace="x", filepath="test.pdf")
            assert store.fetch_file_contents(path, first_version) == b"first"

    def test_store_and_fetch_datepath(self):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir, use_date_in_key_path=True)

            __, path = store.store_file(
                namespace="x", filename="test.pdf", contents="hello"
            )

            contents = store.fetch_file_contents(path)
            assert contents == b"hello"

            # Test that fetching with the key path returned from `make_key_path` works as expected
            path = store.make_key_path(namespace="x", filepath="test.pdf")
            assert store.fetch_file_contents(path) == b"hello"

    def test_get_last_modified(self):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir, use_date_in_key_path=True)

            __, path = store.store_file(
                namespace="x", filename="test.pdf", contents="hello"
            )

            last_modified = store.get_last_modified(path)
            assert last_modified is not None
            assert type(last_modified) == datetime.datetime

    @mock.patch.object(shutil, "copyfile")
    @mock.patch.object(os.path, "exists", return_value=False)
    def test_store_filepath(self, mock_exists, mock_copyfile):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir, use_date_in_key_path=False)
            bucket_name, path = store.store_filepath(namespace="x", filepath="test.pdf")

        expected_store_filepath = os.path.join(tdir, "bucket", "x", "test.pdf")
        assert bucket_name == "bucket"
        assert path == expected_store_filepath
        mock_exists.assert_called_with(expected_store_filepath)
        mock_copyfile.assert_called_once_with("test.pdf", expected_store_filepath)

    @mock.patch.object(shutil, "copyfile")
    @mock.patch.object(os.path, "exists", return_value=False)
    def test_store_filepath_with_dest_filepath(self, mock_exists, mock_copyfile):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir, use_date_in_key_path=False)
            bucket_name, path = store.store_filepath(
                namespace="x", filepath="test.pdf", dest_filepath="foo.pdf"
            )

        expected_store_filepath = os.path.join(tdir, "bucket", "x", "foo.pdf")
        assert bucket_name == "bucket"
        assert path == expected_store_filepath
        mock_exists.assert_called_with(expected_store_filepath)
        mock_copyfile.assert_called_once_with("test.pdf", expected_store_filepath)

    def test_exists(self):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir, use_date_in_key_path=False)

            __, path = store.store_file(
                namespace="x", filename="test.pdf", contents="hello"
            )

            assert store.exists(path) is True

    def test_exists_datepath(self):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir, use_date_in_key_path=True)

            __, path = store.store_file(
                namespace="x", filename="test.pdf", contents="hello"
            )

            assert store.exists(path) is True

    def test_exists_for_missing_key(self):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir)

            assert store.exists("missing_file.pdf") is False

    def test_fetch_nonexistent(self):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir)

            with pytest.raises(storage.KeyDoesNotExist):
                store.fetch_file_contents("belleview/marshlands")

    def test_list_files(self):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir, use_date_in_key_path=False)

            __, path = store.store_file(
                namespace="x", filename="test.pdf", contents="hello"
            )
            __, path = store.store_file(
                namespace="x", filename="test2.pdf", contents="goodbye"
            )
            __, path = store.store_file(
                namespace="y", filename="test3.pdf", contents="goodbye"
            )

            listings = store.list_files(namespace="x")
            assert sorted(list(listings)) == ["x/test.pdf", "x/test2.pdf"]

    def test_download_file(self):
        with tempfile.TemporaryDirectory() as tdir:
            store = storage.LocalFileStore("bucket", tdir, use_date_in_key_path=False)
            __, path = store.store_file(
                namespace="x", filename="test.pdf", contents=b"hello"
            )

            file = store.download_file("x/test.pdf")

        assert file.name == tdir + "/x/test.pdf"

    @override_settings(MEDIA_ROOT="/media-root/", MEDIA_URL="/media-url/")
    def test_fetch_url(self):
        store = storage.LocalFileStore("bucket-name")
        fetch_url = store.fetch_url("some/key")
        assert fetch_url == "/media-url/bucket-name/some/key"

    @override_settings(MEDIA_ROOT="/media-root/", MEDIA_URL="/media-url/")
    def test_fetch_url_with_version(self):
        store = storage.LocalFileStore("bucket-name")
        fetch_url = store.fetch_url("some/key", version_id="some-version")
        assert fetch_url == "/media-url/bucket-name/some/some-version/key"

    @override_settings(MEDIA_ROOT="/media-root/", MEDIA_URL="/media-url/")
    def test_fetch_url_with_key_path_containing_root_and_bucket(self):
        store = storage.LocalFileStore("bucket-name")
        fetch_url = store.fetch_url("/media-root/bucket-name/some/key")
        assert fetch_url == "/media-url/bucket-name/some/key"

    @mock.patch.object(storage.LocalFileStore, "_filepath_for_key_path")
    def test_fetch_csv_file_contents_using_s3_select(self, mock__filepath_for_key_path):
        store = storage.LocalFileStore("my_bucket")
        mock_csv_data = "Name,Age\nAlice,25\nBob,30\nCharlie,35\n"
        with tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".csv"
        ) as tmp_csv_file:
            tmp_csv_file.write(mock_csv_data)
            tmp_csv_file_path = tmp_csv_file.name

        mock__filepath_for_key_path.return_value = tmp_csv_file_path

        input_serializer = s3_select.CSVInputSerializer(
            FileHeaderInfo=s3_select.FileHeaderInfo.USE, FieldDelimiter=","
        )
        output_serializer = s3_select.JSONOutputSerializer()

        results = list(
            store.fetch_file_contents_using_s3_select(
                key_path="my_csv_file.csv",
                raw_sql="SELECT * FROM s3object",
                input_serializer=input_serializer,
                output_serializer=output_serializer,
            )
        )

        expected_results = [
            '{"Name":"Alice","Age":25}\n'
            '{"Name":"Bob","Age":30}\n'
            '{"Name":"Charlie","Age":35}\n'
        ]
        assert results == expected_results

    @mock.patch.object(storage.LocalFileStore, "_filepath_for_key_path")
    def test_fetch_csv_file_contents_using_s3_select_and_where_statement(
        self, mock__filepath_for_key_path
    ):
        store = storage.LocalFileStore("my_bucket")
        mock_csv_data = "Name,Age\nAlice,25\nBob,30\nCharlie,35\n"
        with tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".csv"
        ) as tmp_csv_file:
            tmp_csv_file.write(mock_csv_data)
            tmp_csv_file_path = tmp_csv_file.name

        mock__filepath_for_key_path.return_value = tmp_csv_file_path

        input_serializer = s3_select.CSVInputSerializer(
            FileHeaderInfo=s3_select.FileHeaderInfo.USE, FieldDelimiter=","
        )
        output_serializer = s3_select.JSONOutputSerializer()

        results = list(
            store.fetch_file_contents_using_s3_select(
                key_path="my_csv_file.csv",
                raw_sql="SELECT * FROM s3object WHERE Name = 'Alice'",
                input_serializer=input_serializer,
                output_serializer=output_serializer,
            )
        )

        expected_results = ['{"Name":"Alice","Age":25}\n']
        assert results == expected_results

    @mock.patch.object(storage.LocalFileStore, "_filepath_for_key_path")
    def test_fetch_parquet_file_contents_using_s3_select(
        self, mock__filepath_for_key_path
    ):
        store = storage.LocalFileStore("my_bucket")
        mock_data = {"Name": ["Alice", "Bob", "Charlie"], "Age": [25, 30, 35]}
        df = pd.DataFrame(mock_data)

        with tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".parquet"
        ) as tmp_parquet_file:
            parquet_file_path = tmp_parquet_file.name

            table = pyarrow.Table.from_pandas(df)
            parquet.write_table(table, parquet_file_path)

            mock__filepath_for_key_path.return_value = parquet_file_path

            input_serializer = s3_select.ParquetInputSerializer()
            output_serializer = s3_select.JSONOutputSerializer()

            results = list(
                store.fetch_file_contents_using_s3_select(
                    key_path="my_parquet_file.parquet",
                    raw_sql="SELECT * FROM s3object",
                    input_serializer=input_serializer,
                    output_serializer=output_serializer,
                )
            )

            expected_results = [
                '{"Name":"Alice","Age":25}\n'
                '{"Name":"Bob","Age":30}\n'
                '{"Name":"Charlie","Age":35}\n'
            ]
            assert results == expected_results

    def test_fetch_nonexistent_file_with_s3_select(self):
        input_serializer = s3_select.CSVInputSerializer(s3_select.FileHeaderInfo.USE)
        output_serializer = s3_select.JSONOutputSerializer()
        store = storage.LocalFileStore("my_bucket")

        with pytest.raises(FileNotFoundError):
            list(
                store.fetch_file_contents_using_s3_select(
                    key_path="nonexistent_file.csv",
                    raw_sql="SELECT * FROM s3Object",
                    input_serializer=input_serializer,
                    output_serializer=output_serializer,
                )
            )

    def test_fetch_file_with_s3_select_scan_range_raises_error(self):
        input_serializer = s3_select.CSVInputSerializer(s3_select.FileHeaderInfo.USE)
        output_serializer = s3_select.JSONOutputSerializer()
        store = storage.LocalFileStore("my_bucket")

        with pytest.raises(NotImplementedError):
            list(
                store.fetch_file_contents_using_s3_select(
                    key_path="nonexistent_file.csv",
                    raw_sql="SELECT * FROM s3Object",
                    input_serializer=input_serializer,
                    output_serializer=output_serializer,
                    scan_range=s3_select.ScanRange(0, 100),
                )
            )

    @mock.patch.object(storage.LocalFileStore, "_filepath_for_key_path")
    def test_json_output_unsupported_record_separator_raises_exception(
        self, mock__filepath_for_key_path
    ):
        store = storage.LocalFileStore("my_bucket")
        mock_data = {"Name": ["Alice", "Bob", "Charlie"], "Age": [25, 30, 35]}
        df = pd.DataFrame(mock_data)

        with tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".parquet"
        ) as tmp_parquet_file:
            parquet_file_path = tmp_parquet_file.name

            table = pyarrow.Table.from_pandas(df)
            parquet.write_table(table, parquet_file_path)

            mock__filepath_for_key_path.return_value = parquet_file_path

            input_serializer = s3_select.ParquetInputSerializer()
            output_serializer = s3_select.JSONOutputSerializer("\r")

            with pytest.raises(NotImplementedError):
                list(
                    store.fetch_file_contents_using_s3_select(
                        key_path="my_parquet_file.parquet",
                        raw_sql="SELECT * FROM s3object",
                        input_serializer=input_serializer,
                        output_serializer=output_serializer,
                    )
                )

    def test_output_csv_with_serializer_quoting_always(self):
        store = storage.LocalFileStore("my_bucket")
        serializer = s3_select.CSVOutputSerializer(
            QuoteFields=s3_select.QuoteFields.ALWAYS
        )
        result = store.output_csv_with_serializer(
            df=self.sample_dataframe, output_serializer=serializer
        )
        expected = '"Name","Age"\n"Alice","25"\n"Bob","30"\n"Charlie","35"\n'
        assert result == expected

    def test_output_csv_with_serializer_quoting_as_needed(self):
        sample_dataframe = pd.DataFrame(
            {"Name": ["Ali,ce", "Bob", "Charlie"], "Age": [25, 30, 35]}
        )
        store = storage.LocalFileStore("my_bucket")
        serializer = s3_select.CSVOutputSerializer(
            QuoteFields=s3_select.QuoteFields.ASNEEDED
        )
        result = store.output_csv_with_serializer(
            df=sample_dataframe, output_serializer=serializer
        )
        expected = 'Name,Age\n"Ali,ce",25\nBob,30\nCharlie,35\n'
        assert result == expected

    def test_output_csv_with_serializer_custom_delimiter(self):
        store = storage.LocalFileStore("my_bucket")
        serializer = s3_select.CSVOutputSerializer(FieldDelimiter=";")
        result = store.output_csv_with_serializer(
            df=self.sample_dataframe, output_serializer=serializer
        )
        expected = "Name;Age\nAlice;25\nBob;30\nCharlie;35\n"
        assert result == expected

    def test_output_csv_with_serializer_custom_escapechar(self):
        store = storage.LocalFileStore("my_bucket")
        serializer = s3_select.CSVOutputSerializer(QuoteEscapeCharacter="\\")
        result = store.output_csv_with_serializer(
            df=self.sample_dataframe, output_serializer=serializer
        )
        expected = "Name,Age\nAlice,25\nBob,30\nCharlie,35\n"
        assert result == expected

    def test_output_csv_with_serializer_custom_record_delimiter(self):
        store = storage.LocalFileStore("my_bucket")
        serializer = s3_select.CSVOutputSerializer(RecordDelimiter="|")
        result = store.output_csv_with_serializer(
            df=self.sample_dataframe, output_serializer=serializer
        )
        expected = "Name,Age|Alice,25|Bob,30|Charlie,35|"
        assert result == expected

    def test_read_csv_with_serializer(self):
        store = storage.LocalFileStore("my_bucket")

        with tempfile.NamedTemporaryFile(
            delete=False, mode="w", suffix=".csv"
        ) as tmp_csv_file:
            tmp_csv_file.write(self.csv_data)
            tmp_csv_file_path = tmp_csv_file.name
        input_serializer = s3_select.CSVInputSerializer(s3_select.FileHeaderInfo.USE)
        result = store.read_csv_with_serializer(
            csv_file_path=tmp_csv_file_path,
            csv_input_serializer=input_serializer,
        )
        assert isinstance(result, pd.DataFrame)

    def test_query_dataframe_with_sql(self):
        data = {
            "string_column": ["A", "B", "C"],
            "array_column": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        }
        dummy_df = pd.DataFrame(data)

        store = storage.LocalFileStore("my_bucket")
        raw_sql = "SELECT * FROM S3Object WHERE string_column = 'A'"

        result_df = store.query_dataframe_with_sql(raw_sql, dummy_df)

        assert result_df.shape == (1, 2)

        assert result_df["string_column"][0] == "A"
        assert tuple(result_df["array_column"][0]) == (
            1,
            2,
            3,
        )

    def test_query_dataframe_with_sql_with_capitalised_object_in_query(self):
        dummy_df = pd.DataFrame(self.sample_dataframe)

        store = storage.LocalFileStore("my_bucket")
        raw_sql = "SELECT * FROM s3OBJeCT WHERE Name = 'Alice'"

        result_df = store.query_dataframe_with_sql(raw_sql, dummy_df)

        assert result_df.shape == (1, 2)

        assert result_df["Name"][0] == "Alice"
        assert result_df["Age"][0] == 25


class TestFromUri:
    def test_adds_set_acl_bucket_owner_if_in_s3_url(self):
        store = storage.from_uri("s3://some-bucket/a-prefix/?set_acl_bucket_owner")
        assert store.set_acl_bucket_owner

    def test_does_not_set_acl_bucket_owner_if_not_in_s3_url(self):
        store = storage.from_uri("s3://some-bucket/a-prefix/")
        assert not store.set_acl_bucket_owner

    def test_does_not_set_acl_bucket_owner_if_in_s3_url_path(self):
        store = storage.from_uri("s3://some-bucket/set_acl_bucket_owner/")
        assert not store.set_acl_bucket_owner

    def test_adds_use_date_in_key_path_if_in_s3_url(self):
        store = storage.from_uri("s3://some-bucket/a-prefix/?use_date_in_key_path")
        assert store.date_in_key_path

    def test_does_not_use_date_in_key_path_if_not_in_s3_url(self):
        store = storage.from_uri("s3://some-bucket/a-prefix/")
        assert not store.date_in_key_path

    def test_sets_correct_bucket_and_path(self):
        store = storage.from_uri("s3://some-bucket/a-prefix/")
        assert store.bucket_name == "some-bucket"
        assert store.path == "a-prefix"
