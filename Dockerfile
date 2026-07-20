# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# No se necesita gcc: ccxt, pandas, python-telegram-bot tienen wheels precompilados
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    find /usr/local -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

COPY . .

CMD ["python", "-m", "src.main"]
