###############################################################################
#
# Installation and release commands for the `earthdata-varinfo` Python package.
# These can be run from within a conda or Pip based virtual environment, or
# from within a Docker container.
#
###############################################################################
.PHONY: clean build test develop install

build: clean
	python -m pip install --upgrade pip
	python -m pip install --upgrade --quiet setuptools wheel twine
	python -m pip install --upgrade --quiet build
	python -m build

clean:
	rm -rf build dist *.egg-info || true

develop:
	pip install -e .[dev]

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt -r dev-requirements.txt

lint:
	pylint varinfo --extension-pkg-whitelist=netCDF4

prepare-test:
	mkdir -p tests/reports tests/coverage

test: prepare-test
	pytest --junitxml=tests/reports/earthdata-varinfo_junit.xml --cov varinfo --cov-report html:tests/coverage --cov-report term
