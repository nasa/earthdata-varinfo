#!/bin/bash
set -ex

# Make the directory into which XML format test reports will be saved
#
mkdir -p tests/reports

# Make the directory into which coverage reports will be saved
#
mkdir -p tests/coverage

# Run the test Docker image as a container
docker run --rm \
	-v $(pwd)/tests/reports:/app/tests/reports \
	-v $(pwd)/tests/coverage:/app/tests/coverage \
	sds/varinfo test
