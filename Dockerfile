FROM python:3.7.2
LABEL MAINTAINER="Lennart K"

VOLUME /config

RUN mkdir -p /usr/src
WORKDIR /usr/src
COPY . .

RUN pip install -r requirements.txt --no-cache-dir
RUN python setup.py install -O2
RUN pip install $(python -m homecontrol.scripts.module_requirements)

WORKDIR /config

CMD [ "homecontrol", "-cfgfile", "/config/config.yaml" ]
