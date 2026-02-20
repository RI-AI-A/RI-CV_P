# CV Backend Dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    g++ \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Pre-install heavy AI libraries so Docker permanently caches them before reading requirements
RUN pip install --default-timeout=1000 ultralytics==8.1.11 opencv-python-headless==4.9.0.80 torch==2.2.0

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with extended timeout for large AI models
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
