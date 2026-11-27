# OsmoticPoet — How to Add Poems & Music

Use **lowercase filenames with hyphens** (no spaces) and give matching files the **same name** before the extension.

---

## 1. How to Add a New Song
1. Put your files into `F:\Poetry Website\music\inbox\`:
   - **Already an `.mp4` (e.g. YouTube download):** Just drop `my-song.mp4` (no video re-encoding needed; optional `my-song.png`/`.jpg` cover and `my-song.txt` lyrics)
   - **OR Audio + Image/Video:** `my-song.wav` (or `.mp3`) + `my-song.png` (or `.jpg`, `.mp4`), plus optional `my-song.txt` lyrics
2. Double-click **`publish-music.bat`** in `F:\Poetry Website\`.
3. What happens automatically:
   - FFmpeg creates `music/tracks/my-song.mp4` and `music/tracks/my-song.mp3`.
   - A dedicated page `music/my-song.html` is created (showing image + MP3 player underneath if you used an image, or video player inside the frame if you used a video, plus lyrics and a comment box).
   - `music/index.html` and the **4 newest** cards on `index.html` update automatically.
   - Your inbox files are moved to `music/inbox/processed/`.
   - Once you connect a live host via Git, it also auto-uploads (`git push`).

---

## 2. How to Add a New Poem
1. Put these files into `F:\Poetry Website\poetry\inbox\`:
   - **Poem text:** `my-poem.txt` (put the **title on line 1**, leave a blank line, then the poem)
   - **Cover image (recommended):** `my-poem.jpg` (or `.png`, `.webp`)
   - **Audio reading (optional, for listening):** `my-poem.mp3` (or `.wav`)
2. Double-click **`publish-poetry.bat`** in `F:\Poetry Website\`.
3. What happens automatically:
   - `poetry/my-poem.html` is created with the cover, MP3 player slot, full poem, and comment box.
   - `poetry/index.html` and the **4 newest** cards on `index.html` update automatically.
   - Your inbox files are moved to `poetry/inbox/processed/`.

---

## 3. Comments (Web3Forms)
- Every poem and song page has a **Leave a Note** form wired to your Web3Forms key (`38932bab-2025-40ac-b84e-f2ff021cd68f`).
- Comments are emailed straight to the email address you used on Web3Forms, with the poem or song title in the email subject.
