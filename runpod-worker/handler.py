"""RunPod Serverless handler for TRELLIS.2.

Receives image URLs (or base64) and returns a generated 3D model (GLB) as
base64. The pipeline is loaded once at worker startup, not per request.
"""

import os

# Select the xformers attention backend before TRELLIS is imported anywhere
# (flash-attn is not installed in the image).
os.environ.setdefault("ATTN_BACKEND", "xformers")

import base64  # noqa: E402
import io  # noqa: E402
import tempfile  # noqa: E402
import traceback  # noqa: E402

import requests  # noqa: E402
import runpod  # noqa: E402


def load_pipeline():
    """Load the TRELLIS.2 pipeline once at worker startup."""
    os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

    from trellis.pipelines import TrellisImageTo3DPipeline

    pipeline = TrellisImageTo3DPipeline.from_pretrained(
        "microsoft/TRELLIS-image-large"
    )
    pipeline.cuda()
    return pipeline


print("Loading TRELLIS.2 pipeline...")
PIPELINE = load_pipeline()
print("Pipeline loaded.")


def _download_image(url: str):
    from PIL import Image

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return Image.open(io.BytesIO(response.content)).convert("RGBA")


def _base64_to_image(b64_string: str):
    from PIL import Image

    image_data = base64.b64decode(b64_string)
    return Image.open(io.BytesIO(image_data)).convert("RGBA")


def handler(job):
    """RunPod handler.

    input: {"images": ["url"|b64...], "prompt": str, "order_id": str,
            "output_format": "glb"}
    output: {"model_base64": str, "format": "glb", "order_id": str,
             "size_bytes": int}
    """
    job_input = job.get("input", {})
    images_input = job_input.get("images", [])
    order_id = job_input.get("order_id", "unknown")
    output_format = job_input.get("output_format", "glb")

    if not images_input:
        return {"error": "No images provided"}

    print(f"Processing order {order_id} with {len(images_input)} image(s)")

    try:
        first_image = images_input[0]
        if isinstance(first_image, str) and first_image.startswith("http"):
            image = _download_image(first_image)
        else:
            image = _base64_to_image(first_image)
        print(f"Image loaded: {image.size}")

        print("Running 3D generation...")
        outputs = PIPELINE.run(image, seed=42, formats=[output_format])

        with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as tmp:
            tmp_path = tmp.name

        if output_format == "glb":
            from trellis.utils import postprocessing_utils

            glb = postprocessing_utils.to_glb(
                outputs["gaussian"][0],
                outputs["mesh"][0],
                simplify=0.95,
                texture_size=1024,
            )
            glb.export(tmp_path)

        with open(tmp_path, "rb") as f:
            model_bytes = f.read()
        os.unlink(tmp_path)

        print(f"Model generated: {len(model_bytes)} bytes")
        return {
            "model_base64": base64.b64encode(model_bytes).decode("utf-8"),
            "format": output_format,
            "order_id": order_id,
            "size_bytes": len(model_bytes),
        }

    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        print(f"Generation error: {exc}\n{tb}")
        return {"error": str(exc), "traceback": tb}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
