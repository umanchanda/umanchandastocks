FROM ubuntu:18.04

LABEL maintainer="uday.manchanda14@gmail.com"

RUN apt-get update -y && \
    apt-get install -y python3.6 python3-pip python3-dev

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY . /app

ENTRYPOINT [ "python3" ]

CMD [ "app.py" ]