from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_readiness_module():
    path = ROOT / "scripts" / "devpost_readiness.py"
    spec = importlib.util.spec_from_file_location("devpost_readiness", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_devpost_readiness_passes_for_local_package():
    module = load_readiness_module()
    data = module.readiness()

    assert data["ready_for_devpost_packaging"] is True
    assert data["track"] == "Dynatrace partner track"
    assert data["hosted_url"] == "https://zerotouch-sre-971465910048.us-central1.run.app"
    assert "Hosted project URL after Cloud Run deploy" not in data["remaining_external_fields"]


def test_final_checklist_covers_required_devpost_fields():
    checklist = ROOT.joinpath("DEVPOST_FINAL_CHECKLIST.md").read_text(encoding="utf-8")

    assert "Hosted project URL" in checklist
    assert "Public repository URL" in checklist
    assert "Demo video URL" in checklist
    assert "cloud_run_preflight.py" in checklist
    assert "Dynatrace" in checklist
    assert "Cloud Run" in checklist
