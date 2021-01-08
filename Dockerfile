FROM python:3.8-slim

WORKDIR /app
RUN apt-get update && apt-get install -y poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x ./startup.sh
ENTRYPOINT [ "./startup.sh"]