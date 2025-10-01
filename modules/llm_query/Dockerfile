# Dockerfile for BHIV Core LLM Query Service
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash bhiv
RUN chown -R bhiv:bhiv /app

# Copy requirements and install dependencies
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-security.txt || true
RUN pip install --no-cache-dir -r requirements-threats.txt || true

# Install service-specific dependencies
RUN pip install --no-cache-dir \
    fastapi>=0.104.1 \
    uvicorn[standard]>=0.24.0 \
    httpx>=0.25.0 \
    pydantic>=2.5.0 \
    python-jose[cryptography]>=3.3.0 \
    passlib[bcrypt]>=1.7.4 \
    python-multipart>=0.0.6 \
    prometheus-client>=0.17.0 \
    openai>=1.0.0 \
    anthropic>=0.7.0

# Copy application code
COPY security/ ./security/
COPY agents/ ./agents/
COPY modules/shared/ ./modules/shared/
COPY modules/llm_query/ ./modules/llm_query/

# Switch to non-root user
USER bhiv

# Set environment variables
ENV PYTHONPATH="/app:$PYTHONPATH"
ENV SERVICE_NAME="llm_query"
ENV SERVICE_PORT="8004"

# Expose port
EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Run the service
CMD ["python", "modules/llm_query/service.py"]
