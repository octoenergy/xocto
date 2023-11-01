install: 
	pip install pip==23.1.2
	pip install -e .[dev,test]

clean:
	@echo Cleaning workspace
	-rm -rf dist/ *.egg-info/ build/
	-find . -type d -name __pycache__ -delete

# Static analysis

lint:
	make black_check ruff mypy

black_check:
	ruff format .

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

VERSION=v$(shell python setup.py --version)

tag:
	@echo Tagging as $(VERSION)
	git tag -a $(VERSION) -m "Creating version $(VERSION)"
	git push origin $(VERSION)
