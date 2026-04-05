FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/data/huggingface

WORKDIR /workspace

COPY eval/local_intelligence/job-requirements.txt /tmp/job-requirements.txt

RUN python -m pip install --upgrade pip && \
    python -m pip install -r /tmp/job-requirements.txt

