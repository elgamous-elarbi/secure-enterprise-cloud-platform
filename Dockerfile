############################
# Builder
############################

FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

############################
# Runtime
############################

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        wget \
        libpq5 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Création d'un utilisateur non privilégié
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

COPY --from=builder /install /usr/local
COPY . .

RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 5000

CMD ["gunicorn","--bind","0.0.0.0:5000","app:app"]