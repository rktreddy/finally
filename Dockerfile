# Stage 1: Build frontend static export
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

# Install dependencies first (cache layer)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source and build
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend + static files
FROM python:3.12-slim

WORKDIR /app

# Install uv via official installer (auto-detects platform)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx && \
    apt-get purge -y curl && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

# Copy backend project files and install dependencies
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./backend/
WORKDIR /app/backend
RUN uv sync --frozen --no-dev

# Copy backend source
COPY backend/ ./

# Copy frontend build output to static directory
# backend/app/main.py expects static/ as sibling to app/ (i.e., backend/static/)
COPY --from=frontend-build /app/frontend/out /app/backend/static

# Create db directory for volume mount
RUN mkdir -p /app/db

WORKDIR /app

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "--directory", "/app/backend", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
