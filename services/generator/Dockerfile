FROM python:3.7.4-slim

RUN apt-get update
COPY requirements.txt /
RUN pip3 install -r /requirements.txt

COPY /server /server
WORKDIR /server