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
 FROM python:3.8-alpine3.13

 WORKDIR /app/
 RUN apk update
 RUN apk add --no-cache make gcc build-base libressl-dev musl-dev libffi-dev
 RUN apk add --no-cache hdf5 hdf5-dev netcdf netcdf-dev

 RUN addgroup -g 500 bamboo
 RUN adduser -D -h /build -G bamboo -u 500 bamboo

 COPY . /app/
 RUN make develop
 RUN make prepare-test

 RUN chown -R bamboo:bamboo .
 USER bamboo

 ENTRYPOINT ["make"]
