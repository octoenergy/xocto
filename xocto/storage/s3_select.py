"""
This file contains helper functions necessary for using the s3 select functionality.

Note:
    - Many comments have been taken directly from the boto3 [docs]
(https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.select_object_content)
"""
from __future__ import annotations

import dataclasses
import enum
from typing import Any


class S3SelectException(Exception):
    pass


class FileHeaderInfo(str, enum.Enum):
    """
    A bucket of strings used by the `select_object_content` function to read a CSV file.
    """

    # First line is not a header.
    NONE = "NONE"

    # First line is a header, but you can't use the header values to indicate the column in an expression.
    # You can use column position (such as _1, _2, …) to indicate the column (SELECT s._1 FROM OBJECT s ).
    IGNORE = "IGNORE"

    # First line is a header, and you can use the header value to identify a column in an expression
    # (SELECT "name" FROM OBJECT ).
    USE = "USE"


class CompressionType(str, enum.Enum):
    # Specifies object's compression format.
    NONE = "NONE"
    GZIP = "GZIP"
    BZIP2 = "BZIP2"


class QuoteFields(str, enum.Enum):
    # Always use quotation marks for output fields.
    ALWAYS = "ALWAYS"
    # Use quotation marks for output fields when needed.
    ASNEEDED = "ASNEEDED"


@dataclasses.dataclass(frozen=True)
class BaseSerializer:
    def to_dict(self) -> dict[str, Any]:
        """
        A helper method to remove None values from the dict and ensures all enum fields use their values
        instead of an enum instance.
        """

        temp_dict = {k: v for k, v in dataclasses.asdict(self).items() if v}

        for k, v in temp_dict.items():
            if (
                isinstance(v, FileHeaderInfo)
                or isinstance(v, QuoteFields)
                or isinstance(v, CompressionType)
            ):
                temp_dict[k] = v.value
        return temp_dict


@dataclasses.dataclass(frozen=True)
class CSVInputSerializer(BaseSerializer):
    # Describes the first line of input
    FileHeaderInfo: FileHeaderInfo
    # A single character used to indicate that a row should be ignored when the character is present at the start of
    # that row. You can specify any character to indicate a comment line.
    Comments: str | None = None
    # A single character used for escaping the quotation mark character inside an already escaped value.
    # For example, the value """ a , b """ is parsed as " a , b " .
    QuoteEscapeCharacter: str | None = None
    # A single character used to separate individual records in the input. Instead of the default value,
    # you can specify an arbitrary delimiter.
    RecordDelimiter: str | None = "\n"
    # A single character used to separate individual fields in a record. You can specify an arbitrary delimiter.
    FieldDelimiter: str | None = ","
    # A single character used for escaping when the field delimiter is part of the value. For example, if the
    # value is a, b , Amazon S3 wraps this field value in quotation marks, as follows: " a , b " .
    QuoteCharacter: str | None = None
    # Specifies that CSV field values may contain quoted record delimiters and such records should be allowed.
    # Default value is FALSE. Setting this value to TRUE may lower performance.
    AllowQuotedRecordDelimiter: bool | None = False


@dataclasses.dataclass(frozen=True)
class CSVOutputSerializer(BaseSerializer):
    # Indicates whether to use quotation marks around output fields.
    QuoteFields: QuoteFields | None = None
    # The value used to separate individual fields in a record. You can specify an arbitrary delimiter.
    FieldDelimiter: str | None = ","
    # A single character used for escaping when the field delimiter is part of the value. For example,
    # if the value is a, b, Amazon S3 wraps this field value in quotation marks, as follows: " a , b " .
    QuoteCharacter: str | None = None
    # The single character used for escaping the quote character inside an already escaped value.
    QuoteEscapeCharacter: str | None = None
    # A single character used to separate individual records in the output. Instead of the default value,
    # you can specify an arbitrary delimiter.
    RecordDelimiter: str | None = "\n"


@dataclasses.dataclass(frozen=True)
class JSONOutputSerializer(BaseSerializer):
    # A single character used to separate individual records in the output. Instead of the default value,
    # you can specify an arbitrary delimiter.
    RecordDelimiter: str | None = "\n"


@dataclasses.dataclass(frozen=True)
class ScanRange(BaseSerializer):
    """
    Specifies the byte range of the object to get the records from.

    - Provide a start and an end value to perform an inclusive search.
    - Provide only the start value to process search after the given X records.
    - Provide only the end value to search the last X records of the file.
    """

    Start: int | None = None
    End: int | None = None


def get_serializers_for_csv_file(
    *,
    input_serializer: CSVInputSerializer,
    compression_type: CompressionType,
    output_serializer: CSVOutputSerializer | JSONOutputSerializer,
    scan_range: ScanRange | None = None,
) -> dict:
    """
    Returns input and output serialization dictionaries that should be used to perform a select_object_content query.

    Note: It is recommended to use JSONOutputSerializer over CSVOutputSerializer while using ScanRange queries
    because the former prevents premature chunked data. In other words, because scan range queries loop over the file
    using byte range, you can expect the JSON output format to at least return one single row in each iteration. With
    CSV output format, there is a high chance of receiving output that has been chunked to a certain byte.
    """

    compression_type_value = (
        compression_type.value
        if isinstance(compression_type, CompressionType)
        else compression_type
    )

    output_format = output_serializer.to_dict()

    if isinstance(output_serializer, CSVOutputSerializer):
        output_serialization_format = {"CSV": output_format}
    else:
        output_serialization_format = {"JSON": output_format}

    temp_dict = {
        "input_serialization": {
            "CSV": input_serializer.to_dict(),
            "CompressionType": compression_type_value,
        },
        "output_serialization": output_serialization_format,
    }

    if scan_range:
        if compression_type == CompressionType.GZIP:
            raise S3SelectException(
                "Scan range queries are not supported on objects with type GZIP."
            )
        temp_dict["ScanRange"] = scan_range.to_dict()

    return temp_dict
