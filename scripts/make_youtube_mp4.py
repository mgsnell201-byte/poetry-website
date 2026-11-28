import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = ROOT / "music" / "youtube-maker"
OUT_DIR = Path.home() / "Desktop" / "YouTube-Uploads"
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".m4a"}
VIDEO_EXTS = {".mp4", ".mov", ".webm"}
FPS = 25
CROSSFADE_SEC = 2.0


def slugify(stem: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "untitled"


def get_duration_seconds(media_path: Path) -> float:
    res = subprocess.run(
        [
            FFPROBE, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(media_path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(res.stdout.strip())


def build_single_image_video(image: Path, source_media: Path, out_mp4: Path) -> None:
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


def build_slideshow_video(images: list[Path], source_media: Path, out_mp4: Path) -> None:
    total_dur = get_duration_seconds(source_media)
    n = len(images)
    fade = min(CROSSFADE_SEC, total_dur / max(n * 2, 1))
    seg_dur = (total_dur + fade * (n - 1)) / n
    frames = max(1, int(round(seg_dur * FPS)))

    print(f"Building {out_mp4.name} ({n} scenes, {total_dur:.1f}s total, ~{seg_dur:.1f}s per scene)...")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        seg_paths: list[Path] = []

        for idx, img in enumerate(images):
            seg_path = tmp / f"seg_{idx:02d}.mp4"
            if idx % 2 == 0:
                zoom_expr = f"1+0.07*on/{frames}"
            else:
                zoom_expr = f"1.07-0.07*on/{frames}"

            vf = (
                "scale=1280:720:force_original_aspect_ratio=increase,"
                "crop=1280:720,"
                "scale=2560:1440,"
                f"zoompan=z='{zoom_expr}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"d={frames}:s=1280x720:fps={FPS},"
                "format=yuv420p"
            )
            subprocess.run(
                [
                    FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                    "-loop", "1", "-i", str(img),
                    "-t", f"{seg_dur:.3f}",
                    "-vf", vf,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                    "-pix_fmt", "yuv420p",
                    str(seg_path),
                ],
                check=True,
            )
            seg_paths.append(seg_path)
            print(f"  Rendered scene {idx + 1}/{n}: {img.name}")

        cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error"]
        for sp in seg_paths:
            cmd.extend(["-i", str(sp)])
        cmd.extend(["-i", str(source_media)])

        if n == 1:
            fc = f"[0:v]fade=t=out:st={max(0, total_dur - 2.0):.3f}:d=2.0[vout]"
        else:
            fc_parts = []
            prev_label = "[0:v]"
            for i in range(1, n):
                offset = i * (seg_dur - fade)
                out_label = f"[v{i}]" if i < n - 1 else "[vx]"
                fc_parts.append(
                    f"{prev_label}[{i}:v]xfade=transition=fade:duration={fade:.3f}:offset={offset:.3f}{out_label}"
                )
                prev_label = out_label
            fade_out_start = max(0.0, total_dur - 2.0)
            fc_parts.append(f"[vx]fade=t=out:st={fade_out_start:.3f}:d=2.0[vout]")
            fc = ";".join(fc_parts)

        is_mp4_source = source_media.suffix.lower() == ".mp4"
        audio_args = ["-c:a", "copy"] if is_mp4_source else ["-c:a", "aac", "-b:a", "192k"]

        cmd.extend([
            "-filter_complex", fc,
            "-map", "[vout]",
            "-map", f"{n}:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            *audio_args,
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(out_mp4),
        ])
        subprocess.run(cmd, check=True)


def main() -> None:
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    created = 0

    # 1. Subfolders inside music/youtube-maker/ -> multi-image slideshow mode
    for sub in sorted(WORK_DIR.iterdir()):
        if not sub.is_dir() or sub.name.startswith("_"):
            continue
        imgs = sorted(
            [p for p in sub.iterdir() if p.is_file() and not p.name.startswith("_") and p.suffix.lower() in IMAGE_EXTS],
            key=lambda p: p.name.lower(),
        )
        media = [
            p for p in sorted(sub.iterdir())
            if p.is_file() and not p.name.startswith("_") and p.suffix.lower() in (AUDIO_EXTS | VIDEO_EXTS)
        ]
        if not imgs or not media:
            continue
        out_mp4 = OUT_DIR / f"{slugify(sub.name)}-youtube.mp4"
        if len(imgs) == 1:
            build_single_image_video(imgs[0], media[0], out_mp4)
        else:
            build_slideshow_video(imgs, media[0], out_mp4)
        print(f"Saved: {out_mp4}")
        created += 1

    # 2. Loose pairs directly in music/youtube-maker/ -> single-image mode
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

    for stem, files in sorted(by_stem.items()):
        image = files.get("image")
        source_media = files.get("audio") or files.get("video")
        if not image or not source_media:
            continue
        out_mp4 = OUT_DIR / f"{stem}-youtube.mp4"
        build_single_image_video(image, source_media, out_mp4)
        print(f"Saved: {out_mp4}")
        created += 1

    if created == 0:
        print(f"No matching pairs or slideshow folders found in {WORK_DIR}")
    else:
        print(f"\nDone! Created {created} YouTube MP4(s) in {OUT_DIR}")
        print("Verify the video(s) on your Desktop, then delete the input files from music\\youtube-maker\\.")


if __name__ == "__main__":
    main()
