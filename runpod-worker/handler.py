import base64
import gc
import io
import os
import signal
import subprocess
import tempfile
import threading
import time
import traceback
import faulthandler
from typing import Any, Dict, List

import requests
import runpod


os.environ.setdefault("ATTN_BACKEND", "xformers")
os.environ.setdefault("NVDIFFRAST_DISABLE", "1")
os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("SPCONV_ALGO", "native")

faulthandler.enable(all_threads=True)

PIPELINE = None
MONITOR_STARTED = False


def log(message: str) -> None:
    print(f"[TRELLIS_WORKER] {time.strftime('%Y-%m-%d %H:%M:%S')} | {message}", flush=True)


def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as file:
            return file.read().strip()
    except Exception:
        return ""


def get_proc_memory_mb() -> float:
    status = read_text("/proc/self/status")

    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            parts = line.split()
            if len(parts) >= 2:
                return round(int(parts[1]) / 1024, 2)

    return -1.0


def get_cgroup_memory_mb() -> float:
    paths = [
        "/sys/fs/cgroup/memory.current",
        "/sys/fs/cgroup/memory/memory.usage_in_bytes",
    ]

    for path in paths:
        value = read_text(path)
        if value.isdigit():
            return round(int(value) / 1024 / 1024, 2)

    return -1.0


def get_cgroup_memory_limit_mb() -> float:
    paths = [
        "/sys/fs/cgroup/memory.max",
        "/sys/fs/cgroup/memory/memory.limit_in_bytes",
    ]

    for path in paths:
        value = read_text(path)
        if value.isdigit():
            limit = int(value)
            if 0 < limit < 10**18:
                return round(limit / 1024 / 1024, 2)

    return -1.0


def get_nvidia_smi() -> str:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.used,memory.total,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )

        output = result.stdout.strip() or result.stderr.strip()
        return output if output else "nvidia-smi returned empty output"

    except Exception as exc:
        return f"nvidia-smi unavailable: {exc}"


def snapshot(stage: str) -> None:
    try:
        import torch

        if torch.cuda.is_available():
            cuda_allocated = round(torch.cuda.memory_allocated() / 1024 / 1024, 2)
            cuda_reserved = round(torch.cuda.memory_reserved() / 1024 / 1024, 2)
            cuda_max_allocated = round(torch.cuda.max_memory_allocated() / 1024 / 1024, 2)
        else:
            cuda_allocated = -1.0
            cuda_reserved = -1.0
            cuda_max_allocated = -1.0

    except Exception:
        cuda_allocated = -1.0
        cuda_reserved = -1.0
        cuda_max_allocated = -1.0

    log(
        f"{stage} | "
        f"proc_rss_mb={get_proc_memory_mb()} | "
        f"cgroup_mem_mb={get_cgroup_memory_mb()} | "
        f"cgroup_limit_mb={get_cgroup_memory_limit_mb()} | "
        f"torch_cuda_allocated_mb={cuda_allocated} | "
        f"torch_cuda_reserved_mb={cuda_reserved} | "
        f"torch_cuda_max_allocated_mb={cuda_max_allocated} | "
        f"gpu=[{get_nvidia_smi()}]"
    )


def monitor_loop() -> None:
    while True:
        snapshot("heartbeat")
        time.sleep(5)


def start_monitor_once() -> None:
    global MONITOR_STARTED

    if MONITOR_STARTED:
        return

    MONITOR_STARTED = True

    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()


def handle_sigterm(signum, frame) -> None:
    snapshot(f"received_signal_{signum}")
    raise SystemExit(f"Received signal {signum}")


signal.signal(signal.SIGTERM, handle_sigterm)


def get_pipeline():
    global PIPELINE

    if PIPELINE is None:
        snapshot("before_pipeline_import")

        from trellis.pipelines import TrellisImageTo3DPipeline

        snapshot("before_pipeline_from_pretrained")

        pipeline = TrellisImageTo3DPipeline.from_pretrained(
            "microsoft/TRELLIS-image-large"
        )

        snapshot("before_pipeline_cuda")

        pipeline.cuda()

        snapshot("after_pipeline_cuda")

        PIPELINE = pipeline

    return PIPELINE


def download_image(url: str):
    from PIL import Image

    response = requests.get(url, timeout=60)
    response.raise_for_status()

    return Image.open(io.BytesIO(response.content)).convert("RGBA")


def base64_to_image(b64_string: str):
    from PIL import Image

    if "," in b64_string and b64_string.strip().startswith("data:"):
        b64_string = b64_string.split(",", 1)[1]

    image_data = base64.b64decode(b64_string)
    return Image.open(io.BytesIO(image_data)).convert("RGBA")


def load_first_image(images_input: List[str]):
    first_image = images_input[0]

    if isinstance(first_image, str) and first_image.startswith("http"):
        return download_image(first_image)

    return base64_to_image(first_image)


def to_numpy(value):
    if hasattr(value, "detach"):
        return value.detach().cpu().numpy()

    return value


def export_mesh_to_glb(mesh, output_format: str = "glb") -> bytes:
    import trimesh

    vertices = to_numpy(mesh.vertices)
    faces = to_numpy(mesh.faces)

    tm = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    try:
        attrs = to_numpy(mesh.vertex_attrs)

        if attrs.ndim == 2 and attrs.shape[1] >= 3:
            colors = (attrs[:, :3].clip(0, 1) * 255).astype("uint8")
            tm.visual.vertex_colors = colors

    except Exception:
        pass

    with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        tm.export(tmp_path)

        with open(tmp_path, "rb") as file:
            return file.read()

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


def get_generation_kwargs(job_input: Dict[str, Any]) -> Dict[str, Any]:
    seed = int(job_input.get("seed", 42))

    sparse_steps = int(job_input.get("sparse_steps", 4))
    slat_steps = int(job_input.get("slat_steps", 4))

    sparse_cfg = float(job_input.get("sparse_cfg", 7.5))
    slat_cfg = float(job_input.get("slat_cfg", 3.0))

    return {
        "seed": seed,
        "formats": ["mesh"],
        "sparse_structure_sampler_params": {
            "steps": sparse_steps,
            "cfg_strength": sparse_cfg,
        },
        "slat_sampler_params": {
            "steps": slat_steps,
            "cfg_strength": slat_cfg,
        },
    }


def run_generation(pipeline, image, job_input: Dict[str, Any]):
    import torch

    generation_kwargs = get_generation_kwargs(job_input)

    with torch.inference_mode():
        with torch.autocast(device_type="cuda", dtype=torch.float16):
            try:
                return pipeline.run(image, **generation_kwargs)

            except TypeError as exc:
                log(f"pipeline.run did not accept sampler params. Falling back to minimal call. Error: {exc}")

                return pipeline.run(
                    image,
                    seed=int(job_input.get("seed", 42)),
                    formats=["mesh"],
                )


def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    start_monitor_once()

    try:
        import torch

        job_input = job.get("input", {})

        images_input = job_input.get("images", [])
        order_id = job_input.get("order_id", "unknown")
        output_format = job_input.get("output_format", "glb")

        if output_format not in ["glb", "obj", "ply"]:
            return {
                "error": "Invalid output_format",
                "allowed_formats": ["glb", "obj", "ply"],
            }

        if not images_input:
            return {
                "error": "No images provided",
                "expected_input": {
                    "images": ["https://example.com/image.png"],
                    "output_format": "glb",
                    "order_id": "debug-001",
                },
            }

        snapshot(f"job_start order_id={order_id}")

        pipeline = get_pipeline()

        snapshot("pipeline_ready")

        image = load_first_image(images_input)

        snapshot(f"image_loaded size={image.size}")

        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

        snapshot("before_generation")

        outputs = run_generation(pipeline, image, job_input)

        snapshot("after_generation")

        mesh = outputs["mesh"][0]

        snapshot("before_export")

        model_bytes = export_mesh_to_glb(mesh, output_format=output_format)

        snapshot("after_export")

        try:
            del outputs
            del mesh
            del image
        except Exception:
            pass

        gc.collect()
        torch.cuda.empty_cache()

        snapshot("job_finished")

        return {
            "model_base64": base64.b64encode(model_bytes).decode("utf-8"),
            "format": output_format,
            "order_id": order_id,
            "size_bytes": len(model_bytes),
            "debug": {
                "seed": int(job_input.get("seed", 42)),
                "sparse_steps": int(job_input.get("sparse_steps", 4)),
                "slat_steps": int(job_input.get("slat_steps", 4)),
                "sparse_cfg": float(job_input.get("sparse_cfg", 7.5)),
                "slat_cfg": float(job_input.get("slat_cfg", 3.0)),
            },
        }

    except BaseException as exc:
        tb = traceback.format_exc()

        log(f"Handler error: {exc}\n{tb}")

        snapshot("handler_exception")

        return {
            "error": str(exc),
            "traceback": tb,
        }


if __name__ == "__main__":
    snapshot("worker_boot")
    runpod.serverless.start({"handler": handler})
