"""Unit tests for the mesh validator and repair helpers."""

from __future__ import annotations

import trimesh

from app.services.mesh import mesh_validator


def test_validate_valid_box(tmp_path):
    path = tmp_path / "box.glb"
    trimesh.creation.box(extents=(10, 10, 10)).export(str(path))

    report = mesh_validator.validate(str(path))

    assert report.is_valid is True
    assert report.is_manifold is True  # a box is watertight
    assert report.vertex_count > 0
    assert report.face_count > 0
    assert set(report.bounding_box_mm) == {"x", "y", "z"}
    assert report.bounding_box_mm["x"] > 0
    assert report.estimated_volume_cm3 > 0


def test_report_has_all_expected_fields(tmp_path):
    path = tmp_path / "box.glb"
    trimesh.creation.box().export(str(path))

    report = mesh_validator.validate(str(path)).to_dict()
    for key in (
        "is_valid",
        "is_manifold",
        "vertex_count",
        "face_count",
        "bounding_box_mm",
        "estimated_volume_cm3",
        "needs_supports",
        "has_flat_base",
        "issues",
        "warnings",
        "repair_attempted",
        "repair_succeeded",
    ):
        assert key in report


def test_validate_invalid_bytes_returns_invalid(tmp_path):
    path = tmp_path / "garbage.glb"
    path.write_bytes(b"this is not a real glb file")

    report = mesh_validator.validate(str(path))
    assert report.is_valid is False
    assert len(report.issues) >= 1
