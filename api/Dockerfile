# DigiJordii MVP
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1     PYTHONUNBUFFERED=1     PIP_NO_CACHE_DIR=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     wget     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install deps first (better layer caching)
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy app
COPY ingest ./ingest
COPY server ./server
COPY web ./web

# Default envs
ENV HOST=0.0.0.0     PORT=8787     TOP_K=6

EXPOSE 8787

# Start API
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8787"]
