FROM python:3.7.2-stretch
LABEL MAINTAINER="Lennart K"

VOLUME /config

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt --no-cache-dir

COPY . .

RUN ln -s /config /usr/src/app

CMD [ "python", "homecontrol", "-cfgfile", "/config/config.yaml" ]
