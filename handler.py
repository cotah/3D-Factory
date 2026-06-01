"""Root-level RunPod entrypoint marker.

RunPod's GitHub build scans the repository root for ``runpod.serverless.start``
to validate that the repo is a serverless worker. The real implementation lives
in ``runpod-worker/handler.py`` (that's what the Docker image copies and runs via
its CMD). This thin shim exists so the scan succeeds; it lazily delegates to the
worker implementation if it is ever executed directly from the repo root.
"""

import importlib.util
import os

import runpod

_WORKER_HANDLER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "runpod-worker", "handler.py"
)

_impl = None


def _load():
    """Load runpod-worker/handler.py by path (lazy — only when first called)."""
    global _impl
    if _impl is None:
        spec = importlib.util.spec_from_file_location(
            "trellis_worker_handler", _WORKER_HANDLER
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _impl = module.handler
    return _impl


def handler(job):
    return _load()(job)


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
