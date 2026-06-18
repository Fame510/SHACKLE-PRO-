FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY daemon.py state.py audit.py client.py ./

# Create socket directory
RUN mkdir -p /tmp

EXPOSE 8000

CMD ["python", "daemon.py"]
