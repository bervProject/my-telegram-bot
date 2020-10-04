FROM python:3.8-slim

WORKDIR /usr/src/app
RUN apt-get update && apt-get -y install --no-cache poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD [ "python", "src/telegram_bot.py" ]