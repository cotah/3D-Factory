"""RunPod Serverless handler for TRELLIS.2.

Receives image URLs (or base64) and returns a generated 3D model (GLB) as
base64.

The pipeline is lazy-loaded on the FIRST job (not at import time). If loading
fails, the error surfaces as a JSON ``{"error": ...}`` in the job response
instead of crashing the worker before it can register — a crash at import time
shows up to the caller only as an opaque 404.
"""

import base64
import io
import os
import tempfile
import traceback

import requests
import runpod

# Loaded lazily on first use; see get_pipeline().
PIPELINE = None


def get_pipeline():
    """Load the TRELLIS.2 pipeline once, on first use."""
    global PIPELINE
    if PIPELINE is None:
        # Configure TRELLIS backends before it is imported: xformers attention
        # (flash-attn not installed) and disable nvdiffrast (only needed for
        # advanced PBR texture rendering, not for GLB export).
        os.environ.setdefault("ATTN_BACKEND", "xformers")
        os.environ.setdefault("NVDIFFRAST_DISABLE", "1")
        os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

        from trellis.pipelines import TrellisImageTo3DPipeline

        pipeline = TrellisImageTo3DPipeline.from_pretrained(
            "microsoft/TRELLIS-image-large"
        )
        pipeline.cuda()
        PIPELINE = pipeline
    return PIPELINE


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

    Any failure (including pipeline load) returns a JSON error rather than
    raising, so the worker stays alive and the cause is visible in the response.
    """
    try:
        job_input = job.get("input", {})
        images_input = job_input.get("images", [])
        order_id = job_input.get("order_id", "unknown")
        output_format = job_input.get("output_format", "glb")

        if not images_input:
            return {"error": "No images provided"}

        print(f"Processing order {order_id} with {len(images_input)} image(s)")

        # Lazy-load on first request; a failure here is caught below.
        print("Loading TRELLIS.2 pipeline (first request)...")
        pipeline = get_pipeline()
        print("Pipeline ready.")

        first_image = images_input[0]
        if isinstance(first_image, str) and first_image.startswith("http"):
            image = _download_image(first_image)
        else:
            image = _base64_to_image(first_image)
        print(f"Image loaded: {image.size}")

        print("Running 3D generation (mesh only)...")
        outputs = pipeline.run(image, seed=42, formats=["mesh"])
        mesh = outputs["mesh"][0]

        # Geometry-only export via trimesh. Avoids the textured to_glb() path,
        # which needs the nvdiffrast + diff_gaussian_rasterization CUDA
        # extensions (deferred to a later phase). For 3D printing the geometry
        # is what matters; vertex colors are included when available for a
        # nicer preview.
        import trimesh as _trimesh

        vertices = mesh.vertices.detach().cpu().numpy()
        faces = mesh.faces.detach().cpu().numpy()
        tm = _trimesh.Trimesh(vertices=vertices, faces=faces)
        try:
            attrs = mesh.vertex_attrs.detach().cpu().numpy()
            if attrs.ndim == 2 and attrs.shape[1] >= 3:
                colors = (attrs[:, :3].clip(0, 1) * 255).astype("uint8")
                tm.visual.vertex_colors = colors
        except Exception:  # noqa: BLE001
            pass

        with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as tmp:
            tmp_path = tmp.name
        tm.export(tmp_path)

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
        print(f"Handler error: {exc}\n{tb}")
        return {"error": str(exc), "traceback": tb}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
