# TRELLIS.2 RunPod Worker

Serverless worker that turns an input image into a 3D model (GLB) using
Microsoft TRELLIS-image-large.

## Build & push

```bash
docker login -u tuxeai          # needs a Docker Hub password / access token
cd runpod-worker
DOCKER_USERNAME=tuxeai TAG=v1.0 ./build_and_push.sh
# (or) docker build --platform linux/amd64 -t tuxeai/trellis2-runpod-worker:v1.0 .
#      docker push tuxeai/trellis2-runpod-worker:v1.0
```

The build is large (~15-20GB, 20-40 min): it installs CUDA wheels, compiles
flash-attn, and installs TRELLIS.

## Create the RunPod endpoint

```bash
export RUNPOD_API_KEY=...        # never commit this
uv run python backend/scripts/create_runpod_endpoint.py
```

## Configure the backend (Railway)

```bash
railway variables --service 3D-Factory \
  --set "RUNPOD_API_KEY=..." \
  --set "RUNPOD_TRELLIS_ENDPOINT_ID=<id from create script>" \
  --set "RUNPOD_MOCK_MODE=false"   # only after the endpoint is verified!
```

## Test

```bash
export RUNPOD_API_KEY=...
export RUNPOD_TRELLIS_ENDPOINT_ID=...
uv run python backend/scripts/test_runpod_endpoint.py
```

## Handler contract

Input: `{"images": ["url"|b64], "prompt": str, "order_id": str, "output_format": "glb"}`
Output: `{"model_base64": str, "format": "glb", "order_id": str, "size_bytes": int}`
