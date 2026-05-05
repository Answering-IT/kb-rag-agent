# ProcessApp Agent v2.0 - Docker Image
# Multi-stage build for optimized container size

FROM python:3.12-slim as base

# Set working directory
WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy agent code (modular structure)
COPY main.py .
COPY core/ ./core/
COPY prompts/ ./prompts/

# Expose port 8080 (required by Agent Core Runtime)
EXPOSE 8080

# Environment variables (can be overridden)
ENV PORT=8080
ENV MODEL_ID=amazon.nova-pro-v1:0
ENV AWS_REGION=us-east-1
ENV DEBUG=false

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8080/health')"

# Run with OpenTelemetry instrumentation
ENTRYPOINT ["opentelemetry-instrument"]
CMD ["python", "main.py"]
