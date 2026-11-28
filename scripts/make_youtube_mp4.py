import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT / "music" / "youtube-maker"
OUT_DIR = Path.home() / "Desktop" / "YouTube-Uploads"
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a"}
VIDEO_EXTS = {".mp4", ".mov", ".webm"}


def slugify(stem: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "untitled"


def main() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    by_stem: dict[str, dict[str, Path]] = {}
    for p in WORK_DIR.iterdir():
        if not p.is_file() or p.name.startswith("_"):
            continue
        ext = p.suffix.lower()
        entry = by_stem.setdefault(slugify(p.stem), {})
        if ext in IMAGE_EXTS:
            entry["image"] = p
        elif ext in VIDEO_EXTS:
            entry["video"] = p
        elif ext in AUDIO_EXTS:
            entry["audio"] = p

    created = 0
    for stem, files in sorted(by_stem.items()):
        image = files.get("image")
        source_media = files.get("audio") or files.get("video")
        if not image or not source_media:
            continue

        out_mp4 = OUT_DIR / f"{stem}-youtube.mp4"
        is_mp4_source = source_media.suffix.lower() == ".mp4"
        audio_args = ["-c:a", "copy"] if is_mp4_source else ["-c:a", "aac", "-b:a", "192k"]

        print(f"Building {out_mp4.name} from {image.name} + {source_media.name}...")
        cmd = [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-loop", "1", "-i", str(image),
            "-i", str(source_media),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-tune", "stillimage",
            *audio_args,
            "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
            "-shortest",
            str(out_mp4),
        ]
        subprocess.run(cmd, check=True)
        print(f"Saved: {out_mp4}")
        created += 1

    if created == 0:
        print(f"No matching image + audio/video pairs found in {WORK_DIR}")
    else:
        print(f"\nDone! Created {created} YouTube MP4(s) in {OUT_DIR}")
        print("Verify the video(s) on your Desktop, then delete the input files from music\\youtube-maker\\.")


if __name__ == "__main__":
    main()
