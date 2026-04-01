FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

ARG VITE_BASE_PATH=/
ENV VITE_BASE_PATH=${VITE_BASE_PATH}

# Copy package manifests.
COPY frontend/package*.json ./

RUN npm ci

COPY frontend/ .
RUN npm run build
FROM python:3.12-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

COPY main.py ./main.py
COPY src/ ./src/
# Copy from the 'frontend-build' stage instead of the local folder
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

ENV LOGS_DIR=/app/logs
ENV IMAGES_DIR=/app/uploads
ENV ROOT_PATH=
EXPOSE 5000

CMD ["uv", "run", "main.py", "--host", "0.0.0.0", "--port", "5000", "--log-dir", "/app/logs"]
