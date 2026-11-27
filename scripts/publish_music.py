import html
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "music" / "inbox"
PROCESSED = INBOX / "processed"
TRACKS = ROOT / "music" / "tracks"
MUSIC_DIR = ROOT / "music"
IMAGES = ROOT / "assets" / "images"
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm"}


SMALL_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "in", "nor", "of", "on", "or", "the", "to", "with"}


def slugify(stem: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-") or "untitled"


def title_from_stem(stem: str) -> str:
    words = [w for w in re.split(r"[-_]+", stem) if w]
    return " ".join(
        w.capitalize() if (i == 0 or i == len(words) - 1 or w.lower() not in SMALL_WORDS) else w.lower()
        for i, w in enumerate(words)
    )


def detect_motion_in_video(video_path: Path) -> bool:
    """Return True if the video has real motion, False if it is a still image."""
    try:
        cmd = [
            FFMPEG, "-hide_banner", "-nostats",
            "-i", str(video_path),
            "-t", "6",
            "-vf", "mpdecimate,showinfo",
            "-f", "null", "-",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        kept_frames = res.stderr.count("n:")
        return kept_frames > 2
    except Exception:
        return True


def run_ffmpeg(args: list[str]) -> None:
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *args]
    subprocess.run(cmd, check=True)


def process_inbox() -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    TRACKS.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    by_stem: dict[str, dict[str, Path]] = {}
    for p in INBOX.iterdir():
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        entry = by_stem.setdefault(slugify(p.stem), {})
        if ext in AUDIO_EXTS:
            entry["audio"] = p
        elif ext in IMAGE_EXTS:
            entry["image"] = p
        elif ext in VIDEO_EXTS:
            entry["video"] = p
        elif ext == ".txt":
            entry["lyrics"] = p

    count = 0
    for stem, files in sorted(by_stem.items()):
        audio = files.get("audio")
        video = files.get("video")
        image = files.get("image")

        out_mp4 = TRACKS / f"{stem}.mp4"
        out_mp3 = TRACKS / f"{stem}.mp3"

        if video and not audio:
            # Standalone MP4/video: auto-detect whether it has real motion or is a still image
            has_video = detect_motion_in_video(video)
            print(f"Importing {video.name} directly (no video re-encode needed)...")
            if video.suffix.lower() == ".mp4":
                shutil.copy2(video, out_mp4)
            else:
                run_ffmpeg(["-i", str(video), "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k", str(out_mp4)])
            run_ffmpeg(["-i", str(video), "-vn", "-c:a", "libmp3lame", "-b:a", "192k", str(out_mp3)])
            if image:
                shutil.copy2(image, IMAGES / f"{stem}{image.suffix.lower()}")
                shutil.move(str(image), str(PROCESSED / image.name))
            else:
                run_ffmpeg(["-i", str(video), "-ss", "00:00:01", "-vframes", "1", str(IMAGES / f"{stem}.jpg")])
            shutil.move(str(video), str(PROCESSED / video.name))
        elif audio and (video or image):
            visual = video or image
            has_video = visual.suffix.lower() in VIDEO_EXTS
            print(f"Building {out_mp4.name} from {visual.name} + {audio.name}...")
            if not has_video:
                run_ffmpeg([
                    "-loop", "1",
                    "-i", str(visual),
                    "-i", str(audio),
                    "-c:v", "libx264",
                    "-tune", "stillimage",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-shortest",
                    str(out_mp4),
                ])
                shutil.copy2(visual, IMAGES / f"{stem}{visual.suffix.lower()}")
            else:
                run_ffmpeg([
                    "-stream_loop", "-1",
                    "-i", str(visual),
                    "-i", str(audio),
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-pix_fmt", "yuv420p",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-shortest",
                    str(out_mp4),
                ])
                if image:
                    shutil.copy2(image, IMAGES / f"{stem}{image.suffix.lower()}")
                    shutil.move(str(image), str(PROCESSED / image.name))
                else:
                    run_ffmpeg(["-i", str(visual), "-ss", "00:00:01", "-vframes", "1", str(IMAGES / f"{stem}.jpg")])

            if audio.suffix.lower() == ".mp3":
                shutil.copy2(audio, out_mp3)
            else:
                run_ffmpeg(["-i", str(audio), "-c:a", "libmp3lame", "-b:a", "192k", str(out_mp3)])

            shutil.move(str(audio), str(PROCESSED / audio.name))
            shutil.move(str(visual), str(PROCESSED / visual.name))
        else:
            continue

        (TRACKS / f"{stem}.json").write_text(
            json.dumps({"has_video": has_video, "added_at": time.time()}, indent=2), encoding="utf-8"
        )

        if "lyrics" in files:
            shutil.copy2(files["lyrics"], TRACKS / f"{stem}.txt")
            shutil.move(str(files["lyrics"]), str(PROCESSED / files["lyrics"].name))

        count += 1

    return count


def optimize_existing_pngs() -> None:
    originals = IMAGES / "originals"
    originals.mkdir(parents=True, exist_ok=True)
    for png in list(IMAGES.glob("*.png")):
        if png.name.startswith("_"):
            continue
        jpg = IMAGES / f"{png.stem}.jpg"
        run_ffmpeg(["-i", str(png), "-vf", "scale='min(896,iw)':-2", "-q:v", "3", str(jpg)])
        shutil.move(str(png), str(originals / png.name))


def find_cover(stem: str, prefix: str) -> str:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        if (IMAGES / f"{stem}{ext}").exists():
            return f"{prefix}assets/images/{stem}{ext}"
    return ""


def track_has_video(stem: str, has_mp4: bool, has_cover: bool) -> bool:
    meta_path = TRACKS / f"{stem}.json"
    if meta_path.exists():
        try:
            return bool(json.loads(meta_path.read_text(encoding="utf-8")).get("has_video", False))
        except Exception:
            pass
    return has_mp4 and not has_cover


def write_track_pages() -> list[str]:
    mp4s = {p.stem: p for p in sorted(TRACKS.glob("*.mp4"))}
    mp3s = {p.stem: p for p in sorted(TRACKS.glob("*.mp3"))}

    def sort_key(stem: str) -> float:
        meta_path = TRACKS / f"{stem}.json"
        if meta_path.exists():
            try:
                added = json.loads(meta_path.read_text(encoding="utf-8")).get("added_at")
                if added is not None:
                    return float(added)
            except Exception:
                pass
        f = mp3s.get(stem) or mp4s.get(stem)
        return f.stat().st_mtime if f else 0.0

    stems = sorted(set(mp4s) | set(mp3s), key=sort_key, reverse=True)

    for idx, stem in enumerate(stems, start=1):
        title = title_from_stem(stem)
        title_esc = html.escape(title)
        desc_esc = html.escape(f"Listen to {title} by Marvin Snell (OsmoticPoet).")
        cover = find_cover(stem, "../")
        og_img = f"https://osmoticpoet.com/{cover.lstrip('../')}" if cover else "https://osmoticpoet.com/assets/images/the-rooms-we-leave.jpg"
        mp4_src = f"tracks/{stem}.mp4" if stem in mp4s else ""
        mp3_src = f"tracks/{stem}.mp3" if stem in mp3s else ""
        has_video = track_has_video(stem, bool(mp4_src), bool(cover))

        lyrics_path = TRACKS / f"{stem}.txt"
        if lyrics_path.exists():
            lyrics_html = html.escape(lyrics_path.read_text(encoding="utf-8").strip())
            lyrics_cls = "poem-stanza"
        else:
            lyrics_html = f"Lyrics not added yet.\n\nTo add lyrics, place a {stem}.txt file in music/tracks/ or music/inbox/ and run publish-music.bat."
            lyrics_cls = "poem-stanza muted"

        if has_video and mp4_src:
            poster = f' poster="{cover}"' if cover else ""
            visual_html = f"""          <video class="piece-video" controls controlsList="nodownload" oncontextmenu="return false;" preload="metadata"{poster}>
            <source src="{mp4_src}" type="video/mp4">
          </video>"""
            audio_html = ""
        else:
            visual_html = f'          <img class="piece-cover" src="{cover}" alt="{title_esc} cover art">' if cover else ""
            audio_src = mp3_src or mp4_src
            audio_html = f"""          <div class="audio-box">
            <div class="audio-box-label">Listen to Track (MP3)</div>
            <audio controls controlsList="nodownload" oncontextmenu="return false;" preload="metadata">
              <source src="{audio_src}" type="audio/mpeg">
            </audio>
          </div>""" if audio_src else ""

        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_esc} — OsmoticPoet</title>
  <meta name="description" content="{desc_esc}">
  <meta property="og:type" content="music.song">
  <meta property="og:title" content="{title_esc} — OsmoticPoet">
  <meta property="og:description" content="{desc_esc}">
  <meta property="og:url" content="https://osmoticpoet.com/music/{stem}.html">
  <meta property="og:image" content="{og_img}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Inter:wght@300;400;500;600&family=Lora:ital,wght@0,400;0,500;1,400&display=swap" media="print" onload="this.media='all'">
  <link rel="stylesheet" href="../css/styles.css">
</head>
<body>
  <header class="site-header">
    <div class="nav-inner">
      <a class="brand" href="../index.html">
        <span class="brand-dot" aria-hidden="true"></span>
        <span>OsmoticPoet</span>
      </a>
      <button class="menu-toggle" type="button" aria-label="Toggle navigation">Menu</button>
      <ul class="nav-links">
        <li><a href="../index.html">Home</a></li>
        <li><a href="../poetry/index.html">Poetry</a></li>
        <li><a href="index.html" class="active">Music</a></li>
        <li><a href="../about/index.html">About</a></li>
          <li><a href="../privacy.html">Privacy</a></li>
      </ul>
    </div>
  </header>

  <main class="container">
    <section class="section">
      <a class="breadcrumb" href="index.html">&larr; All Music</a>
      <div class="card piece-layout">
        <div class="piece-media">
{visual_html}
{audio_html}
        </div>
        <div>
          <h1 class="piece-title">{title_esc}</h1>
          <p class="{lyrics_cls}">{lyrics_html}</p>
        </div>
      </div>
    </section>

    <section class="section" id="comments">
      <div class="section-head">
        <h2 class="section-title">Leave a Note</h2>
        <span class="section-link">Sent directly via email</span>
      </div>
      <div class="card">
        <form class="comment-form" id="comment-form" action="https://api.web3forms.com/submit" method="POST">
          <input type="hidden" name="access_key" value="38932bab-2025-40ac-b84e-f2ff021cd68f">
          <input type="hidden" name="subject" value="Comment on Track: {title_esc}">
          <input type="checkbox" name="botcheck" style="display: none;" tabindex="-1" autocomplete="off">

          <div class="form-row">
            <div class="form-field">
              <label for="comment-name">Name</label>
              <input id="comment-name" name="name" type="text" placeholder="Your name" required>
            </div>
            <div class="form-field">
              <label for="comment-email">Email (optional)</label>
              <input id="comment-email" name="email" type="email" placeholder="you@example.com">
            </div>
          </div>

          <div class="form-field">
            <label for="comment-message">Comment</label>
            <textarea id="comment-message" name="message" placeholder="Share a thought..." required></textarea>
          </div>

          <div class="form-actions">
            <button class="btn btn-primary" type="submit">Send Comment</button>
            <span class="form-status" id="comment-status" aria-live="polite"></span>
          </div>
          <p class="form-disclaimer">Your email is optional, used only to reply to your note, and never shared or added to any mailing list. Prefer not to use the form? Email <a href="mailto:mgsnell201@gmail.com">mgsnell201@gmail.com</a> directly. &middot; <a href="../privacy.html">Privacy Policy</a></p>
        </form>
      </div>
    </section>

    <footer class="site-footer">
      <div>
        <p class="footer-brand">OsmoticPoet</p>
        <p class="footer-tagline">Words written for quiet hours, paired with sound.</p>
        <span class="footer-copy">&copy; 2026 OsmoticPoet</span>
      </div>
      <div>
        <p class="footer-heading">Explore</p>
        <ul class="footer-links">
          <li><a href="../index.html">Home</a></li>
          <li><a href="../poetry/index.html">Poetry</a></li>
          <li><a href="../music/index.html">Music</a></li>
          <li><a href="../about/index.html">About</a></li>
        </ul>
      </div>
      <div>
        <p class="footer-heading">Follow</p>
        <ul class="footer-links">
          <li><a href="https://www.youtube.com/" target="_blank" rel="noopener">YouTube</a></li>
          <li><a href="https://www.facebook.com/" target="_blank" rel="noopener">Facebook</a></li>
        </ul>
      </div>
    </footer>
  </main>

  <script src="../js/main.js" defer></script>
</body>
</html>
"""
        (MUSIC_DIR / f"{stem}.html").write_text(page, encoding="utf-8")

    return stems


def build_track_cards(stems: list[str], prefix: str, href_prefix: str) -> str:
    if not stems:
        return '        <p class="poem-stanza muted">No tracks yet.</p>'

    cards = []
    for idx, stem in enumerate(stems, start=1):
        title = html.escape(title_from_stem(stem))
        cover = find_cover(stem, prefix)
        img_html = f'\n          <img class="media-card-img" loading="lazy" decoding="async" src="{cover}" alt="{title} cover">' if cover else ""
        cards.append(
            f"""        <a class="media-card" href="{href_prefix}{stem}.html">{img_html}
          <div class="media-card-body">
              <h3 class="media-card-title">{title}</h3>
          </div>
        </a>"""
        )
    return "\n".join(cards)


def write_sitemap() -> None:
    base = "https://osmoticpoet.com"
    urls = [
        f"{base}/",
        f"{base}/poetry/",
        f"{base}/music/",
        f"{base}/about/",
        f"{base}/privacy.html",
    ]
    for folder in ("poetry", "music"):
        for p in sorted((ROOT / folder).glob("*.html")):
            if p.name != "index.html":
                urls.append(f"{base}/{folder}/{p.name}")
    entries = "\n".join(f"  <url><loc>{html.escape(u)}</loc></url>" for u in urls)
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")


def replace_section(path: Path, start_marker: str, end_marker: str, new_body: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"({re.escape(start_marker)}\s*)(.*?)(\s*{re.escape(end_marker)})",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise RuntimeError(f"Markers not found in {path}")
    path.write_text(pattern.sub(rf"\1{new_body}\3", text, count=1), encoding="utf-8")


def git_push_if_configured() -> None:
    if not (ROOT / ".git").exists():
        print("Note: Git is not initialized here yet. Once you connect GitHub/Netlify/Cloudflare Pages, this script will auto-upload.")
        return
    remotes = subprocess.run(["git", "-C", str(ROOT), "remote"], capture_output=True, text=True)
    if not remotes.stdout.strip():
        print("Note: No git remote configured yet. Skipping upload.")
        return
    subprocess.run(["git", "-C", str(ROOT), "add", "."], check=True)
    status = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True)
    if status.stdout.strip():
        subprocess.run(["git", "-C", str(ROOT), "commit", "-m", "Update music tracks"], check=True)
        subprocess.run(["git", "-C", str(ROOT), "pull", "--rebase"], check=True)
        subprocess.run(["git", "-C", str(ROOT), "push"], check=True)
        print("Uploaded changes to remote website.")
    else:
        print("No changes to upload.")


if __name__ == "__main__":
    created = process_inbox()
    optimize_existing_pngs()
    stems = write_track_pages()
    replace_section(MUSIC_DIR / "index.html", "<!-- TRACKS_START -->", "<!-- TRACKS_END -->", build_track_cards(stems, "../", ""))
    replace_section(ROOT / "index.html", "<!-- HOME_TRACKS_START -->", "<!-- HOME_TRACKS_END -->", build_track_cards(stems[:4], "", "music/"))
    write_sitemap()
    print(f"Done. Processed {created} new track(s), generated {len(stems)} track page(s), and updated index.html + music/index.html.")
    git_push_if_configured()
