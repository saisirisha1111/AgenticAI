# Dockerfile
FROM python:3.12.11
WORKDIR /Demoapp
COPY requiremnets.txt .
RUN pip install -r requiremnets.txt
COPY . .
EXPOSE 8000
CMD uvicorn agents.ingestion_structuring_agent:app --host 0.0.0.0 --port $PORT