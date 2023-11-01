from __future__ import annotations

import os
from urllib import parse


def pop_url_query_param(url: str, key: str) -> tuple[str, str | None]:
    """
    Pop one query string value off a URL returning both the modified URL and popped value.

    E.g.
    >>> pop_url_query_param('https://localhost/x/y/x?a=1&b=2&c=3', 'b')
    ('https://localhost/x/y/x?a=1&c=3', '2')

    Missing values return an unchanged URL and None as the attribute value.
    >>> pop_url_query_param('https://localhost/x/y/x?a=1&b=2&c=3', 'd')
    ('https://localhost/x/y/x?a=1&b=2&c=3', None)

    Raises a ValueError if the requested param has multiple values.
    >>> pop_url_query_param('https://localhost/x/y/x?a=1&a=2', 'a')
    Traceback (most recent call last):
        ...
    ValueError: ...
    """
    parsed_url = parse.urlparse(url)
    query_dict = parse.parse_qs(
        parsed_url.query, keep_blank_values=True, errors="strict"
    )
    query_value_list = query_dict.pop(key, (None,))
    if len(query_value_list) != 1:
        raise ValueError(f"Cannot pop multi-valued query param: Key {key!r} in {url!r}")
    modified_url = parsed_url._replace(query=parse.urlencode(query_dict, doseq=True))
    resulting_url = parse.urlunparse(modified_url)
    resulting_url = _fix_url_scheme(old_url=url, new_url=resulting_url)
    return resulting_url, query_value_list[0]


def parse_file_destination_from_url(url: str) -> tuple[str, str, str]:
    """
    Split a destination URL into a pyFileSystem URL, destination path and upload path.

    A common problem when uploading files to file-systems like FTP or SFTP is that uploads are not
    atomic. That means that when uploading a file for another party to download then is a chance
    that they will see a partially uploaded file. To avoid that problem it's common to upload the
    file to an intermediary (upload) path and then move it to the final (destination) path. That
    approach works because while the upload is not atomic, the server-side rename/move is.

    When configuring pyFileSystems it's nice to use a single URL rather than separate values for
    HOST, PORT, PATH, USERNAME, PASSWORD, etc. This function extends those ergonomics by allowing a
    single URL to specific both the upload and final destination locations.

    The "Destination URLs" taken by this function are pyFileSystem URLs describing a directory into
    which a file should be written. This URL can have an optional `upload` key in the query string.
    If that key exists then is is a path to a directory relative to the main URL. This indicates
    where the file should be uploaded before being moved to the final destination

    This function parses the given "destination URL" into three parts.
    - A pyFileSystem URL which contains both the destination and upload directories
    - The destination path (Relative to the returned FS URL)
    - The upload path (Relative to the returned FS URL)

    pyFileSystem filesystems are sandboxed, which means we can't escape them using `..` or similar.
    That means that we have to ensure that the returned URL contains both the destination and
    upload paths. That means modifying the URL path to be the common ancestor of the two dirs.

    The `upload` dir can be a subdir of the destination` ...
    >>> parse_file_destination_from_url('ftp://some_server/dir/destination?upload=temp')
    'ftp://some_server/dir/destination', '.', 'temp')

    ... or a parent dir ...
    >>> parse_file_destination_from_url('ftp://some_server/dir/destination?upload=..')
    ('ftp://some_server/dir', 'destination', '.')

    ... Or a sibling ..
    >>> parse_file_destination_from_url('ftp://some_server/dir/destination?upload=../temp')
    ('ftp://some_server/dir', 'destination', 'temp')

    ... Or an absolute path.
    >>> parse_file_destination_from_url('ftp://some_server/dir/destination?upload=/temp')
    ('ftp://some_server/', 'dir/destination', 'temp')

    If the upload path is not given then it's assumed that the file should be directly uploaded to
    the destination dir.
    >>> parse_file_destination_from_url('ftp://some_server/dir/destination')
    ('ftp://some_server/dir/destination', '.', '.')

    A destination path can be specified with a `destination` query key. This is useful if you need
    to force a certain pyFileSystem URL rather than using the full path to the final `destination`.
    (c.f. the above example)
    >>> parse_file_destination_from_url('ftp://some_server/?destination=dir/destination')
    ('ftp://some_server/', 'dir/destination', '.')

    If both `destination` and `upload` query key are specified then they are both used. This is
    useful if you need to force a certain pyFileSystem URL rather than finding the nearest common
    ancestor of `destination` and `upload`
    >>> parse_file_destination_from_url('ftp://some_server/?destination=dir/destination&upload=dir/destination/temp')
    ('ftp://some_server/', 'dir/destination', 'dir/destination/temp')
    """
    (url, url_relative_upload_path) = pop_url_query_param(url, key="upload")
    (url, url_relative_destination_path) = pop_url_query_param(url, key="destination")

    if not url_relative_upload_path and url_relative_destination_path:
        return url, url_relative_destination_path, "."
    elif url_relative_upload_path and url_relative_destination_path:
        # Explicitly set destination and upload paths means we should use them without finding defaults.
        return url, url_relative_destination_path, url_relative_upload_path
    elif not url_relative_upload_path:
        return url, ".", "."
    else:
        parsed_url = parse.urlparse(url)
        destination_path = parsed_url.path
        upload_path = os.path.abspath(
            os.path.join(destination_path, url_relative_upload_path)
        )
        common_path = os.path.commonpath((destination_path, upload_path))
        new_url = parse.urlunparse(parsed_url._replace(path=common_path))
        new_url = _fix_url_scheme(old_url=url, new_url=new_url)
        upload_path = os.path.abspath(
            os.path.join(destination_path, url_relative_upload_path)
        )
        rel_destination_path = os.path.relpath(destination_path, common_path)
        rel_upload_path = os.path.relpath(upload_path, common_path)
        return new_url, rel_destination_path, rel_upload_path


# Private


def _fix_url_scheme(*, old_url: str, new_url: str) -> str:
    """
    Restore '://' to a URL where urlunparse(urlparse(url)) has removed it.

    Strictly speaking URLs which don't have a username, password or host don't need the "//" after
    the `schema:`. Python's urlunparse normalises URLs and "may result in a slightly different, but
    equivalent URL". This leads to results like:

    - urlunparse(urlparse("schema://")) == "schema:".
    - urlunparse(urlparse("schema:///root/subdir")) == "schema:/root/subdir"

    Unfortunately not all tools cope well with URLs that don't include the '://'. This function
    restores the "://" where a trip through urlunparse has removed it.
    """
    if "://" in old_url and "://" not in new_url:
        segments = new_url.split(":", maxsplit=1)
        new_url = segments[0] + "://" + segments[1]
    return new_url
