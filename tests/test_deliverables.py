from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_required_hackathon_deliverables_exist():
    required = [
        "README.md",
        "MIT-LICENSE.txt",
        "HACKATHON_STATUS.md",
        "DEVPOST_SUBMISSION.md",
        "CLOUD_RUN_DEPLOYMENT.md",
        "DEMO_RECORDING_SCRIPT.md",
        "Dockerfile",
        "requirements.txt",
        "sample_alert.json",
        "scripts/capture_demo.py",
        "scripts/create_demo_video.py",
        "scripts/cloud_run_preflight.py",
        "app/adk_adapter.py",
    ]

    for name in required:
        assert ROOT.joinpath(name).exists(), name


def test_docs_describe_live_first_and_fallback_behavior():
    readme = ROOT.joinpath("README.md").read_text(encoding="utf-8")
    devpost = ROOT.joinpath("DEVPOST_SUBMISSION.md").read_text(encoding="utf-8")

    assert "DYNATRACE_API_KEY" in readme
    assert "GEMINI_API_KEY" in readme
    assert "mock_dynatrace.py" in readme
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
    script = ROOT.joinpath("DEMO_RECORDING_SCRIPT.md").read_text(encoding="utf-8")

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


def test_cloud_run_preflight_does_not_expose_secret_values():
    script = ROOT.joinpath("scripts/cloud_run_preflight.py").read_text(encoding="utf-8")

    assert "dotenv_values" in script
    assert '"present" if value else "missing"' in script
    assert "DYNATRACE_API_KEY" in script
    assert "GEMINI_API_KEY" in script
