FROM python:3.8-alpine

WORKDIR /usr/src/app
RUN apk update && apk add --no-cache poppler-utils
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD [ "python", "src/telegram_bot.py" ]