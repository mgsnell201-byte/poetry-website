import html
import json
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "poetry" / "inbox"
PROCESSED = INBOX / "processed"
POEMS_DIR = ROOT / "poetry"
POEMS_DATA = POEMS_DIR / "poems"
IMAGES = ROOT / "assets" / "images"
FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"

TEXT_EXTS = {".txt", ".md"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac"}


def title_from_stem(stem: str) -> str:
    return " ".join(w.capitalize() for w in re.split(r"[-_]+", stem) if w)


def run_ffmpeg(args: list[str]) -> None:
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", *args]
    subprocess.run(cmd, check=True)


def process_inbox() -> int:
    INBOX.mkdir(parents=True, exist_ok=True)
    POEMS_DATA.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)

    by_stem: dict[str, dict[str, Path]] = {}
    for p in INBOX.iterdir():
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        entry = by_stem.setdefault(p.stem, {})
        if ext in TEXT_EXTS:
            entry["text"] = p
        elif ext in IMAGE_EXTS:
            entry["image"] = p
        elif ext in AUDIO_EXTS:
            entry["audio"] = p

    count = 0
    for stem, files in sorted(by_stem.items()):
        text_file = files.get("text")
        if not text_file:
            continue

        shutil.copy2(text_file, POEMS_DATA / f"{stem}.txt")
        shutil.move(str(text_file), str(PROCESSED / text_file.name))

        if "image" in files:
            img = files["image"]
            shutil.copy2(img, IMAGES / img.name)
            shutil.move(str(img), str(PROCESSED / img.name))

        if "audio" in files:
            aud = files["audio"]
            out_mp3 = POEMS_DATA / f"{stem}.mp3"
            if aud.suffix.lower() == ".mp3":
                shutil.copy2(aud, out_mp3)
            else:
                run_ffmpeg(["-i", str(aud), "-c:a", "libmp3lame", "-b:a", "192k", str(out_mp3)])
            shutil.move(str(aud), str(PROCESSED / aud.name))

        (POEMS_DATA / f"{stem}.json").write_text(
            json.dumps({"added_at": time.time()}, indent=2), encoding="utf-8"
        )
        count += 1

    return count


def find_cover(stem: str, prefix: str) -> str:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if (IMAGES / f"{stem}{ext}").exists():
            return f"{prefix}assets/images/{stem}{ext}"
    if (IMAGES / "_poem-default.png").exists():
        return f"{prefix}assets/images/_poem-default.png"
    return ""


def write_poem_pages() -> list[tuple[str, str]]:
    txt_files = {p.stem: p for p in sorted(POEMS_DATA.glob("*.txt"))}

    def sort_key(stem: str) -> float:
        meta_path = POEMS_DATA / f"{stem}.json"
        if meta_path.exists():
            try:
                added = json.loads(meta_path.read_text(encoding="utf-8")).get("added_at")
                if added is not None:
                    return float(added)
            except Exception:
                pass
        return txt_files[stem].stat().st_mtime

    stems = sorted(txt_files.keys(), key=sort_key, reverse=True)
    results: list[tuple[str, str]] = []

    for num, stem in enumerate(stems, start=1):
        raw = txt_files[stem].read_text(encoding="utf-8").strip()
        lines = raw.splitlines()
        title = lines[0].strip() if lines else title_from_stem(stem)
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        title_esc = html.escape(title)
        body_esc = html.escape(body)
        cover = find_cover(stem, "../")
        mp3_exists = (POEMS_DATA / f"{stem}.mp3").exists()

        img_html = f'          <img class="piece-cover" src="{cover}" alt="{title_esc} illustration">' if cover else ""
        audio_note = "" if mp3_exists else f'\n            <p class="audio-note">Audio reading slot ready for <code>poetry/poems/{stem}.mp3</code>.</p>'
        audio_html = f"""          <div class="audio-box">
            <div class="audio-box-label">Listen to Poem (MP3)</div>
            <audio controls controlsList="nodownload" oncontextmenu="return false;" preload="metadata">
              <source src="poems/{stem}.mp3" type="audio/mpeg">
            </audio>{audio_note}
          </div>"""

        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_esc} — OsmoticPoet</title>
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
        <li><a href="index.html" class="active">Poetry</a></li>
        <li><a href="../music/index.html">Music</a></li>
        <li><a href="../about/index.html">About</a></li>
      </ul>
    </div>
  </header>

  <main class="container">
    <section class="section">
      <a class="breadcrumb" href="index.html">&larr; All Poems</a>
      <div class="card piece-layout">
        <div class="piece-media">
{img_html}
{audio_html}
        </div>
        <div>
          <div class="card-meta">Poem &middot; No. {num:02d}</div>
          <h1 class="piece-title">{title_esc}</h1>
          <p class="poem-stanza">{body_esc}</p>
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
          <input type="hidden" name="subject" value="Comment on Poem: {title_esc}">
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

  <script src="../js/main.js"></script>
</body>
</html>
"""
        (POEMS_DIR / f"{stem}.html").write_text(page, encoding="utf-8")
        results.append((stem, title))

    return results


def build_poem_cards(items: list[tuple[str, str]], prefix: str, href_prefix: str) -> str:
    if not items:
        return '        <p class="poem-stanza muted">No poems yet.</p>'

    cards = []
    for num, (stem, title) in enumerate(items, start=1):
        title_esc = html.escape(title)
        cover = find_cover(stem, prefix)
        img_html = f'\n          <img class="media-card-img" src="{cover}" alt="{title_esc} cover">' if cover else ""
        cards.append(
            f"""        <a class="media-card" href="{href_prefix}{stem}.html">{img_html}
          <div class="media-card-body">
            <div class="card-meta">Poem &middot; No. {num:02d}</div>
            <h3 class="media-card-title">{title_esc}</h3>
          </div>
        </a>"""
        )
    return "\n".join(cards)


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
        subprocess.run(["git", "-C", str(ROOT), "commit", "-m", "Update poems"], check=True)
        subprocess.run(["git", "-C", str(ROOT), "pull", "--rebase"], check=True)
        subprocess.run(["git", "-C", str(ROOT), "push"], check=True)
        print("Uploaded changes to remote website.")
    else:
        print("No changes to upload.")


if __name__ == "__main__":
    created = process_inbox()
    items = write_poem_pages()
    replace_section(POEMS_DIR / "index.html", "<!-- POEMS_START -->", "<!-- POEMS_END -->", build_poem_cards(items, "../", ""))
    replace_section(ROOT / "index.html", "<!-- HOME_POEMS_START -->", "<!-- HOME_POEMS_END -->", build_poem_cards(items[:4], "", "poetry/"))
    print(f"Done. Processed {created} new poem(s), generated {len(items)} poem page(s), and updated index.html + poetry/index.html.")
    git_push_if_configured()
