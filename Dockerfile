# syntax=docker/dockerfile:1

FROM python:3.12.2-slim-bookworm

RUN apt-get update && apt-get upgrade -y

RUN groupadd -r app && useradd -r -g app app

COPY . .

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

WORKDIR ./app

USER app

CMD ["python3", "-u", "app.py"]
