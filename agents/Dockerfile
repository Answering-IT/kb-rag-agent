# Use official Python runtime
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy agent code
COPY main.py .
COPY metadata_handler.py .

# Expose port 8080 (required by Agent Core Runtime)
EXPOSE 8080

# Run with OpenTelemetry instrumentation
ENTRYPOINT ["opentelemetry-instrument"]
CMD ["python", "main.py"]
