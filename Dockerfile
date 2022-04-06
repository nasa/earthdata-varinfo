 ##############################################################################
 #
 # A Dockerfile to be used for the testing and release of the `sds-varinfo`
 # Python library. This draws heavily from the template used to release the
 # `harmony-service-lib`.
 #
 # The produced image will allow targets within the associated Makefile to be
 # run via the `docker run` command, e.g.:
 #
 # $ docker build -t sds:varinfo:latest .
 # $ docker run --rm sds/varinfo:latest test
 #
 # These commands are encapsulated in bin/build-image.sh and bin/run-test.sh
 #
 # NOTE: 2021-07-07: Alpine version has been pinned to 3.13 due to regression
 #       in the image, see: https://gitlab.alpinelinux.org/alpine/aports/-/issues/12763
 #       Expected resolution mid-July 2021 (remove tag from image when fixed).
 #
 #
 ##############################################################################
 FROM python:3.10-slim

 WORKDIR /app/
 RUN apt-get update && apt-get install -y \
    make gcc hdf5-tools libnetcdf-dev && \
    rm -rf /var/lib/apt/lists/*

 RUN addgroup -gid 500 bamboo
 RUN adduser --disabled-password --home /build --ingroup bamboo --uid 500 bamboo

 COPY . /app/
 RUN make develop
 RUN make prepare-test

 RUN chown -R bamboo:bamboo .
 USER bamboo

 ENTRYPOINT ["make"]
