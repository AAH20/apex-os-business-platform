# APEX-OS Business Platform - Multi-stage Dockerfile

# Stage 1: Frontend build
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --only=production && npm cache clean --force
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend dependencies
FROM python:3.12-slim AS backend-builder
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 3: Frontend server (nginx serving static files)
FROM nginx:1.27-alpine AS frontend-server
COPY --from=frontend-builder /app/frontend/dist /usr/share/nginx/html
COPY nginx/frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

# Stage 4: Production backend image
FROM python:3.12-slim AS production

# Security: Create non-root user
RUN groupadd -r apex && useradd -r -g apex -d /app -s /sbin/nologin apex

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend dependencies
COPY --from=backend-builder /root/.local /home/apex/.local
ENV PATH=/home/apex/.local/bin:$PATH

# Copy backend application
COPY backend/ ./backend/

# Set ownership
RUN chown -R apex:apex /app /home/apex

# Switch to non-root user
USER apex

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
