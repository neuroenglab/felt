FROM node:22-alpine AS frontend-build

# Define that we expect a token during build time
ARG NODE_AUTH_TOKEN

WORKDIR /app/frontend

# Copy package files AND the .npmrc we just created
COPY frontend/package*.json frontend/.npmrc ./

# npm ci will now use the NODE_AUTH_TOKEN passed from the build command
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
# Copy from the 'frontend-build' stage instead of the local folder
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

ENV LOGS_DIR=/app/logs
EXPOSE 5000

CMD ["uv", "run", "main.py", "--host", "0.0.0.0", "--port", "5000", "--log-dir", "/app/logs"]
