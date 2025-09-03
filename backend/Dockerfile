# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Expose the port that Cloud Run will use
EXPOSE 8080

# Run the FastAPI server on 0.0.0.0:8080 (Cloud Run requirement)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
