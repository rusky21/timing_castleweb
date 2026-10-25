# ==========================================
# 🏰 CASTLEWEB Backend Dockerfile
# Multi-stage production-ready build
# ==========================================

FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Final Production Stage
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Create non-root user
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash -m appuser

# Pre-create standard directories
RUN mkdir -p /app/uploads /app/data /tmp/uploads && \
    chown -R appuser:appgroup /app /tmp/uploads && \
    chmod 777 /app/uploads /tmp/uploads

# Copy application code and scripts
COPY . .

# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh && \
    chown -R appuser:appgroup /app

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
