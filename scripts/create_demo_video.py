from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets" / "screenshots"
OUT_DIR = ROOT / "demo_assets"
OUT_FILE = OUT_DIR / "zerotouch_sre_demo.mp4"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    home = ASSETS / "04-hosted-showcase.png"
    review = ASSETS / "05-visual-demo-result.png"
    if not home.exists() or not review.exists():
        raise SystemExit("Required screenshots are missing. Capture homepage and incident-review screenshots first.")

    concat = OUT_DIR / "ffmpeg_inputs.txt"
    concat.write_text(
        "\n".join(
            [
                f"file '{home.as_posix()}'",
                "duration 4",
                f"file '{review.as_posix()}'",
                "duration 6",
                f"file '{review.as_posix()}'",
            ]
        ),
        encoding="utf-8",
    )

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-vf",
        "scale=1280:-2,format=yuv420p",
        "-r",
        "30",
        str(OUT_FILE),
    ]
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as exc:
        raise SystemExit("ffmpeg is required to create zerotouch_sre_demo.mp4") from exc

    print(OUT_FILE)


if __name__ == "__main__":
    main()
