# Stage 1: Build Vue frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /build

# Copy frontend source
COPY frontend-vue/ ./frontend-vue/

# Install deps and build (output goes to ../frontend-dist per vite.config.js)
WORKDIR /build/frontend-vue
RUN npm install && npm run build


# Stage 2: Python backend
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies (use root requirements.txt — no pyinstaller)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend (vite outputs to /build/frontend-dist)
COPY --from=frontend-builder /build/frontend-dist ./frontend-dist/

# Run from backend directory so relative paths resolve correctly
WORKDIR /app/backend

EXPOSE 8000

# Render sets $PORT; fall back to 8000 locally
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
