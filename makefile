install: 
	pip install -e .[dev,test]

clean:
	-rm -rf dist/ *.egg-info/ build/
	-find . -type d -name __pycache__ -delete

package:
	python setup.py bdist_wheel

publish: clean package
	twine upload dist/*

lint:
	flake8

test:
	py.test
