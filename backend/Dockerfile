# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv pip install --system -e .

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/questions/ ./data/questions/
COPY data/images/ ./data/images/

# Create data directory for SQLite database
RUN mkdir -p /data

# Set environment variables
ENV DATABASE_URL="sqlite+aiosqlite:////data/tutor.db"
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Run uvicorn directly - seeding happens in lifespan
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
