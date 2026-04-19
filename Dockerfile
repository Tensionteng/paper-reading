# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python backend
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy backend files
COPY backend/pyproject.toml ./
COPY backend/app ./app

# Install Python dependencies
RUN uv pip install --system -e .

# Copy frontend build artifacts
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create data directories
RUN mkdir -p /app/data/papers /app/data/images

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
