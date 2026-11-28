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
KOKORO_PYTHON = Path(r"F:\kokoro-tts\.venv\Scripts\python.exe")
KOKORO_SCRIPT = Path(r"F:\kokoro-tts\narrate_all.py")

TEXT_EXTS = {".txt", ".md"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac"}

TAG_MAP = {
    "nature": "Nature & Seasons",
    "seasons": "Nature & Seasons",
    "nature & seasons": "Nature & Seasons",
    "holiday": "Holidays & Celebrations",
    "holidays": "Holidays & Celebrations",
    "celebrations": "Holidays & Celebrations",
    "holidays & celebrations": "Holidays & Celebrations",
    "love": "Love & Longing",
    "longing": "Love & Longing",
    "love & longing": "Love & Longing",
    "humor": "Humor & Wit",
    "wit": "Humor & Wit",
    "humor & wit": "Humor & Wit",
    "faith": "Faith & Reflection",
    "reflection": "Faith & Reflection",
    "faith & reflection": "Faith & Reflection",
    "life": "Life & Memory",
    "memory": "Life & Memory",
    "life & memory": "Life & Memory",
    "short": "Short Reads",
    "short reads": "Short Reads",
}


def parse_poem_text_and_tags(raw: str) -> tuple[str, list[str]]:
    lines = raw.splitlines()
    tags: list[str] = []
    if len(lines) >= 2 and re.match(r"^\s*tags\s*:", lines[1], re.I):
        tag_str = re.sub(r"^\s*tags\s*:\s*", "", lines[1], flags=re.I)
        for part in re.split(r"[,;|]+", tag_str):
            key = part.strip().lower()
            if key in TAG_MAP and TAG_MAP[key] not in tags:
                tags.append(TAG_MAP[key])
        lines = [lines[0], *lines[2:]]
    body_lines = [ln for ln in lines[1:] if ln.strip()]
    if len(body_lines) <= 14 and "Short Reads" not in tags:
        tags.append("Short Reads")
    cleaned = "\n".join(lines).strip() + "\n"
    return cleaned, tags


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
        if not p.is_file() or p.name.startswith("_"):
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

        raw_text = text_file.read_text(encoding="utf-8", errors="ignore")
        cleaned_text, parsed_tags = parse_poem_text_and_tags(raw_text)
        (POEMS_DATA / f"{stem}.txt").write_text(cleaned_text, encoding="utf-8")
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

        meta: dict[str, object] = {"added_at": time.time()}
        if parsed_tags:
            meta["tags"] = parsed_tags
        (POEMS_DATA / f"{stem}.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        count += 1

    return count


def narrate_missing_poems() -> None:
    missing = [p for p in sorted(POEMS_DATA.glob("*.txt")) if not (POEMS_DATA / f"{p.stem}.mp3").exists()]
    if not missing:
        return
    if not KOKORO_PYTHON.exists() or not KOKORO_SCRIPT.exists():
        print("Note: Kokoro TTS not found; skipping auto-narration.")
        return
    print(f"Narrating {len(missing)} poem(s) via Kokoro TTS...")
    subprocess.run([str(KOKORO_PYTHON), str(KOKORO_SCRIPT)], check=True)


def optimize_existing_pngs() -> None:
    originals = IMAGES / "originals"
    originals.mkdir(parents=True, exist_ok=True)
    for png in list(IMAGES.glob("*.png")):
        if png.name.startswith("_"):
            continue
        jpg = IMAGES / f"{png.stem}.jpg"
        run_ffmpeg(["-i", str(png), "-vf", "scale='min(896,iw)':-2", "-q:v", "3", str(jpg)])
        shutil.move(str(png), str(originals / png.name))


def get_poem_tags(stem: str) -> list[str]:
    meta_path = POEMS_DATA / f"{stem}.json"
    if meta_path.exists():
        try:
            tags = json.loads(meta_path.read_text(encoding="utf-8")).get("tags", [])
            if isinstance(tags, list):
                return [str(t) for t in tags if t]
        except Exception:
            pass
    return []


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
    parsed: list[tuple[str, str, str]] = []
    for stem in stems:
        raw = txt_files[stem].read_text(encoding="utf-8").strip()
        lines = raw.splitlines()
        title = lines[0].strip() if lines else title_from_stem(stem)
        body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
        parsed.append((stem, title, body))

    results: list[tuple[str, str]] = []

    for idx, (stem, title, body) in enumerate(parsed):
        title_esc = html.escape(title)
        body_esc = html.escape(body)
        prev_poem = parsed[idx - 1] if idx > 0 else None
        next_poem = parsed[idx + 1] if idx + 1 < len(parsed) else None
        prev_nav = (
            f'<a class="piece-nav-btn" href="{prev_poem[0]}.html" title="{html.escape(prev_poem[1])}">&larr; Previous Poem</a>'
            if prev_poem
            else '<span class="piece-nav-btn is-disabled" aria-disabled="true">&larr; Previous Poem</span>'
        )
        next_nav = (
            f'<a class="piece-nav-btn" href="{next_poem[0]}.html" title="{html.escape(next_poem[1])}">Next Poem &rarr;</a>'
            if next_poem
            else '<span class="piece-nav-btn is-disabled" aria-disabled="true">Next Poem &rarr;</span>'
        )
        snippet = " ".join(ln.strip() for ln in body.splitlines() if ln.strip())[:155]
        desc_esc = html.escape(f"{title} — {snippet}" if snippet else f"{title} by OsmoticPoet")
        cover = find_cover(stem, "../")
        og_img = f"https://osmoticpoet.com/{cover.removeprefix('../')}" if cover else "https://osmoticpoet.com/assets/images/_poem-default.png" 
        mp3_exists = (POEMS_DATA / f"{stem}.mp3").exists()
        ld_json = json.dumps({
            "@context": "https://schema.org",
            "@type": "CreativeWork",
            "name": title,
            "url": f"https://osmoticpoet.com/poetry/{stem}.html",
            "image": og_img,
            "description": f"{title} — {snippet}" if snippet else f"{title} by OsmoticPoet",
            "author": {"@type": "Person", "name": "Marvin Snell", "alternateName": "OsmoticPoet"},
        }, ensure_ascii=False)

        img_html = f'          <img class="piece-cover" src="{cover}" alt="{title_esc} illustration">' if cover else ""
        if mp3_exists:
            audio_html = f"""          <div class="audio-box">
            <div class="audio-box-label">Listen to Poem (MP3)</div>
            <audio controls controlsList="nodownload" oncontextmenu="return false;" preload="metadata">
              <source src="poems/{stem}.mp3" type="audio/mpeg">
            </audio>
          </div>"""
        else:
            audio_html = f"""          <div class="audio-box">
            <div class="audio-box-label">Listen to Poem (MP3)</div>
            <p class="audio-note">Audio reading slot ready for <code>poetry/poems/{stem}.mp3</code>.</p>
          </div>"""

        page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_esc} — OsmoticPoet</title>
  <meta name="description" content="{desc_esc}">
  <link rel="canonical" href="https://osmoticpoet.com/poetry/{stem}.html">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{title_esc} — OsmoticPoet">
  <meta property="og:description" content="{desc_esc}">
  <meta property="og:url" content="https://osmoticpoet.com/poetry/{stem}.html">
  <meta property="og:image" content="{og_img}">
  <link rel="icon" href="../assets/favicon.svg" type="image/svg+xml">
  <link rel="icon" href="../assets/favicon-48x48.png" sizes="48x48" type="image/png">
  <link rel="icon" href="../favicon.ico" sizes="any">
  <link rel="apple-touch-icon" href="../assets/apple-touch-icon.png">
  <link rel="stylesheet" href="../css/styles.css?v=2">
  <script type="application/ld+json">{ld_json}</script>
</head>
<body>
  <header class="site-header">
    <div class="nav-inner">
      <a class="brand" href="../index.html">
        <img class="brand-logo" src="../assets/logo.svg" alt="" width="26" height="26" aria-hidden="true">
        <span>OsmoticPoet</span>
      </a>
      <button class="menu-toggle" type="button" aria-label="Toggle navigation">Menu</button>
      <ul class="nav-links">
        <li><a href="../index.html">Home</a></li>
        <li><a href="index.html" class="active">Poetry</a></li>
        <li><a href="../music/index.html">Music</a></li>
        <li><a href="../about/index.html">About</a></li>
          <li><a href="../privacy.html">Privacy</a></li>
      </ul>
    </div>
  </header>

  <main class="container">
    <section class="section">
      <a class="breadcrumb" href="index.html">&larr; Previous page</a>
      <div class="card piece-layout">
        <div class="piece-media">
{img_html}
{audio_html}
        </div>
        <div>
          <h1 class="piece-title">{title_esc}</h1>
          <p class="poem-stanza">{body_esc}</p>
          <div class="vote-bar" data-vote-id="poetry/{stem}">
            <div class="vote-actions">
              <button class="vote-btn" type="button" data-vote="up" aria-label="Like"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/></svg><span class="vote-count">0</span></button>
              <button class="vote-btn" type="button" data-vote="down" aria-label="Dislike"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z"/></svg><span class="vote-count">0</span></button>
            </div>
            <nav class="piece-nav" aria-label="Poem navigation">
              {prev_nav}
              {next_nav}
            </nav>
          </div>
        </div>
      </div>
    </section>

    <section class="section" id="comments">
      <div class="section-head">
        <h2 class="section-title">Leave a Note</h2>
        <span class="section-link">Sent directly via email</span>
      </div>
      <div class="card">
        <form class="comment-form" id="comment-form" action="/api/note" method="POST">
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
          <p class="form-disclaimer">Your email is optional, used only to reply to your note, and never shared or added to any mailing list. Prefer not to use the form? Email <a href="mailto:marvin@osmoticpoet.com">marvin@osmoticpoet.com</a> directly. &middot; <a href="../privacy.html">Privacy Policy</a></p>
        </form>
      </div>
    </section>

    <footer class="site-footer">
      <div>
        <p class="footer-brand">OsmoticPoet</p>
        <p class="footer-tagline">Words written for quiet hours, paired with sound.</p>
        <span class="footer-copy">&copy; 2026 Marvin Snell (OsmoticPoet). All rights reserved.</span>
      </div>
      <div>
        <p class="footer-heading">Explore</p>
        <ul class="footer-links">
          <li><a href="../index.html">Home</a></li>
          <li><a href="../poetry/index.html">Poetry</a></li>
          <li><a href="../music/index.html">Music</a></li>
          <li><a href="../about/index.html">About</a></li>
          <li><a href="../privacy.html">Privacy</a></li>
        </ul>
      </div>
    </footer>
  </main>

  <script src="../js/main.js?v=4" defer></script>
</body>
</html>
"""
        (POEMS_DIR / f"{stem}.html").write_text(page, encoding="utf-8")
        results.append((stem, title))

    return results


def build_poem_cards(items: list[tuple[str, str]], prefix: str, href_prefix: str, include_controls: bool = False) -> str:
    if not items:
        return '        <p class="poem-stanza muted">No poems yet.</p>'

    cards = []
    for num, (stem, title) in enumerate(items, start=1):
        title_esc = html.escape(title)
        cover = find_cover(stem, prefix)
        img_html = f'\n          <img class="media-card-img" loading="lazy" decoding="async" src="{cover}" alt="{title_esc} cover">' if cover else ""
        if include_controls:
            tags_attr = html.escape("|".join(get_poem_tags(stem)))
            attrs = f' data-stem="{stem}" data-tags="{tags_attr}"'
            select_html = f'\n          <span class="card-select" role="checkbox" tabindex="0" aria-checked="false" aria-label="Save {title_esc} to reading list" title="Save to Reading List">&#10003;</span>'
        else:
            attrs = ""
            select_html = ""
        cards.append(
            f"""        <a class="media-card" href="{href_prefix}{stem}.html"{attrs}>{select_html}{img_html}
          <div class="media-card-body">
              <h3 class="media-card-title">{title_esc}</h3>
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


def deploy_cloudflare() -> None:
    if not shutil.which("wrangler.cmd") and not shutil.which("wrangler"):
        return
    cmd_bin = "wrangler.cmd" if shutil.which("wrangler.cmd") else "wrangler"
    print("Deploying to https://osmoticpoet.com ...")
    subprocess.run([cmd_bin, "pages", "deploy", str(ROOT), "--project-name", "osmoticpoet", "--branch", "main"], check=True)


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
    narrate_missing_poems()
    optimize_existing_pngs()
    items = write_poem_pages()
    replace_section(POEMS_DIR / "index.html", "<!-- POEMS_START -->", "<!-- POEMS_END -->", build_poem_cards(items, "../", "", include_controls=True))
    replace_section(ROOT / "index.html", "<!-- HOME_POEMS_START -->", "<!-- HOME_POEMS_END -->", build_poem_cards(items[:4], "", "poetry/"))
    write_sitemap()
    print(f"Done. Processed {created} new poem(s), generated {len(items)} poem page(s), and updated index.html + poetry/index.html.")
    git_push_if_configured()
    deploy_cloudflare()
