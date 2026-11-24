# Etapa 1 (builder): imagen slim por su bajo peso y compatibilidad con wheels
# de Python (evita los fallos de compilación habituales en imágenes Alpine).
FROM python:3.12-slim AS builder

WORKDIR /build

# Se copia requirements.txt antes del código fuente para aprovechar la caché
# de capas de Docker y no reinstalar dependencias ante cambios solo en app/.
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Etapa 2 (runtime): imagen final limpia únicamente con las dependencias
# instaladas y el código de ejecución, sin herramientas de compilación.
FROM python:3.12-slim

WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/

# Principio de mínimo privilegio: usuario no root con UID/GID numérico fijo
# para cumplir Hadolint (DL3066) y políticas runAsNonRoot en Kubernetes.
RUN groupadd --gid 10001 appgroup \
    && useradd --uid 10001 --gid appgroup --create-home --shell /bin/bash appuser
USER 10001:10001

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
