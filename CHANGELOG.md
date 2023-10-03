# Changelog

## v4.4.0 - 2023-10-03

- Add `is_left_finite` and `is_right_finite` methods to `ranges.RangeSet` [#96](https://github.com/octoenergy/xocto/pull/96/).

## v4.3.0 - 2023-09-27

- Enable querying parquet files using `S3FileStore.fetch_object_contents_with_s3_select` and `LocalFileStore.fetch_object_contents_with_s3_select` [#95](https://github.com/octoenergy/xocto/pull/95/)

## v4.2.1 - 2023-09-18

- Allow timzone override in `localtime.parse_dt` [#93](https://github.com/octoenergy/xocto/pull/93)

## v4.2.0 - 2023-09-06

- Add `localtime.parse_date` and `localtime.parse_dt` [#91](https://github.com/octoenergy/xocto/pull/91)

## v4.1.1 - 2023-09-06

- Allow any iterable type in `ranges.any_overlapping` [#90](https://github.com/octoenergy/xocto/pull/90)

## v4.1.0 - 2023-09-01

- Add URL utils [#87](https://github.com/octoenergy/xocto/pull/87)

## v4.0.0 - 2023-07-05

- Remove pytz in favour of Python's builtin ZoneInfo [#61](https://github.com/octoenergy/xocto/pull/61)
- Bump min supported Django version to 4.0 [#61](https://github.com/octoenergy/xocto/pull/61)

## v3.2.0 - 2023-06-07

- Bump min supported Python version to 3.9 [#74](https://github.com/octoenergy/xocto/pull/74), prompting a minor version change from 3.1.4 to 3.2.0
- Update error message for ranges with unbounded end [#75](https://github.com/octoenergy/xocto/pull/75)
- Ranges: add utils to check period covering [#69](https://github.com/octoenergy/xocto/pull/69)
- Add an extra example to ranges.Range.union [#67](https://github.com/octoenergy/xocto/pull/67)
- Improve localtime module docstrings [#65](https://github.com/octoenergy/xocto/pull/65)
- Defer openpyxl import [#62](https://github.com/octoenergy/xocto/pull/62)

## v3.1.4 - 2023-03-24

- Added ddtrace as a dependency [#56](https://github.com/octoenergy/xocto/pull/56)

## v3.1.2 - 2023-03-20

- `get_finite_datetime_ranges_from_timestamps()` now accepts an Iterable rather than a list. [#54](https://github.com/octoenergy/xocto/pull/54)

## v3.1.1 - 2023-03-13

- Added numpy as a dependency [#52](https://github.com/octoenergy/xocto/pull/52)

## v3.1.0 - 2023-03-07

- New function `pact_testing.get_git_branch_name()` for getting current git branch name [#40](https://github.com/octoenergy/xocto/pull/40)
- New tracing module [#46](https://github.com/octoenergy/xocto/pull/46)
- Updated dependencies so openpyxl, pandas, python-dateutil, python-magic, pytz, structlog, and xlrd are installed not just in dev [#48](https://github.com/octoenergy/xocto/pull/48)
- Add pyarrow dependency [#44](https://github.com/octoenergy/xocto/pull/44)

## v3.0.0 - 2023-02-28

Includes:

- Many type annotations added ([#33](https://github.com/octoenergy/xocto/pull/33)), breaking changes for some users means releasing this as a major version upgrade.
- Type annotation for `get_finite_datetime_ranges_from_timestamps` updated ([#37](https://github.com/octoenergy/xocto/pull/37)).
- Added the `localtime` function `period_exceeds_one_year` for determining whether a datetime period
  exceeds one year ([#41](https://github.com/octoenergy/xocto/pull/41)).

## v2.4.0 - 2023-02-28

Includes:

- Many type annotations added ([#33](https://github.com/octoenergy/xocto/pull/33)).
- Type annotation for `get_finite_datetime_ranges_from_timestamps` updated ([#37](https://github.com/octoenergy/xocto/pull/37)).
- Added the `localtime` function `period_exceeds_one_year` for determining whether a datetime period
  exceeds one year ([#41](https://github.com/octoenergy/xocto/pull/41)).

## v2.3.0 - 2023-01-20

Includes:

- Addition of get_last_modified function ([#32](https://github.com/octoenergy/xocto/pull/32))
- Update project dependencies ([#34](https://github.com/octoenergy/xocto/pull/34))

## v2.2.1 - 2022-12-23

Includes:

- A small fix to publish the storage module in setup.py
- README update

## v2.2 - 2022-12-22

Includes:

- Remove the assert_never helper ([#16](https://github.com/octoenergy/xocto/pull/16))
- Add common pact testing test fixtures #18 ([#18](https://github.com/octoenergy/xocto/pull/18))
- Add S3 reusable code ([#19](https://github.com/octoenergy/xocto/pull/19))

Starting from this release, this project will be versioned using [Semantic Versioning ](https://semver.org/):

> Given a version number MAJOR.MINOR.PATCH, increment the:
>
> - MAJOR version when you make incompatible API changes
> - MINOR version when you add functionality in a backwards compatible manner
> - PATCH version when you make backwards compatible bug fixes
> - Additional labels for pre-release and build metadata are available as extensions to the MAJOR.MINOR.PATCH format.

In practice this has been happening already, but we are now making it official.

## v2.1 - 2022-11-25

This is an unknown release, mentioned here for the sake of completeness.

## v2.0 - 2022-07-31

Includes:

- The localtime functions now return a Python datetime timezone UTC instead of a pytz UTC

## v1.6.1 - 2022-05-12

Includes:

- Fix `is_local_time()` when using Python's datetime timezone UTC

## v1.6 - 2022-05-05

Includes:

- Support for Django v4 (currently only supports `USE_DEPRECATED_PYTZ = True`)

## v1.5 - 2022-04-14

Includes:

- Add the localtime, ranges, numbers and types modules
- Update black and isort

## v1.4 - 2019-03-14

Includes:

- Include AWS instance ID in event metadata.

## v1.3 - 2018-03-08

Includes:

- New settlement period functions.

## v1.2 - 2018-01-08

Includes:

- New function to calculate the number of settlement periods in a given timedelta.

## v1.1 - 2017-12-19

Includes:

- Import settlement period helpers from [octotools repo](https://github.com/octoenergy/octotools)

## v1.0.2 - 2017-01-24

Includes:

- Ensure event meta data is published if it is non-empty

## v1.0.1

Includes:

- Event publishing functionality
- Unapplied migration checking function

## v1.0.0

Whoops
