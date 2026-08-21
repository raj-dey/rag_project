FROM python:3.12-slim

WORKDIR /app

# Set python path environment variable
ENV PYTHONPATH=/app

# Copy frontend requirements and install
COPY frontend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source files
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit on host 0.0.0.0 and port $PORT
CMD ["sh", "-c", "streamlit run frontend/app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
