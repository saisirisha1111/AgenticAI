FROM python:3.12.11

# Set working directory
WORKDIR /app

# Copy requirement file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Cloud Run uses port 8080
EXPOSE 8080

# Start the FastAPI app
CMD ["sh", "-c", "uvicorn agents.ingestion_structuring_agent:app --host 0.0.0.0 --port $PORT"]
