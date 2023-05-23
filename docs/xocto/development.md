# Development

## Installation of development environment

Create and activate a Python 3.9 virtualenv then run:

```sh
make install
```

to install the package including development and testing dependencies

## Running tests

Run the test suite with:

```sh
make test
```

## Running static analysis

Use these make commands:

```sh
make lint
make black
make isort
make mypy
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

## Publishing

Release to PyPI by creating a pull request that:

1. Adds release notes to `CHANGELOG.md`.

2. Updates the `VERSION` constant in `setup.py`.

3. Updates the `__version__` constant in `xocto/__init__.py`.

Commit these changes in a single commit with subject matching
`Bump version to v...`.

After merging the pull request, push an annotated tag to Github with:

```sh
make tag
```

This will trigger a Github action to publish the package to PyPI.
