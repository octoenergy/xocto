install:
	pip install -e .[dev,test]

clean:
	@echo Cleaning workspace
	-rm -rf dist/ *.egg-info/ build/
	-find . -type d -name __pycache__ -delete

VERSION=$(shell python setup.py --version)

tag:
	@echo Tagging as $(VERSION)
	git tag -a $(VERSION) -m "xoct $(VERSION)"
	git push origin $(VERSION)

publish: clean build_package upload_package tag

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
