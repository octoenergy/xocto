# Changelog

## v2.1 - 2022-11-25

Includes:
- Add common pact testing fixture helpers.

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
