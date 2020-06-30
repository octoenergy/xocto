# xocto - utilities for Python services

This repo houses various shared utilities for Python services at Octopus Energy.

CI status:

[![CircleCI](https://circleci.com/gh/octoenergy/xocto/tree/master.svg?style=svg)](https://circleci.com/gh/octoenergy/xocto/tree/master)

PyPI detail page: https://pypi.python.org/pypi/xocto

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

## Contributing

Create and activate a virtualenv then:

    $ make

Test package locally with:

    $ make test

and:

    $ make lint  

Development docker images can be built with:

    $ make docker_images

which creates separate images for pytest, isort and black. Each can be run like so:

    $ docker run -v `pwd`:/opt/app xocto/pytest
    $ docker run -v `pwd`:/opt/app xocto/isort
    $ docker run -v `pwd`:/opt/app xocto/black

## Release new version

Release to PyPI by:

1. Bumping the version in `setup.py`

2. Updating `CHANGELOG.md`

3. Committing

        $ git commit -am "Bump version to v..."

4. Running: 

        $ make publish
