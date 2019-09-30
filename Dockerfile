FROM python:3.7.3-alpine
LABEL MAINTAINER="Lennart K"

RUN apk add build-base git musl-dev libffi-dev openssl-dev

RUN pip install uvloop

VOLUME /config

RUN mkdir -p /usr/src
WORKDIR /usr/src
COPY . .

RUN pip install -r requirements.txt --no-cache-dir
RUN python setup.py install -O2
RUN pip install $(python -m homecontrol.scripts.module_requirements)

WORKDIR /config

CMD [ "homecontrol", "-cfgdir", "/config" ]
