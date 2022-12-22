import csv
import io
import os

import pytest

from xocto.storage import files


class TestSize:
    @pytest.mark.parametrize(
        "file,size",
        [
            (io.BytesIO(), 0),
            (io.BytesIO(b"Lorem ipsum"), 11),
            (io.StringIO(), 0),
            (io.StringIO("Lorem ipsum"), 11),
        ],
    )
    def test_returns_size(self, file, size):
        assert files.size(file) == size


def test_files_hash_correctly():
    file1 = io.BytesIO(b"This is my first file")
    assert (
        files.hashfile(file1) == "2f1b1b913ca382ad8f992ec6a18ecedfa2fcd8ff21b0a2227614a7bd94c23d2d"
    )
    file2 = io.BytesIO(b"And this is my second")
    assert (
        files.hashfile(file2) == "8cbe3eb51eec64423d2a870da81475361fa3571402fb77810db261e1920d45b4"
    )


def test_convert_xlsx_file_to_csv(fixture_path):

    report_filename = "Daily-report-Octopus Energy-2020-04-08"
    xlsx_filepath = fixture_path(f"siteworks/agent_reports/{report_filename}.xlsx")
    csv_filepath = fixture_path(f"siteworks/agent_reports/{report_filename}.csv")

    with files.convert_xlsx_to_csv(
        xlsx_filepath=xlsx_filepath, csv_filepath=csv_filepath
    ) as csv_file:
        rows = csv.reader(csv_file)
        rows = list(rows)
        assert len(rows) == 4
        assert rows[0][0] == "MPAN"
        assert rows[0][79] == "Customer_spoken_to_about_rearranged_time"

        assert rows[1][0] == "1111111111111"
        assert rows[1][5] == "02/10/2019"
        assert rows[2][0] == "2222222222222"

        assert rows[2][14] == "16:00"
        assert rows[3][0] == "3333333333333"

    os.remove(csv_filepath)


def test_convert_xls_file_to_csv(fixture_path):

    report_filename = "Daily-report-Octopus Energy-2019-08-15"
    xls_filepath = fixture_path(f"siteworks/agent_reports/{report_filename}.xls")
    csv_filepath = fixture_path(f"siteworks/agent_reports/{report_filename}.csv")

    with files.convert_xls_to_csv(
        xls_filepath=xls_filepath, csv_filepath=csv_filepath
    ) as csv_file:
        rows = csv.reader(csv_file)
        rows = list(rows)
        assert len(rows) == 3
        assert rows[0][0] == "MPAN"

        # Seems to be one less field in the older AES report sampled for this test
        assert rows[0][78] == "Customer_spoken_to_about_rearranged_time"

        assert rows[1][0] == "1111111111111"
        assert rows[1][1] == "2222222222222"
        assert rows[1][3] == "1 MADE UP ROAD"
        assert rows[1][5] == "13/08/2018"
        assert rows[1][14] == "13:00"

        assert rows[2][0] == "3333333333333"
        assert rows[2][1] == "4444444444444"
        assert rows[2][3] == "2 EXAMPLE ROAD"
        assert rows[2][5] == "13/08/2018"

    os.remove(csv_filepath)
