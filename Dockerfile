# Stage 1: Build stage
FROM python:3.13-slim AS build-stage

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.1.14

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    certbot \
    python3-certbot-nginx \
    antiword \
    curl \
    wget \
    gcc \
    cron \
    procps \
    libicu-dev \
    pkg-config \
    build-essential \
    net-tools \
    dnsutils \
    musl-dev \
    libpq-dev \
    postgresql-client \
    osm2pgsql \
    netcat-traditional \
    inetutils-ping \
    telnet \
    ntp \
    poppler-utils \
    libreoffice-core \
    libreoffice-writer \
    && rm -rf /var/lib/apt/lists/*

# Install NTP
RUN ntpd -gq
ENV TZ=Europe/Vienna
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install Poetry and Python dependencies
RUN pip install --upgrade pip \
  && pip install gunicorn \
  && pip install poetry \
  && pip install psycopg2-binary

# Copy the entire project directory
COPY . /code
WORKDIR /code

RUN ls -la

RUN if [ -f .env ]; then cat .env; fi

# Project initialization:
RUN rm -rf /code/.venv && poetry config virtualenvs.create false && poetry install --no-interaction --no-ansi --no-root

# Temp Environment Workaround
COPY .env.devel .env

# Expose ports
EXPOSE 80 443

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "backend.main:app", "--bind", "0.0.0.0:80"]
