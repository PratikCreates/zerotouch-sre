from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DOCS = ROOT / "_private" / "docs"


def test_required_hackathon_deliverables_exist():
    public_required = [
        "README.md",
        "Dockerfile",
        "requirements.txt",
        "sample_alert.json",
        "LICENSE",
        "app/adk_adapter.py",
    ]
    private_required = [
        "HACKATHON_STATUS.md",
        "DEVPOST_SUBMISSION.md",
        "CLOUD_RUN_DEPLOYMENT.md",
        "DEMO_RECORDING_SCRIPT.md",
        "FINAL_SUBMISSION_FIELDS.md",
    ]

    for name in public_required:
        assert ROOT.joinpath(name).exists(), name
    
    if PRIVATE_DOCS.exists():
        for name in private_required:
            assert PRIVATE_DOCS.joinpath(name).exists(), name
            
    for name in ["scripts/capture_demo.py", "scripts/create_demo_video.py", "scripts/cloud_run_preflight.py"]:
        assert ROOT.joinpath(name).exists(), name


def test_docs_describe_live_first_and_fallback_behavior():
    readme = ROOT.joinpath("README.md").read_text(encoding="utf-8")
    assert "DYNATRACE_API_KEY" in readme
    assert "GEMINI_API_KEY" in readme
    assert "mock_dynatrace.py" in readme

    if PRIVATE_DOCS.exists():
        devpost = PRIVATE_DOCS.joinpath("DEVPOST_SUBMISSION.md").read_text(encoding="utf-8")
        assert "Cloud Run" in devpost
        assert "https://zerotouch-sre-971465910048.us-central1.run.app" in devpost
        assert "tries real credentials first" in devpost


def test_capture_demo_script_is_documented_and_present():
    script = ROOT.joinpath("scripts/capture_demo.py").read_text(encoding="utf-8")
    readme = ROOT.joinpath("README.md").read_text(encoding="utf-8")

    assert "demo_response.json" in script
    assert "agent_trace.json" in readme
    assert "capture_demo.py" in readme


def test_demo_recording_script_covers_hosted_flow():
    if PRIVATE_DOCS.exists():
        script = PRIVATE_DOCS.joinpath("DEMO_RECORDING_SCRIPT.md").read_text(encoding="utf-8")
        assert "https://zerotouch-sre-971465910048.us-central1.run.app" in script
        assert "POST" in script
        assert "agent_trace.json" in script
        assert "python -m pytest -q" in script


def test_demo_video_generator_is_available_and_ignored():
    generator = ROOT.joinpath("scripts/create_demo_video.py").read_text(encoding="utf-8")
    gitignore = ROOT.joinpath(".gitignore").read_text(encoding="utf-8")

    assert "zerotouch_sre_demo.mp4" in generator
    assert "ffmpeg" in generator
    assert "demo_assets/" in gitignore


def test_final_submission_fields_are_copy_paste_ready():
    if PRIVATE_DOCS.exists():
        fields = PRIVATE_DOCS.joinpath("FINAL_SUBMISSION_FIELDS.md").read_text(encoding="utf-8")
        assert "Hosted Project URL" in fields
        assert "https://zerotouch-sre-971465910048.us-central1.run.app" in fields
        assert "Public Repository URL" in fields
        assert "https://github.com/PratikCreates/zerotouch-sre" in fields
        assert "Demo Video URL" in fields
        assert "zerotouch_sre_demo.mp4" in fields



def test_cloud_run_preflight_does_not_expose_secret_values():
    script = ROOT.joinpath("scripts/cloud_run_preflight.py").read_text(encoding="utf-8")

    assert "dotenv_values" in script
    assert '"present" if value else "missing"' in script
    assert "DYNATRACE_API_KEY" in script
    assert "GEMINI_API_KEY" in script
