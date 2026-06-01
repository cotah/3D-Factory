"""Create the TRELLIS.2 serverless endpoint on RunPod.

The API key is read from the RUNPOD_API_KEY environment variable so it is never
committed. Run with:

    RUNPOD_API_KEY=... uv run python scripts/create_runpod_endpoint.py
"""

from __future__ import annotations

import json
import os
import sys

import requests

API_KEY = os.environ.get("RUNPOD_API_KEY")
if not API_KEY:
    print("ERROR: set RUNPOD_API_KEY in the environment first.", file=sys.stderr)
    sys.exit(1)

IMAGE_NAME = os.environ.get(
    "RUNPOD_IMAGE", "tuxeai/trellis2-runpod-worker:v1.0"
)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "name": "trellis2-3d-generation",
    "imageName": IMAGE_NAME,
    "gpuIds": "NVIDIA GeForce RTX 4090,NVIDIA RTX A5000",
    "minWorkers": 0,
    "maxWorkers": 1,
    "idleTimeout": 5,
    "scalerType": "QUEUE_DEPTH",
    "scalerValue": 1,
    "executionTimeoutMs": 300000,
}

response = requests.post(
    "https://api.runpod.io/v2/endpoint",
    headers=headers,
    json=payload,
    timeout=60,
)

print(f"Status: {response.status_code}")
try:
    body = response.json()
    print(json.dumps(body, indent=2))
    endpoint_id = body.get("id")
    if endpoint_id:
        print(f"\nEndpoint ID: {endpoint_id}")
        print(f"Set on Railway: RUNPOD_TRELLIS_ENDPOINT_ID={endpoint_id}")
except ValueError:
    print(response.text)
