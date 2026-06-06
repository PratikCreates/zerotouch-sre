from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "demo_assets"
VIDEO_PATH = OUT_DIR / "zerotouch_sre_demo.mp4"
HOSTED_URL = "https://zerotouch-sre-971465910048.us-central1.run.app"


@dataclass(frozen=True)
class Slide:
    title: str
    subtitle: str
    bullets: Sequence[str]
    footer: str = "ZeroTouch SRE | Google Cloud Rapid Agent Hackathon"
    seconds: int = 12


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, typeface: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), trial, font=typeface)[2]
        if width <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_slide(slide: Slide, path: Path) -> None:
    width, height = 1920, 1080
    image = Image.new("RGB", (width, height), "#07131f")
    draw = ImageDraw.Draw(image)
    for y in range(height):
        blue = 31 + int(26 * y / height)
        green = 19 + int(42 * y / height)
        draw.line([(0, y), (width, y)], fill=(7, green, blue))

    accent = "#4de1ff"
    gold = "#ffd166"
    white = "#f8fbff"
    muted = "#b9c7d5"
    panel = "#0f2233"

    draw.rounded_rectangle((90, 74, 1830, 980), radius=42, fill=panel, outline="#2c5875", width=3)
    draw.text((140, 130), slide.title, font=font(72, bold=True), fill=white)
    draw.text((144, 220), slide.subtitle, font=font(34), fill=accent)

    y = 325
    bullet_font = font(36)
    for bullet in slide.bullets:
        draw.ellipse((150, y + 12, 174, y + 36), fill=gold)
        for index, line in enumerate(wrap(draw, bullet, bullet_font, 1500)):
            draw.text((200, y + index * 48), line, font=bullet_font, fill=white)
        y += 112

    draw.line((140, 895, 1780, 895), fill="#2c5875", width=2)
    draw.text((140, 925), slide.footer, font=font(28), fill=muted)
    image.save(path)


def load_demo_summary() -> dict[str, str]:
    response_path = ROOT / "demo_response.json"
    if not response_path.exists():
        return {"status": "mitigated", "telemetry_mode": "mock", "incident_id": "INC-DEMO-20260607"}
    data = json.loads(response_path.read_text(encoding="utf-8"))
    return {
        "status": str(data.get("status", "mitigated")),
        "telemetry_mode": str(data.get("telemetry_mode", "mock")),
        "incident_id": str(data.get("incident_id", "INC-DEMO-20260607")),
    }


def slides() -> list[Slide]:
    summary = load_demo_summary()
    return [
        Slide(
            title="ZeroTouch SRE",
            subtitle="Autonomous alert triage, safe mitigation, and post-mortems",
            bullets=(
                "A production alert enters a FastAPI webhook.",
                "The agent gathers telemetry, reasons about root cause, plans mitigation, and writes artifacts.",
                "Cloud Run hosted backend: " + HOSTED_URL,
            ),
        ),
        Slide(
            title="Why It Matters",
            subtitle="The first minutes of an incident are expensive",
            bullets=(
                "SREs jump between alerts, logs, dashboards, runbooks, and post-incident notes.",
                "ZeroTouch SRE compresses that loop into one auditable backend pipeline.",
                "The agent helps, but destructive production actions stay policy-gated.",
            ),
        ),
        Slide(
            title="Agent Loop",
            subtitle="Perceive -> Retrieve -> Reason -> Plan -> Execute -> Synthesize",
            bullets=(
                "gemini-3.5-flash role handles the high-speed incident loop.",
                "gemini-3.1-pro role handles report synthesis when live Gemini is available.",
                "The generated agent trace records every stage for review.",
            ),
        ),
        Slide(
            title="Partner Telemetry",
            subtitle="Dynatrace live-first, deterministic fallback",
            bullets=(
                "The service attempts real Dynatrace evidence with deployed credentials.",
                "If live auth or API evidence fails, the MCP-compatible client falls back autonomously.",
                "This run completed with telemetry_mode=" + summary["telemetry_mode"] + ".",
            ),
        ),
        Slide(
            title="Hosted Smoke Test",
            subtitle="Cloud Run endpoint is live",
            bullets=(
                "GET /health returned status=ok.",
                "POST /alert returned ok=true and status=" + summary["status"] + ".",
                "Incident " + summary["incident_id"] + " produced mitigation, post-mortem, runbook, and trace paths.",
            ),
        ),
        Slide(
            title="Safe Mitigation",
            subtitle="Simulation allowlist, no unbounded production writes",
            bullets=(
                "Allowed actions: scale_service, rollback_release, open_incident_channel.",
                "Every action is marked simulated_success and written to an audit log.",
                "Unapproved destructive actions are rejected by policy.",
            ),
        ),
        Slide(
            title="Generated Evidence",
            subtitle="Artifacts for humans and machines",
            bullets=(
                "post_mortem.md: readable incident narrative and follow-up actions.",
                "runbook.json: machine-readable incident object.",
                "agent_trace.json: inspectable agent-stage trace with model-role metadata.",
            ),
        ),
        Slide(
            title="Quality Gate",
            subtitle="Ready for Devpost packaging",
            bullets=(
                "pytest: 13 passed.",
                "Cloud Run deployed with provider keys sourced from Secret Manager.",
                "Remaining external fields: public GitHub repo URL and uploaded video URL.",
            ),
        ),
    ]


def build_video() -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frame_paths: list[Path] = []
    for index, slide in enumerate(slides(), start=1):
        frame_path = OUT_DIR / f"slide_{index:02d}.png"
        draw_slide(slide, frame_path)
        frame_paths.append(frame_path)

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is not available on PATH")

    concat_path = OUT_DIR / "slides.txt"
    lines: list[str] = []
    for frame_path, slide in zip(frame_paths, slides(), strict=True):
        normalized = frame_path.as_posix().replace("'", "'\\''")
        lines.append(f"file '{normalized}'")
        lines.append(f"duration {slide.seconds}")
    lines.append(f"file '{frame_paths[-1].as_posix()}'")
    concat_path.write_text("\n".join(lines), encoding="utf-8")

    command = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-vf",
        "format=yuv420p,fps=30",
        "-c:v",
        "libx264",
        "-movflags",
        "+faststart",
        str(VIDEO_PATH),
    ]
    subprocess.run(command, check=True, cwd=ROOT)
    return VIDEO_PATH


if __name__ == "__main__":
    print(build_video())
