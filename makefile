install:
	pip install uv==0.2.34
	uv pip install -r requirements.txt --editable .

sync_requirements:
	uv pip compile --output-file=requirements.txt --extra=dev pyproject.toml

# CI step wrappers

ci: format_check lint_check test mypy

format_check:
	ruff format --check .

lint_check:
	ruff check .

test:
	py.test

mypy:
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
	git push origin $(VERSION)
