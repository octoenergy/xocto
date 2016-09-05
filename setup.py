from setuptools import setup, find_packages
from codecs import open
from os import path

REPO_ROOT = path.abspath(path.dirname(__file__))

with open(path.join(REPO_ROOT, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='xocto',
    version='1.0',
    description='Octopus Energy Python service utilities',
    long_description=long_description,
    url='https://github.com/octoenergy/xocto',
    author='Octopus Energy',
    author_email='talent@octopus.energy',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
    ],
    packages=find_packages(exclude=['tests']),
    install_requires=[],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'dev': [
            'wheel==0.29.0',
            'twine==1.8.1',
            'flake8==3.0.4',
        ],
        'test': [
            'pytest==3.0.2'
        ],
    },
)
