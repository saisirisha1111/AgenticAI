# Dockerfiles
FROM python:3.12.11
WORKDIR /Demoapp
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8080
CMD uvicorn agents.ingestion_structuring_agent:app --host 0.0.0.0 --port $PORT