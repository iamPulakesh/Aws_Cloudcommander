FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY commands/ ./commands/
COPY roles.json ./app/roles.json

ENV PYTHONUNBUFFERED=1

CMD ["python", "app/main.py"]
