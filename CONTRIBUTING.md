# Contributing to xocto

## Releases

### Create a PR with release notes and version updates

1. Write release notes in `CHANGELOG`.
2. Update `VERSION` in `setup.py`.
3. Update `__version__` in `xocto/__init__.py` file.

### Packaging and uploading to PyPI

After merging the release PR, create a tag and push it to the repo.

```
$ git tag -a v3.1.4 -m "xocto v3.1.4"
$ git push origin v3.1.4
```

This should trigger the GitHub actions workflow and publish Python 🐍 distributions 📦 to PyPI and TestPyPI!
