FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

# Copy package files AND the .npmrc we just created
COPY frontend/package*.json frontend/.npmrc ./

# Use build secret so the token is not stored in image history (--secret id=NODE_AUTH_TOKEN,env=NODE_AUTH_TOKEN)
RUN --mount=type=secret,id=NODE_AUTH_TOKEN \
    export NODE_AUTH_TOKEN=$(cat /run/secrets/NODE_AUTH_TOKEN) && npm ci

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
EXPOSE 5000

CMD ["uv", "run", "main.py", "--host", "0.0.0.0", "--port", "5000", "--log-dir", "/app/logs"]
