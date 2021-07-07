###############################################################################
#
# Installation and release commands for the `sds-varinfo` Python package.
# These can be run from within a conda or Pip based virtual environment, or
# from within a Docker container.
#
###############################################################################
.PHONY: clean build publish test develop

REPO ?= https://upload.pypi.org/legacy/
REPO_USER ?= unset
REPO_PASS ?= unset

build: clean
	python -m pip install --upgrade pip
	python -m pip install --upgrade --quiet setuptools wheel twine
	python setup.py --quiet sdist bdist_wheel

publish: build
	python -m twine check dist/*
	python -m twine upload --username "$(REPO_USER)" --password "$(REPO_PASS)" --repository-url "$(REPO)" dist/*

clean:
	rm -rf build dist *.egg-info || true

develop:
	pip install -e .[dev]

lint:
	pylint varinfo --extension-pkg-whitelist=netCDF4

prepare-test:
	mkdir -p tests/reports tests/coverage

test: prepare-test
	coverage run -m xmlrunner discover tests -o tests/reports
	coverage html --omit="*tests/*" -d tests/coverage
