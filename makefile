install:
	pip install -U uv
	uv pip install -e '.[dev,docs]'


# CI step wrappers

ci: format_check lint_check test mypy

format_check:
	ruff format --check .

lint_check:
	ruff check .

test:
	py.test  --benchmark-disable

benchmark:
	py.test  --benchmark-only --benchmark-autosave --benchmark-compare --benchmark-group-by=func --benchmark-columns mean,rounds,iterations

mypy:
	mypy --version
	mypy

# Local helpers

clean:
	@echo Cleaning workspace
	-rm -rf dist/ *.egg-info/ build/
	-find . -type d -name __pycache__ -delete

format:
	ruff check --fix .
	ruff format .

# Releases

# Extract version from pyproject.toml
VERSION=v$(shell python -c "import importlib.metadata; print(importlib.metadata.version('xocto'))")

tag:
	@echo Tagging as $(VERSION)
	git tag -a $(VERSION) -m "Creating version $(VERSION)"
	git push origin tag $(VERSION)
