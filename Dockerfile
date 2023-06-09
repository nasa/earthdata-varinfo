 ##############################################################################
 #
 # A Dockerfile to be used for the testing and release of the
 # `earthdata-varinfo` Python library. This draws heavily from the template
 # used to release the `harmony-service-lib` package (see
 # https://github.com/nasa/harmony-service-lib-py).
 #
 # The produced image will allow targets within the associated Makefile to be
 # run via the `docker run` command, e.g.:
 #
 # $ docker build -t earthdata/varinfo:latest .
 # $ docker run --rm earthdata/varinfo:latest test
 #
 # These commands are encapsulated in bin/build-image.sh and bin/run-test.sh
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
