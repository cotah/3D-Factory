"""Mesh validation and repair using Trimesh.

``validate(path)`` returns a structured report (watertight/manifold, vertex and
face counts, bounding box, volume, supports/flat-base heuristics, issues and
warnings). ``attempt_repair(path)`` tries to make a non-watertight mesh
printable and writes a repaired copy.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class MeshReport:
    is_valid: bool
    is_manifold: bool
    vertex_count: int
    face_count: int
    bounding_box_mm: dict = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    estimated_volume_cm3: float = 0.0
    needs_supports: bool = False
    has_flat_base: bool = False
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    repair_attempted: bool = False
    repair_succeeded: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def _load_mesh(path: str):
    import trimesh

    loaded = trimesh.load(path, force="mesh")
    if not isinstance(loaded, trimesh.Trimesh) or loaded.is_empty:
        raise ValueError("File did not load as a non-empty mesh")
    return loaded


def validate(path: str) -> MeshReport:
    """Validate a mesh file and return a structured report.

    A file that cannot be loaded as a mesh yields an invalid report (rather
    than raising), so callers can route it like any other failure.
    """
    try:
        mesh = _load_mesh(path)
    except Exception as exc:  # noqa: BLE001
        return MeshReport(
            is_valid=False,
            is_manifold=False,
            vertex_count=0,
            face_count=0,
            issues=[f"Could not load mesh: {type(exc).__name__}"],
        )

    extents = mesh.extents.tolist() if mesh.extents is not None else [0, 0, 0]
    width, depth, height = (extents + [0, 0, 0])[:3]
    bounding_box = {
        "x": round(float(width), 3),
        "y": round(float(depth), 3),
        "z": round(float(height), 3),
    }

    # Volume is in the mesh's own units cubed; treat as mm^3 -> cm^3.
    try:
        volume_cm3 = round(abs(float(mesh.volume)) / 1000.0, 3)
    except Exception:  # noqa: BLE001
        volume_cm3 = 0.0

    footprint = max(width, depth) or 1.0
    needs_supports = height > footprint * 1.5

    # Flat-base heuristic: enough vertices sit near the lowest Z plane.
    has_flat_base = False
    try:
        z_min = float(mesh.bounds[0][2])
        threshold = (height or 1.0) * 0.02
        near_bottom = (mesh.vertices[:, 2] - z_min) < threshold
        has_flat_base = bool(near_bottom.sum() >= 3)
    except Exception:  # noqa: BLE001
        has_flat_base = False

    # Blocking issues fail validation; warnings are advisory (handled in the
    # slicer). Flipped normals are blocking; non-watertight is a common, fixable
    # warning so the preview/approval flow can still proceed.
    issues: list[str] = []
    if not mesh.is_winding_consistent:
        issues.append("Mesh has inconsistent face winding (flipped normals).")

    warnings: list[str] = []
    if not mesh.is_watertight:
        warnings.append("Mesh is not watertight (has holes / open edges).")
    if needs_supports:
        warnings.append("Tall/overhanging geometry likely needs supports.")
    if not has_flat_base:
        warnings.append("No clear flat base detected; bed adhesion may suffer.")

    return MeshReport(
        is_valid=len(issues) == 0,
        is_manifold=bool(mesh.is_watertight),
        vertex_count=int(len(mesh.vertices)),
        face_count=int(len(mesh.faces)),
        bounding_box_mm=bounding_box,
        estimated_volume_cm3=volume_cm3,
        needs_supports=needs_supports,
        has_flat_base=has_flat_base,
        issues=issues,
        warnings=warnings,
    )


def attempt_repair(path: str, output_path: str | None = None) -> tuple[bool, str | None]:
    """Try to repair a non-watertight mesh; write a repaired copy on success.

    Returns ``(succeeded, repaired_path_or_None)``.
    """
    import trimesh

    mesh = _load_mesh(path)
    mesh.merge_vertices()
    mesh.update_faces(mesh.unique_faces())
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    try:
        trimesh.repair.fill_holes(mesh)
        trimesh.repair.fix_normals(mesh)
    except Exception:  # noqa: BLE001
        pass

    if not mesh.is_watertight:
        return False, None

    out = output_path or (path + ".repaired.glb")
    mesh.export(out)
    return True, out


# Backwards-compatible alias for the Phase 1 name.
validate_mesh = validate
