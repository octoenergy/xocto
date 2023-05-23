install: 
	pip install pip==23.1.2
	pip install -e .[dev,test]

clean:
	@echo Cleaning workspace
	-rm -rf dist/ *.egg-info/ build/
	-find . -type d -name __pycache__ -delete

# Static analysis

lint:
	flake8

test:
	py.test

black:
	black -v --check .

isort:
	isort --check-only .

mypy:
	mypy

docker_images:
	docker build -t xocto/pytest --target=pytest .
	docker build -t xocto/isort --target=isort .
	docker build -t xocto/black --target=black .

# Releases

VERSION=$(shell python setup.py --version)

tag:
	@echo Tagging as $(VERSION)
	git tag -a $(VERSION) -m "Creating version $(VERSION)"
	git push origin $(VERSION)

