FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend

ARG FRONTEND_BASE_URL=/

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
ENV FRONTEND_BASE_URL=${FRONTEND_BASE_URL}
RUN FRONTEND_BASE_URL=${FRONTEND_BASE_URL} npm run build

FROM python:3.11-slim AS backend
ARG FRONTEND_BASE_URL=/
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev

COPY pyproject.toml poetry.lock README.md ./

RUN pip install --upgrade pip \
    && pip install --no-cache-dir poetry \
    && poetry self add poetry-plugin-export \
    && poetry export --format requirements.txt --output requirements.txt --without-hashes \
    && pip install --no-cache-dir -r requirements.txt \
    && rm -f requirements.txt

COPY src ./src
COPY scripts ./scripts

RUN pip install --no-cache-dir --no-deps .

COPY --from=frontend-build /app/frontend/dist ./frontend/dist
COPY docker/backend-entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENV SOCIALSIM4_FRONTEND_DIST_PATH=/app/frontend/dist

RUN pip uninstall -y poetry \
    && apt-get purge -y build-essential \
    && apt-get autoremove -y --purge \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
