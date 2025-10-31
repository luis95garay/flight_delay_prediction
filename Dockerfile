# syntax=docker/dockerfile:1.2
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies (only production dependencies)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY challenge/ ./challenge/
COPY data/ ./data/
COPY start.sh ./

# Make start script executable and fix line endings
RUN sed -i.bak 's/\r$//' start.sh && rm -f start.sh.bak && chmod +x start.sh

# Make start script executable
RUN chmod +x start.sh

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["./start.sh"]