# xocto - utilities for Python services

This repo houses various shared utilities for Python services at Kraken
Technologies.

This library works with Python 3.8 and above.

CI status:

[![CircleCI](https://circleci.com/gh/octoenergy/xocto/tree/master.svg?style=svg)](https://circleci.com/gh/octoenergy/xocto/tree/master)

PyPI detail page: <https://pypi.python.org/pypi/xocto>

## Functionality

### Event publishing

Use `events.publish` to publish application events. These will be logged as JSON
to a logger named "events".

Sample usage:

```python
from xocto import events

events.publish(
    event="ACCOUNT.CREATED",
    params={
        'name': 'Barry Chuckle',
        'quote_id': 'xyz123',
    },
    meta={
        'account_id': 'A-12312345'
    },
    account=account,  # optional
    request=request,  # optional
)
```

### Event timing

Time events using:

```python
from xocto import events

with events.Timer() as t:
    # do some things

events.publish(
    event="SOMETHING.HAPPENED",
    meta={
        "duration_in_ms": t.duration_in_ms
    }
)
```

### Ranges

The `ranges` module is, as the name suggests, a utility for working with ranges.

The most basic building block of the module is the `Range` class.

A few basic examples of its usage:

```python
from xocto.ranges import Range, RangeBoundaries

>>> Range(0, 2, boundaries=RangeBoundaries.EXCLUSIVE_INCLUSIVE)
<Range: (0,2]>
>>> Range(0, 2, boundaries="[]")
<Range: [0,2]>
>>> sorted([Range(1, 4), Range(0, 5)])
[<Range: [0,5)>, <Range: [1,4)>]
>>> sorted([Range(1, 2), Range(None, 2)])
[<Range: [None,2)>, <Range: [1,2)>]
>>> sorted([Range(3, 5), Range(3, 4)])
[<Range: [3,4)>, <Range: [4,5)>]
```

See [`xocto.ranges`](xocto/ranges.py) for more details, including examples and in
depth technical details.

### Numbers

The `numbers` module is intended as your one-stop shop for all things numbers.

An example of rounding a number to an arbitrary integer base:

```python
from xocto.numbers import quantise

>>> quantise(256, 5)
255
```

See [xocto.numbers](xocto/numbers.py) for more details, including examples and in depth technical details.

### The localtime module

This module is a battle tested and well reviewed module for working with dates,
times and timezones.

It's been over the years internally in Kraken Technologies, and is used heavily
internally.

The main API it presents is composed of a series of functions which accept a
date/datetime object, and manipulate it in one form or another.

Examples of a few of those:

```python
from xocto import localtime
>>> now = localtime.now()
>>> now
2022-04-20 14:57:53.045707+02:00
>>> localtime.seconds_in_the_future(n=10, dt=now)
2022-04-20 14:58:03.045707+02:00
>>> localtime.nearest_half_hour(now)
2022-04-20 15:00:00+02:00
```

See [xocto.localtime](xocto/localtime.py) for more details, including examples and in depth technical details.

## Development

### Installation

Create and activate a Python 3.8 virtualenv then run:

```sh
make install
```

to install the package including development and testing dependencies

### Running tests

Run the test suite with:

```sh
make test
```

### Running static analysis

Use these make commands

```sh
make lint
make black
make isort
```

Docker images for these jobs can be built with:

```sh
make docker_images
```

This creates separate images for pytest, isort and black. Each can be run like
so:

```sh
docker run -v `pwd`:/opt/app xocto/pytest
docker run -v `pwd`:/opt/app xocto/isort
docker run -v `pwd`:/opt/app xocto/black
```

### Publishing

Release to PyPI by:

1. Bumping the version in `setup.py`

2. Updating `CHANGELOG.md`

3. Committing:

   ```sh
   git commit -am "Bump version to v..."
   ```

4. Running:

   ```sh
   make publish
   ```
