FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and startup script
COPY app.py .
COPY start.sh .
RUN chmod +x start.sh

# Expose port
EXPOSE 8080

# Run the app
CMD ["./start.sh"]
