"""Smoke-test the TRELLIS.2 RunPod endpoint with a public image.

Reads RUNPOD_API_KEY and RUNPOD_TRELLIS_ENDPOINT_ID from the environment. Run:

    RUNPOD_API_KEY=... RUNPOD_TRELLIS_ENDPOINT_ID=... \
        uv run python scripts/test_runpod_endpoint.py
"""

from __future__ import annotations

import base64
import json
import os
import sys

import requests

API_KEY = os.environ.get("RUNPOD_API_KEY")
ENDPOINT_ID = os.environ.get("RUNPOD_TRELLIS_ENDPOINT_ID")
if not API_KEY or not ENDPOINT_ID:
    print(
        "ERROR: set RUNPOD_API_KEY and RUNPOD_TRELLIS_ENDPOINT_ID first.",
        file=sys.stderr,
    )
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "input": {
        "images": ["https://picsum.photos/seed/test/512/512"],
        "prompt": "test 3d object",
        "order_id": "test-001",
        "output_format": "glb",
    }
}

response = requests.post(
    f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync",
    headers=headers,
    json=payload,
    timeout=300,
)
print(f"Status: {response.status_code}")
result = response.json()

output = result.get("output") or {}
if output.get("model_base64"):
    model_bytes = base64.b64decode(output["model_base64"])
    with open("test_output.glb", "wb") as f:
        f.write(model_bytes)
    print(f"Success! Saved test_output.glb ({len(model_bytes)} bytes)")
else:
    print(json.dumps(result, indent=2))
