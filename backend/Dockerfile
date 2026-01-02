FROM python:3.11

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY . .

# Create non-root user for security
# Add user to dialout group for serial port access (Linux)
RUN useradd -m -u 1000 -G dialout appuser && chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
