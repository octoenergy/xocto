# Changelog

## Unreleased

## V8.1.1 - 2025-07-28

- Fix spanish month translation typo [#217](https://github.com/octoenergy/xocto/pull/217).

## V8.1.0 - 2025-02-18

- Mark `FiniteDatetimeRange.days` as deprecated [#207](https://github.com/octoenergy/xocto/pull/207).
- Add `localtime.get_local_timezone()` [#206](https://github.com/octoenergy/xocto/pull/206/).

## V8.0.0 - 2025-02-05

- Remove convenience code for ddtrace [#201](https://github.com/octoenergy/xocto/pull/201/).

## V7.2.0 - 2025-01-30

- Allow the `union` operation between `FiniteDatetimeRange` and `HalfFiniteDatetimeRange` 
  (and other `DatetimeRange`s) [#189](https://github.com/octoenergy/xocto/pull/189/).

## V7.1.1 - 2025-01-22

- Improve the performance of `FiniteDatetimeRange.intersection`,
  `FiniteDatetimeRange.union` and `FiniteDatetimeRange.__lt__` [#187](https://github.com/octoenergy/xocto/pull/187).

## V7.1.0 - 2025-01-13

- Add `ranges.any_gaps` function [#185](https://github.com/octoenergy/xocto/pull/185).
- Improve the performance of the `ranges.any_overlapping` function
  (with some benchmark showing a >100x speed up) [#184](https://github.com/octoenergy/xocto/pull/184).

## V7.0.0 - 2024-12-19

- Add `FiniteDatetimeRange.as_date_range` [#181](https://github.com/octoenergy/xocto/pull/181)
- [Breaking] Remove `ranges.date_range_for_midnight_range` (replaced by FiniteDatetimeRange.as_date_range) [#181](https://github.com/octoenergy/xocto/pull/181)

## v6.2.0 - 2024-12-11

- Add `ranges.date_range_for_midnight_range` [#178](https://github.com/octoenergy/xocto/pull/178)
- Add `FiniteDatetimeRange.localize` [#178](https://github.com/octoenergy/xocto/pull/178)

## v6.1.0 - 2024-08-30

- Add optional `timezone` parameter to datetime-based range fields [#174](https://github.com/octoenergy/xocto/pull/174)

## v6.0.0 - 2024-08-30

- [Breaking] Use parameter object for passing options to `pact_service`.
  Rename parameter `pact_version` to `consumer_version`.
  [#166](https://github.com/octoenergy/xocto/pull/166)
- Fix bug with `list_files`  method in `S3SubdirectoryFileStore` [#171](https://github.com/octoenergy/xocto/pull/171)

## v5.1.0 - 2024-07-03

- Add `ranges.iterate_over_months` function [#163](https://github.com/octoenergy/xocto/pull/163)

## v5.0.1 - 2024-06-18

- Implements `__copy__` and `__deepcopy__` on Range types [#160](https://github.com/octoenergy/xocto/pull/160/)

## v5.0.0 - 2024-06-18

- [Breaking] Range types are now (mostly) immutable [#142](https://github.com/octoenergy/xocto/pull/142)
    - start, end, and bounds can no longer be modified after creation
- [Breaking] The `types` module is now split into a package containing `types.generic` and `types.django` [#144](https://github.com/octoenergy/xocto/pull/144)
    - `xocto.numbers` and `xocto.ranges` can now be imported without configuring Django
- Postgres range database fields now allow querying by a single value [#150](https://github.com/octoenergy/xocto/pull/150)
- `Storage.fetch_file` now supports fetching a range [#154](https://github.com/octoenergy/xocto/pull/154/)
- Enables `FiniteDatetimeRange` to be unioned with more than two ranges [#155](https://github.com/octoenergy/xocto/pull/155)

## v4.10.2 - 2024-03-13

- Yanked v4.10.1 due to unintentional inclusion of breaking changes. This release is identical to v4.10.1, but with the breaking changes from [#142](https://github.com/octoenergy/xocto/pull/142) removed.


## v4.10.1 - 2024-03-12

- Updated build config to automatically include sub-packages [#143](https://github.com/octoenergy/xocto/pull/143)
    - Makes available the new `xocto.fields` package in the distribution introduced in 4.10.0

## v4.10.0 - 2024-03-05

- Updated dev dependencies like ruff, pytest, and mypy [#138](https://github.com/octoenergy/xocto/pull/138)
- Updated doc dependencies to fix the build [#139](https://github.com/octoenergy/xocto/pull/139)
- Added a new module `xocto.fields.postgres.ranges` to provide range fields that work with the `Range` classes from `xocto.ranges` [#136](https://github.com/octoenergy/xocto/pull/136)
    - Tests now depend on postgres and psycopg2
- Doc site should now build again correctly

## v4.9.3 - 2024-01-16

- Add "as_finite_datetime_periods" fn [#134](https://github.com/octoenergy/xocto/pull/134)

## v4.9.2 - 2023-12-07

- Add HalfFiniteRangeSet class to better support working with sets of such ranges [#130](https://github.com/octoenergy/xocto/pull/130)

## v4.9.1 - 2023-11-20

- Include py.typed files in package data to restore correct type checking [#127](https://github.com/octoenergy/xocto/pull/127)

## v4.9.0 - 2023-11-17

- Modernize setup to use pyproject.toml [#116](https://github.com/octoenergy/xocto/pull/116)
- Populate `xocto.__version__` from package metadata
- Enables `FiniteDateRange` to be unioned with more than two ranges [#123](https://github.com/octoenergy/xocto/pull/123)

## v4.8.0 - 2023-11-02

- Fix docs by adding missing rtd theme [#115](https://github.com/octoenergy/xocto/pull/113)
- Adding explicit type for Optional OneToOneField [#113](https://github.com/octoenergy/xocto/pull/113)
- Fix `OverflowError` when calling `is_disjoint` on a range containing `date.min` or `date.max` [#112](https://github.com/octoenergy/xocto/pull/112)
- Improve autodoc of callables and variables [#111](https://github.com/octoenergy/xocto/pull/111)

## v4.7.0 - 2023-10-31

🎃 Happy Halloween! 🎃

- Adding explicit type for Optional Foreign Key [#108](https://github.com/octoenergy/xocto/pull/108)

## v4.6.1 - 2023-10-27

- Fix erroneously narrow typehinting in localtime module [#106](https://github.com/octoenergy/xocto/pull/106)
- Fix ValueError bug when trying to intersect adjacent FiniteDateRanges [#105](https://github.com/octoenergy/xocto/pull/105)

## v4.6.0 - 2023-10-20

- Upgrade duckdb package to version 0.9.0[#104](https://github.com/octoenergy/xocto/pull/104)

## v4.5.0 - 2023-10-18

- Fix bug with `FiniteDateRange.days` being 1 day short [#98](https://github.com/octoenergy/xocto/pull/98)
- Make `FiniteDateRange.is_disjoint` recognise adjacent ranges as not disjoint [#99](https://github.com/octoenergy/xocto/pull/99)
- Add a `strftime` function to localtime module [#100](https://github.com/octoenergy/xocto/pull/100)

## v4.4.0 - 2023-10-12

- Replaced flake8 and isort with ruff [#101](https://github.com/octoenergy/xocto/pull/101)
- Updated types in localtime.py [#101](https://github.com/octoenergy/xocto/pull/101)
- Add `RangeSet.is_(left|right)_finite` [#96](https://github.com/octoenergy/xocto/pull/96)

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
