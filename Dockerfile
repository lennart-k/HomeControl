FROM python:3.8.6-alpine
LABEL MAINTAINER="Lennart K"

RUN apk add build-base git musl-dev libffi-dev openssl-dev

RUN pip install uvloop

VOLUME /config

RUN mkdir -p /usr/src
WORKDIR /usr/src
COPY . .

RUN scripts/docker_pip_requirements
RUN pip install --compile --no-cache-dir --prefer-binary -e ./
RUN python -m compileall homecontrol

WORKDIR /config

CMD [ "homecontrol", "--cfgdir", "/config" ]
