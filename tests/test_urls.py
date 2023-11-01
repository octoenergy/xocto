import pytest

from xocto import urls


class TestPopURLQueryParam:
    def test_returns_modifed_url_and_popped_value(self):
        test_url = "https://localhost/x/y/x?a=1&b=2&c=3"
        (new_url, param) = urls.pop_url_query_param(test_url, "b")
        assert new_url == "https://localhost/x/y/x?a=1&c=3"
        assert param == "2"

    def test_returns_unmodified_url_for_missing_values(self):
        """
        Missing values return an unchanged URL and None as the attribute value.
        """
        test_url = "https://localhost/x/y/x?a=1&c=3"
        (new_url, param) = urls.pop_url_query_param(test_url, "b")
        assert new_url == test_url
        assert param is None

    def test_keeps_slashes_on_schema_only_urls(self):
        """
        URLs which have no path or netloc don't lose their slashes.

        Without special handling in `pop_url_query_param`, schema only URLs would lose their
        trailing slashes.

        >>> urllib.parse.urlunparse(urllib.parse.urlparse("schema://"))
        "schema:"

        Maybe that's a "valid" and "equivalent" URL but some libraries check for the "://" string
        to identify a URL. So keeping the trailing slashes is required for compatability. One
        specific library which has this behaviour is pyFilesystem where `open_fs("mem://")` opens
        an in-memory filesystem and `open_fs("mem:")` opens the `./mem:` directory.
        """
        test_url = "mem://?a=1"
        (new_url, param) = urls.pop_url_query_param(test_url, "a")
        assert new_url == "mem://"
        assert param == "1"

        test_url = "mem://"
        (new_url, param) = urls.pop_url_query_param(test_url, "a")
        assert new_url == test_url
        assert param is None

    def test_keeps_slashes_on_schema_only_urls_with_multiple_variables(self):
        """
        URLs which have no path or netloc don't lose their slashes.

        Without special handling in `pop_url_query_param`, schema only URLs would lose their
        trailing slashes.

        >>> urllib.parse.urlunparse(urllib.parse.urlparse("schema://"))
        "schema:"

        Maybe that's a "valid" and "equivalent" URL but some libraries check for the "://" string
        to identify a URL. So keeping the trailing slashes is required for compatability. One
        specific library which has this behaviour is pyFilesystem where `open_fs("mem://")` opens
        an in-memory filesystem and `open_fs("mem:")` opens the `./mem:` directory.
        """
        test_url = "mem://?a=1&b=2"
        (new_url, param) = urls.pop_url_query_param(test_url, "a")
        assert new_url == "mem://?b=2"
        assert param == "1"

        test_url = "mem://?b=2"
        (new_url, param) = urls.pop_url_query_param(test_url, "a")
        assert new_url == test_url
        assert param is None

    def test_raises_value_error_for_params_with_multiple_values(self):
        """
        Raises a ValueError if the requested param has multiple values.
        """
        with pytest.raises(ValueError):
            urls.pop_url_query_param("https://localhost/x/y/x?a=1&a=2", "a")


class TestParseFileDestinationFromURL:
    def test_handles_upload_dir_being_subdir_of_destination_dir(self):
        """
        Where `upload` starts with no dots or slashes it is a subdirs of the destination dir.

        In that case the returned URL is that of the destination and the upload path is given
        relative to that.
        """
        dest_url = "ftp://some_server/gas/destination?upload=nested/sub/dir"
        (fs_url, dest_path, upload_path) = urls.parse_file_destination_from_url(
            dest_url
        )

        assert fs_url == "ftp://some_server/gas/destination"
        assert dest_path == "."
        assert upload_path == "nested/sub/dir"

    def test_handles_destination_dir_being_subdir_of_upload_dir(self):
        """
        Where `upload` is ".." it is the parent of the destination dir.

        In that case the returned URL is that of the upload dir and the destination path is given
        relative to that.
        """
        dest_url = "ftp://some_server/gas/destination?upload=.."
        (fs_url, dest_path, upload_path) = urls.parse_file_destination_from_url(
            dest_url
        )

        assert fs_url == "ftp://some_server/gas"
        assert dest_path == "destination"
        assert upload_path == "."

    def test_handles_destination_dir_and_upload_dir_being_cousins(self):
        """
        Where `upload` starts "..", destination and upload dirs will have common ancestor.

        The destination and upload dir can be in different parts of the file system with neither
        being a sub dir of the other. In that case the returned URL is that of the nearest common
        ancestor between the two dirs and both paths are given relative to that.
        """
        dest_url = "ftp://some_server/gas/destination/dir?upload=../../upload/sub/dir"
        (fs_url, dest_path, upload_path) = urls.parse_file_destination_from_url(
            dest_url
        )

        assert fs_url == "ftp://some_server/gas"
        assert dest_path == "destination/dir"
        assert upload_path == "upload/sub/dir"

    def test_handles_absolute_upload_dir(self):
        """
        Where `upload` starts "/", it is an absolute path.

        In that case the upload dir is resolved relative to the root of the FS URL.
        """
        dest_url = "ftp://some_server/gas/destination?upload=/gas/upload"
        (fs_url, dest_path, upload_path) = urls.parse_file_destination_from_url(
            dest_url
        )

        assert fs_url == "ftp://some_server/gas"
        assert dest_path == "destination"
        assert upload_path == "upload"

    def test_setting_destination(self):
        url = "ftp://oeftp:blahblah@172.30.195.140?destination=MAM/TO_OE"
        result = urls.parse_file_destination_from_url(url)

        assert result == (
            "ftp://oeftp:blahblah@172.30.195.140",
            "MAM/TO_OE",
            ".",
        )

    def test_setting_destination_and_upload(self):
        url = "ftp://oeftp:blahblah@172.30.195.140?destination=MAM/TO_OE&upload=MAM/TO_OE/pending"
        result = urls.parse_file_destination_from_url(url)

        assert result == (
            "ftp://oeftp:blahblah@172.30.195.140",
            "MAM/TO_OE",
            "MAM/TO_OE/pending",
        )
