# Development

## Installation

Create and activate a Python 3.8 virtualenv then run:

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

## Publishing

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
