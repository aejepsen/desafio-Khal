# GPU: nvidia/cuda runtime (libcublas). Requer --gpus all / compose gpus: all.
FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv ffmpeg \
    && rm -rf /var/lib/apt/lists \
    && ln -sf /usr/bin/python3 /usr/bin/python

COPY requirements.txt .
RUN pip3 install --upgrade pip && pip3 install -r requirements.txt

COPY app.py .

EXPOSE 8210
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8210"]
