# FinAlly — Multi-stage Docker build
# Stage 1: Build Next.js static export
# Stage 2: Python 3.12 runtime with FastAPI serving frontend + API

# --- Stage 1: Frontend build ---
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend

# Install dependencies first (layer caching)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source and build static export
COPY frontend/ ./
RUN npm run build


# --- Stage 2: Python runtime ---
FROM python:3.12-slim AS runtime

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/backend

# Install Python dependencies (layer caching)
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

# Copy backend source
COPY backend/ ./

# Copy frontend build output to /app/frontend/out
# main.py resolves: Path(__file__).parent.parent.parent / "frontend" / "out"
# __file__ = /app/backend/app/main.py -> parent.parent.parent = /app -> /app/frontend/out
COPY --from=frontend-build /app/frontend/out /app/frontend/out

# Create db directory for volume mount
RUN mkdir -p /app/db

# Database path points to volume-mountable directory
ENV DB_PATH=/app/db/finally.db

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
