install:
	uv sync --all-groups


# CI step wrappers

ci: format_check lint_check test mypy

format_check:
	uv run ruff format --check .

lint_check:
	uv run ruff check .

test:
	uv run pytest --benchmark-disable

benchmark:
	pytest  --benchmark-only --benchmark-autosave --benchmark-compare --benchmark-group-by=func --benchmark-columns mean,rounds,iterations

mypy:
	uv run mypy --version
	uv run mypy

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
	@BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	if [ "$$BRANCH" != "main" ]; then \
		echo "Error: You must be on the 'main' branch to tag. Current branch: $$BRANCH"; \
		exit 1; \
	fi
	@echo Tagging as $(VERSION)
	git tag -a $(VERSION) -m "Creating version $(VERSION)"
	git push origin tag $(VERSION)
