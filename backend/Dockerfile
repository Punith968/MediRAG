# ---------------------------------------------------------------------------
# MediRAG backend — production image
#
# Base: Official PyTorch image with CUDA 11.8 + cuDNN 8
#   - torch, torchvision, torchaudio already installed (CUDA build)
#   - Do NOT reinstall torch from PyPI; requirements.txt deliberately omits them
# ---------------------------------------------------------------------------
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

WORKDIR /app

# System packages
#   ffmpeg      — required by openai-whisper for audio decoding
#   libsm6      — required by OpenCV (indirect dep of some ML libs)
#   libxext6    — same
#   git         — needed by some HuggingFace model downloads at runtime
#
# DEBIAN_FRONTEND=noninteractive + TZ prevent tzdata from blocking on an
# interactive timezone prompt during apt-get install inside Docker.
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Etc/UTC

RUN apt-get update -o Acquire::Retries=5 && \
    apt-get install -y --no-install-recommends -o Acquire::Retries=5 \
        tzdata \
        ffmpeg \
        libsm6 \
        libxext6 \
        git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and build tools first
RUN pip install --no-cache-dir --upgrade pip "setuptools<81" wheel

# Install openai-whisper BEFORE requirements.txt so its torch dependency
# resolves against the pre-installed CUDA build, not a fresh CPU wheel.
RUN pip install --no-cache-dir --no-build-isolation openai-whisper==20231117

# Application dependencies (torch/torchvision/torchaudio intentionally absent)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Temp directory for audio processing
RUN mkdir -p /tmp/medirag
ENV MEDIRAG_TMP_DIR=/tmp/medirag

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]