# builder: Instala dependências Python (inclui toolchain de compilação)
FROM python:3.12-slim AS builder
WORKDIR /app

# gcc + default-libmysqlclient-dev: necessário para compliar dependências.
# nativas de algumas libs (cryptography, já trazem wheels na marioria dos casos, mas o build fica resiliente a plataformas sem wheel pronto)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copiar só o requirements.txt primerio: esta camada só é invalidada quando
# uma dependência muda, não a cada alteração de código-fonte.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --user -r requirements.txt

# runtime: imagem final, sem toolchain de build
FROM python:3.12-slim AS runtime
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appgroup && useradd -r -g appgroup -d /app appuser

COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

COPY --chown=appuser:appgroup . .
RUN chmod +x docker-entrypoint.sh \
    && mkdir -p uploads && chown appuser:appgroup uploads

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
# 1 worker: ver PRD seção 2.4 (uploads em disco local + rate limit em memória
# de processo tornam >1 worker/réplica incorreto com o código atual).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
