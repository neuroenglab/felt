FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

ARG VITE_BASE_PATH=/
ENV VITE_BASE_PATH=${VITE_BASE_PATH}

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
# vite.config.ts writes the bundle to ../src/felt/static
RUN mkdir -p /app/src/felt && npm run build

FROM python:3.12-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/
COPY --from=frontend-build /app/src/felt/static ./src/felt/static
RUN uv sync --no-dev

ENV LOGS_DIR=/app/logs
ENV IMAGES_DIR=/app/uploads
ENV ROOT_PATH=
EXPOSE 5000

CMD ["uv", "run", "felt", "--host", "0.0.0.0", "--port", "5000"]
