# OsmoticPoet — How to Add Poems & Music

Use **lowercase filenames with hyphens** (no spaces) and give matching files the **same name** before the extension.

### Cover Image Sizes (Cheat Sheet — also saved in `assets\images\_IMAGE-SIZES.txt`)
- **Poems:** **`896 × 1120`** (4:5 portrait, `.jpg` or `.png`)
- **Music (YouTube):** **`1280 × 720`** (16:9 landscape, `.jpg` or `.png`)

---

## 1. How to Add a New Song
1. Put your files into `F:\Poetry Website\music\inbox\`:
   - **YouTube track (recommended, saves storage):** Drop `my-song.txt` with the **title on line 1**, **`YouTube: <url>` on line 2**, and **`Tags: ...` on line 3** (see `_music-template.txt` in `music\inbox\`), plus optional lyrics and optional **`1280 × 720` (16:9 landscape)** `my-song.jpg` cover (if omitted, the YouTube thumbnail is fetched automatically).
   - **OR Already an `.mp4` (e.g. YouTube download):** Drop `my-song.mp4` (optional `my-song.png`/`.jpg` cover and `my-song.txt` lyrics)
   - **OR Audio + Image/Video:** `my-song.wav` (or `.mp3`) + `my-song.png` (or `.jpg`, `.mp4`), plus optional `my-song.txt` lyrics
2. Double-click **`publish-music.bat`** in `F:\Poetry Website\`.
3. What happens automatically:
   - FFmpeg creates `music/tracks/my-song.mp4` and `music/tracks/my-song.mp3`.
   - A dedicated page `music/my-song.html` is created (showing image + MP3 player underneath if you used an image, or video player inside the frame if you used a video, plus lyrics and a comment box).
   - `music/index.html` and the **4 newest** cards on `index.html` update automatically.
   - Your inbox files are moved to `music/inbox/processed/`.
   - Once you connect a live host via Git, it also auto-uploads (`git push`).
4. **To add or update lyrics on an existing song:** save `<song-name>.txt` (for example, `never-built-for-clouds.txt`) directly in `F:\Poetry Website\music\tracks\` and double-click **`publish-music.bat`**.
5. **To build a `1280 × 720` YouTube `.mp4` without DaVinci Resolve:** drop your `1280 × 720` image + `.mp4` (or `.mp3`/`.wav`) with matching names into `F:\Poetry Website\music\youtube-maker\` and double-click **`make-youtube-mp4.bat`**. The finished `<song-name>-youtube.mp4` is saved to **`Desktop\YouTube-Uploads\`**; verify it, then delete the two original files from `music\youtube-maker\`.

---

## 2. How to Add a New Poem
1. Put these files into `F:\Poetry Website\poetry\inbox\`:
   - **Poem text:** `my-poem.txt` (put the **title on line 1**, optionally **`Tags: ...` on line 2**—see `_poem-template.txt` in `poetry\inbox\`—leave a blank line, then the poem)
   - **Cover image (recommended):** `my-poem.jpg` (or `.png`, `.webp`)
   - **Audio reading (optional, for listening):** `my-poem.mp3` (or `.wav`)
2. Double-click **`publish-poetry.bat`** in `F:\Poetry Website\`.
3. What happens automatically:
   - `poetry/my-poem.html` is created with the cover, MP3 player slot, full poem, and comment box.
   - `poetry/index.html` and the **4 newest** cards on `index.html` update automatically.
   - Your inbox files are moved to `poetry/inbox/processed/`.

---

---

## 3. How to Add or Replace an Image or Audio on an Existing Poem
1. Find the poem's exact **lowercase-with-hyphens** filename in `F:\Poetry Website\poetry\poems\` (for example, `spin.txt` or `what-the-morning-gives.txt`).
2. Drop the matching file into the right folder:
   - **Cover image (`896 × 1120` `.png` or `.jpg`):** put `what-the-morning-gives.png` into `F:\Poetry Website\assets\images\` *(if replacing an existing `.jpg` with a `.png`—or vice versa—delete the old one so only one image remains)*
   - **Audio reading (`.mp3`):** put `what-the-morning-gives.mp3` into `F:\Poetry Website\poetry\poems\`
3. Double-click **`publish-poetry.bat`**.

---

## 4. How to Remove a Poem
1. Delete `poetry/poems/<poem-name>.txt`, `poetry/poems/<poem-name>.json`, and `poetry/<poem-name>.html`.
2. Double-click **`publish-poetry.bat`** to rebuild the pages and update `https://osmoticpoet.com`.

---

## 5. Comments (Cloudflare Worker)
- Every poem and song page has a **Leave a Note** form that posts to `/api/note`, handled by the `osmoticpoet-mailer` Cloudflare Worker (`mailer-worker/`).
- Comments are emailed straight to `mgsnell201@gmail.com` via Cloudflare Email Sending (`notes@osmoticpoet.com`), with the poem or song title in the email subject.

---

## 6. Future Ideas — Reader Discovery & Reading List (Brainstorm / Planned)
How readers can narrow down ~500 poems and build their own reading session:

1. **Cover Checkboxes → "My Reading List"**
   - Each cover card on `/poetry/` (and `/music/`) has a subtle checkbox / bookmark icon in the corner.
   - Selected poems are saved in `localStorage` so they persist across visits.
   - A **`View Selected (N)`** + **`Clear`** bar lets readers filter the archive to only their checked poems.
   - Inside that Reading List, **`← Previous Poem`** / **`Next Poem →`** steps through only their selected poems, and **`← Previous page`** returns to their Reading List.
2. **Broad Category / Style Pills (Coarse Filter)**
   - 6–10 broad buckets at the top of `/poetry/` (for example: `All`, `Nature & Seasons`, `Holidays & Celebrations`, `Love & Longing`, `Humor & Wit`, `Faith & Reflection`, `Life & Memory`, `Short Reads`) stored in each poem's `poetry/poems/<stem>.json` file.
   - Shrinks ~500 poems down to ~30–60 in one click before readers check off favorites.
3. **"Surprise Me" (Random Poem) Button**
   - One-click button on `/poetry/` that opens a random poem for visitors who don't know where to start.
4. **"Start Here / Poet's Picks" Collection**
   - A small curated tab or shelf of 8–12 flagship poems so first-time visitors immediately experience your best work.
5. **Optional 1–2 Line Opening Teaser**
   - A brief preview of the poem's opening lines on hover or in a list view.
