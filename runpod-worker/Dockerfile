# Base image with CUDA 12.4 + cuDNN (devel, so nvcc is available for builds).
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV OPENCV_IO_ENABLE_OPENEXR=1
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
# Disable nvdiffrast (not installed); TRELLIS still exports GLB without it.
ENV NVDIFFRAST_DISABLE=1
# Build CUDA extensions for common datacenter + Ada GPUs.
ENV TORCH_CUDA_ARCH_LIST="8.6;8.9;9.0"

RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    git \
    wget \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    ninja-build \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3 /usr/bin/python

RUN pip3 install --upgrade pip

WORKDIR /app

# PyTorch with CUDA 12.4.
RUN pip3 install torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu124

# xformers attention (flash-attn fails to compile in this image; xformers ships
# prebuilt CUDA wheels and TRELLIS supports it via ATTN_BACKEND=xformers).
# Unpinned xformers, but constrain torch/torchvision in the SAME command so pip
# cannot upgrade torch to satisfy a newer xformers — an upgrade would break
# torchvision's compiled ops ("operator torchvision::nms does not exist"). pip
# resolves to the xformers build that matches torch 2.4.0.
RUN pip3 install xformers torch==2.4.0 torchvision==0.19.0 --index-url https://download.pytorch.org/whl/cu124

# RunPod SDK.
RUN pip3 install runpod==1.7.0

# spconv — sparse convolution CUDA backend required by TRELLIS. Prebuilt wheel
# for CUDA 12.4 (matches the base image).
RUN pip3 install spconv-cu124

# TRELLIS Python dependencies.
RUN pip3 install \
    pillow \
    numpy \
    scipy \
    trimesh \
    open3d \
    huggingface_hub \
    transformers \
    diffusers \
    accelerate \
    einops \
    imageio \
    imageio-ffmpeg \
    requests \
    opencv-python-headless \
    easydict \
    omegaconf \
    plyfile \
    pygltflib \
    git+https://github.com/EasternJournalist/utils3d.git@9a4eb15

# nvdiffrast is intentionally omitted: it needs CUDA compilation that fails in
# this build, and TRELLIS only uses it for advanced PBR texture rendering.
# Exporting a GLB for 3D preview works without it (see NVDIFFRAST_DISABLE below).

# Clone TRELLIS. It is NOT a pip-installable package (no setup.py / pyproject.toml),
# so we add it to PYTHONPATH and import it as a module instead of `pip install -e .`.
# Its Python deps (einops, utils3d, etc.) are installed in the pip block above.
RUN git clone https://github.com/microsoft/TRELLIS.git /app/TRELLIS

ENV PYTHONPATH=/app/TRELLIS:$PYTHONPATH

WORKDIR /app

# TRELLIS reads ATTN_BACKEND to pick the attention implementation.
ENV ATTN_BACKEND=xformers

COPY handler.py .

# Optional: pre-download the model weights to speed up cold start (bigger image).
# RUN python3 -c "from trellis.pipelines import TrellisImageTo3DPipeline; TrellisImageTo3DPipeline.from_pretrained('microsoft/TRELLIS-image-large')"

CMD ["python3", "-u", "handler.py"]
