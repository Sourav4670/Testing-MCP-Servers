# ── Build stage (compile nothing, just install) ────────────────────────────
FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency specification first (layer-caching)
COPY pyproject.toml ./

# Install the package in editable mode so the src/ import path works
COPY src/ src/
RUN pip install --no-cache-dir -e .

# ── Runtime image ──────────────────────────────────────────────────────────
FROM base AS runtime

COPY . .

# Default: start in streamable-http mode so Docker works out-of-the-box
# Override with:  docker run ... --mode sse
EXPOSE 8080
ENTRYPOINT ["python", "-m", "travel_advisor"]
CMD ["--mode", "streamable-http", "--host", "0.0.0.0", "--port", "8080"]
