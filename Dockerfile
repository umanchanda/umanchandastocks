FROM python:3.11-slim

LABEL maintainer="uday.manchanda14@gmail.com"

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENTRYPOINT ["python"]

CMD ["application.py"]
