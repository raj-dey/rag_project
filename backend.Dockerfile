FROM python:3.12-slim

WORKDIR /app

# Set python path environment variable
ENV PYTHONPATH=/app

# Install system dependencies (build-essential for compilation if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Optimize torch installation for CPU-only (saves ~1.5 GB in image size)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source files
COPY . .

# Expose port (Cloud Run sets PORT env var)
EXPOSE 8000

# Run backend main using uvicorn
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
