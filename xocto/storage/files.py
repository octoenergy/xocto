"""
A module for file-related functions.
"""
from __future__ import annotations

import codecs
import csv
import hashlib
import io
import os
import tempfile
from typing import IO, Any

import openpyxl
import pandas as pd
import xlrd

XLRD_FLOAT_TYPE = 2


def size(file: IO) -> int:
    """
    Return the size of the file in bytes.
    """
    position = file.tell()
    file.seek(0, os.SEEK_END)
    size_ = file.tell()
    file.seek(position)
    return size_


def hashfile(file_handle, hasher=hashlib.sha256, blocksize=65536):
    """
    Get contents of file as hash. Use like so:
    >>> hashfile(open(myfile, 'rb'))
    ... 40c33eec0a307e7726992d3786f11a8c30309489455c33cfc14b36e6fbf7347b
    """
    hasher = hasher()
    _buffer = file_handle.read(blocksize)
    while len(_buffer) > 0:
        hasher.update(_buffer)
        _buffer = file_handle.read(blocksize)
    return hasher.hexdigest()


def convert_xlsx_to_csv(
    xlsx_filepath: str,
    csv_filepath: str | None = None,
    encoding: str | None = None,
    errors: str | None = None,
    quoting: int | None = csv.QUOTE_ALL,
    delimiter: str | None = ",",
) -> IO:
    """
    Convert .xlsx files to CSV format using `openpyxl` and return a handle to the output file.

    Args:
        xlsx_filepath:     Path of .xls or .xlsx file to convert.
        csv_filepath:       Location of result file referenced by returned handler. A temporary
                            file will be created if this arg is not present.
        encoding:           Encoding scheme for csv file.
        errors:             How file object should handle encoding errors.
        quoting:            The type of quoting the output CSV file should have
        delimiter:          The delimiter the output CSV file should have

    """
    # data_only to extract values from formulae and not formulas themselves
    workbook = openpyxl.load_workbook(xlsx_filepath, data_only=True, read_only=True)
    sheet = workbook.active

    csv_file, wr = _get_csv_file_and_writer(csv_filepath, encoding, errors, quoting, delimiter)

    for row in sheet.rows:
        wr.writerow([cell.value for cell in row])

    # Return handle to csv object
    csv_file.seek(0)
    return csv_file


def convert_xls_to_csv(
    xls_filepath: str,
    csv_filepath: str | None = None,
    encoding: str | None = None,
    errors: str | None = None,
    quoting: int | None = csv.QUOTE_ALL,
    delimiter: str | None = ",",
) -> IO:
    """
    Convert .xls files to CSV format using `xlrd` and return a handle to the output file.

    Args:
        xls_filepath:       Path of .xls file to convert.
        csv_filepath:       Location of result file referenced by returned handler. A temporary
                            file will be created if this arg is not present.
        encoding:           Encoding scheme for csv file.
        errors:             How file object should handle encoding errors.
        quoting:            The type of quoting the CSV file should have
        delimiter:          The delimiter the output CSV file should have

    """
    workbook = xlrd.open_workbook(xls_filepath)
    sheet = workbook.sheet_by_index(0)

    csv_file, wr = _get_csv_file_and_writer(csv_filepath, encoding, errors, quoting, delimiter)
    for rownum in range(sheet.nrows):
        row = sheet.row(rownum)
        values = []
        for cell in row:
            value = cell.value
            # Excel treats all numbers as floats
            if cell.ctype == XLRD_FLOAT_TYPE:
                if cell.value % 1 == 0.0:
                    value = int(value)
            values.append(value)
        wr.writerow(values)

    # Return handle to csv object
    csv_file.seek(0)
    return csv_file


def _get_csv_file_and_writer(
    csv_filepath: str | None,
    encoding: str | None,
    errors: str | None,
    quoting: int | None = csv.QUOTE_ALL,
    delimiter: str | None = ",",
) -> tuple[IO, Any]:
    if quoting is None:
        quoting = csv.QUOTE_ALL
    if delimiter is None:
        delimiter = ","

    if csv_filepath:
        csv_file = open(csv_filepath, mode="w+", encoding=encoding, errors=errors)
    else:
        # `error' argument added in 3.8
        csv_file = tempfile.NamedTemporaryFile(mode="w+", encoding=encoding)  # type: ignore

    return csv_file, csv.writer(csv_file, quoting=quoting, delimiter=delimiter)


def remove_bom(string):
    """
    Remove the BOM mark from the beginning of a string if it exists.

    This mark is sometimes added to excel files and causes issues when reading.
    """
    return string[3:] if string.startswith(str(codecs.BOM_UTF8)) else string


def generate_csv_bytes(data: list, headers: list) -> bytes:
    """
    Generates a csv file and transforms it to bytes.
    reference: https://okhlopkov.medium.com/dont-save-a-file-on-disk-to-send-it-with-telegram-bot-d7cd591fec2d
    :param data: List containing the data rows
    :param headers: List containing the headers of the file
    """
    rows = [headers, *data]

    string_io = io.StringIO()

    csv.writer(string_io).writerows(rows)
    string_io.seek(0)

    csv_bytes = io.BytesIO()
    csv_bytes.write(string_io.getvalue().encode())
    csv_bytes.seek(0)

    return csv_bytes.read()


def convert_csv_to_parquet(
    data: bytes,
    na_values: str | dict | None = None,
    data_type: str | dict | None = None,
    parse_dates: list[str] | None = None,
) -> bytes:
    """
    Converts bytes from CSV format to Parquet.

    :param data: bytes contents for/from a CSV file
    :param na_values: Additional strings to recognize as NA/NaN. If dict passed, specific
    per-column NA values.
    :param data_type: Data type for data or columns. You can Use str, object or a dict with
    the column names and types. E.g. {‘a’: np.float64, ‘b’: np.int32, ‘c’: ‘Int64’}
    :return: bytes for a Parquet file
    """
    dataframe = pd.read_csv(
        io.BytesIO(data),
        dtype=data_type,
        na_values=na_values,
        parse_dates=parse_dates,
        thousands=",",
    )
    bytes_io = io.BytesIO()
    dataframe.to_parquet(bytes_io, engine="pyarrow")
    bytes_io.seek(0)
    return bytes_io.read()
