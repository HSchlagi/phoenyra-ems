FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Copy application code
COPY . /app

# Create necessary directories
RUN mkdir -p /app/data /app/logs

# Set environment variables
ENV FLASK_APP=web.app:app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "web.app:app"]
