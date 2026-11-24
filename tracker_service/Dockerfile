# Etapa 1 (builder): construcción multietapa con python:3.12-slim para
# aislar la instalación de dependencias de la imagen final de ejecución.
FROM python:3.12-slim AS builder

WORKDIR /build

# Copia aislada de requirements.txt para maximizar la reutilización de caché.
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Etapa 2 (runtime): imagen final minimalista solo con paquetes y código.
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/

# Usuario no privilegiado con UID/GID numérico (cumple Hadolint DL3066).
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --create-home --shell /bin/bash appuser
USER 10001:10001

EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
