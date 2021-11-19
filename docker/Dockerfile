FROM python:buster

RUN apt update && \
    apt upgrade -y

ENV DEBIAN_FRONTEND="noninteractive" TZ="UTC"

RUN apt install -y git curl

# Python build stuff
#RUN apt install -y libssl-dev zlib1g-dev \
#    libbz2-dev libreadline-dev libsqlite3-dev \
#    libncursesw5-dev tk-dev libxmlsec1-dev libffi-dev python-dev

ADD files/startup.sh /startup.sh
ADD files/debug.sh /debug.sh
