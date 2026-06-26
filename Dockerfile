FROM python:3.11-slim
WORKDIR /app

# Install postgresql-client for backup/restore operations
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY index.html .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4999"]
