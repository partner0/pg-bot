FROM python:alpine

WORKDIR /pg-bot

ENV PYTHONUNBUFFERED 1

COPY . .

RUN pip3 install -r requirements.txt

CMD [ "gunicorn", "pg-bot-api:app", "--bind", "0.0.0.0:80", "--worker-class", "uvicorn.workers.UvicornWorker", "--timeout", "300", "--log-level", "info" ]