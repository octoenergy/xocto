install: 
	pip install pip==23.3.1
	pip install -e '.[dev,docs]'

clean:
	@echo Cleaning workspace
	-rm -rf dist/ *.egg-info/ build/
	-find . -type d -name __pycache__ -delete

# Static analysis

lint:
	make format_check ruff mypy

format_check:
	ruff format --check .

ruff:
	ruff check .

mypy:
	mypy

test:
	py.test

format:
	ruff check --fix .
	ruff format .

docker_images:
	docker build -t xocto/pytest --target=pytest .
	docker build -t xocto/ruff --target=ruff .

# Releases

VERSION=v$(shell grep -m 1 version pyproject.toml | tr -s ' ' | tr -d '"' | tr -d "'" | cut -d' ' -f3)

tag:
	@echo Tagging as $(VERSION)
	git tag -a $(VERSION) -m "Creating version $(VERSION)"
	git push origin $(VERSION)
