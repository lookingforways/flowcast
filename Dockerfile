FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate default background image
RUN python scripts/generate_default_bg.py

# Create data directories
RUN mkdir -p /app/data/db /app/data/uploads/backgrounds /app/data/uploads/fonts \
             /app/data/downloads /app/data/renders /app/data/tokens

# Secure token directory
RUN chmod 700 /app/data/tokens

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
