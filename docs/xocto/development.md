# Development

This page details how to develop `xocto`.

## Installation of development environment

Create and activate a Python 3.9 virtualenv then run:

```sh
make install
```

to install the package including development and testing dependencies.

## Running tests

Run the test suite with:

```sh
make test
```

## Running static analysis

Use these make commands:

```sh
make format_check  # Check formatting
make lint_check    # Check linting
make mypy          # Check Python type annotations
```

## Coding conventions

### Don't mix code changes with version updates

Code changes mixed with version updates are problematic. The reason is because
of this workflow:

1. I write a bug-fix PR that also updates the version
2. You add a feature PR that also updates the version
3. Everyone else mixes version changes with their code change PRs
4. My PR is accepted, now everyone else has to update the version specified in
   their PR

This is why typically in shared projects version releases are separated into
their own pull requests.

## Publishing

### Version number

First determine the version number. Follow the instructions specified on
[semver.org](https://semver.org/) which advocates this pattern:

```
MAJOR.MINOR.PATCH
```

where:

- MAJOR version when you make backwards-incompatible API changes
- MINOR version when you add functionality in a backward compatible manner
- PATCH version when you make backward compatible bug fixes

### Release to PyPI

Create a pull request that:

1. Adds release notes to `CHANGELOG.md`.

2. Update the `version` constant in `pyproject.toml`, following the
   [semver.org](https://semver.org/) specification.

Commit these changes in a single commit with subject matching
`Bump version to v...`.

After merging the pull request, push an annotated tag to Github with:

```sh
make
make tag
```

This will trigger a Github action to publish the package to PyPI.

### Backporting a fix

If you've committed a bug fix that you'd like to release as a patch to a previous
version (say, we've moved from 1.0.0 to 1.2.0 but you'd like to release a 1.0.1),
then you can follow this recipe:

1. Checkout the tag of the version you want to backport to:

```sh
git checkout v1.0.0
```

2. Then cherry-pick the specific commit you want to backport:

```sh
git cherry-pick <commit-hash>
```

3. Next, follow the release process as defined above. Add the release note, bump
   the version to v1.0.1, and push the tag.

4. Repeat the process for any other versions you want to backport to, such as
   v1.1.0, ensuring that the changelog is updated to reflect v1.0.1 in each
   version you're updating.

5. Finally, update the changelog on `main` to reflect the newly backported versions.

Backporting should be used sparingly, as it can result in a non-linear change
history as release tags diverge. Only critical bug fixes should be backported,
and usually only when a new major version with backward compatible changes has
been released inbetween the fix and backport target.
