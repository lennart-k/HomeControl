FROM python:3.7
LABEL MAINTAINER="Lennart K"

VOLUME /config

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt --no-cache-dir

COPY . .

CMD [ "python", "homecontrol", "-cfgfile", "/config/config.yaml" ]
