FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV SPCONV_ALGO=native
ENV ATTN_BACKEND=xformers

RUN apt-get update && apt-get install -y \
    python3.11 python3.11-dev python3-pip \
    git wget curl ninja-build build-essential \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 \
    libxrender-dev libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    pip3 install --upgrade pip

WORKDIR /app

# PyTorch cu124 (torch + torchvision + torchaudio juntos, do índice cu124, para
# o pip resolver o trio CUDA consistente e o torchvision vir com as extensões).
RUN pip3 install torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu124

# Valida no build que o torchvision tem as extensões CUDA (operador nms) antes
# de seguir — falha cedo aqui em vez de só em runtime.
RUN python3 -c "import torchvision; print(torchvision.__version__)" && \
    python3 -c "from torchvision.ops import nms; print('nms OK')"

# xformers do PyPI (não do índice cu124)
RUN pip3 install xformers==0.0.27.post2

# RunPod SDK
RUN pip3 install runpod==1.7.0

# Dependências básicas do TRELLIS (do setup.sh --basic). transformers/diffusers
# PINADOS: as versões atuais assumem torch 2.5+ (transformers importa
# torch.distributed.tensor.device_mesh, que não existe no torch 2.4). Estas são
# da era do TRELLIS e compatíveis com torch 2.4.0 (diffusers 0.31 declara torch<2.5).
RUN pip3 install \
    pillow imageio imageio-ffmpeg tqdm easydict \
    opencv-python-headless scipy ninja rembg onnxruntime \
    trimesh open3d xatlas pyvista pymeshfix igraph \
    transformers==4.46.3 diffusers==0.31.0 accelerate \
    einops plyfile pygltflib omegaconf \
    git+https://github.com/EasternJournalist/utils3d.git@9a4eb15e4021b67b12c460c7057d642626897ec8

# spconv (sparse convolution — obrigatório para TRELLIS)
RUN pip3 install spconv-cu124

# Clona TRELLIS e adiciona ao PYTHONPATH
RUN git clone https://github.com/microsoft/TRELLIS.git /app/TRELLIS

ENV PYTHONPATH=/app/TRELLIS

WORKDIR /app

COPY handler.py .

CMD ["python3", "-u", "handler.py"]
