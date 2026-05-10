FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

# System dependencies:
RUN apt-get update && apt-get install -y --no-install-recommends \
    stockfish \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# sym link to stockfish
RUN if [ -x /usr/games/stockfish ]; then ln -sf /usr/games/stockfish /usr/local/bin/stockfish; fi

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

RUN mkdir -p chess_com_data/chess_data_cache \
    && mkdir -p twic/data \
    && mkdir -p outputs

ENV STOCKFISH_PATH=/usr/local/bin/stockfish
ENV CHESS_API_BASE_URL=http://api:8000/api/v1

EXPOSE 8000
EXPOSE 8501