FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY run_api.py .
COPY data_pipeline/ ./data_pipeline/
COPY frontend/ ./frontend/
COPY entrypoint.sh .
COPY ["Score model/", "/app/Score model/"]

RUN chmod +x entrypoint.sh

ENV PYTHONPATH=/app/src

EXPOSE 8000

CMD ["./entrypoint.sh"]
