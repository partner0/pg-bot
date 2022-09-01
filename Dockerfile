FROM python:alpine

WORKDIR /pg-bot

COPY . .

RUN pip3 install -r requirements.txt

CMD [ "uvicorn", "--host", "0.0.0.0", "--port", "80", "pg-bot-api:app" ]