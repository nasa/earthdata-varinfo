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
 ##############################################################################
 FROM python:3.8-alpine

 WORKDIR /app/
 RUN apk update
 RUN apk add --no-cache make build-base libffi-dev

 RUN addgroup -g 500 bamboo
 RUN adduser -D -h /build -G bamboo -u 500 bamboo

 COPY . /app/
 RUN make develop
 RUN make prepare-test

 RUN chown -R bamboo:bamboo .
 USER bamboo

 ENTRYPOINT ["make"]
