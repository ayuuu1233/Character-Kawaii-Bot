FROM python:3.10-slim-bullseye

RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    bash \
    curl \
    git \
    libffi-dev \
    libjpeg-dev \
    libwebp-dev \
    libpq-dev \
    python3-dev \
    gcc \
    ffmpeg \
    libopus0 \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/
WORKDIR /app/

RUN pip3 install --no-cache-dir -U -r requirements.txt

CMD ["python3", "-m", "shivu"]
