# WARP.md

This guide helps operate this repo from Warp (warp.dev), and explains the two modes: Flask and Static (Pages + Workers).

Modes
- Flask (full features): server-rendered pages, admin tools, on-demand cache under static/games/bin, SHA checks, zip diagnostics.
- Static (serverless): pure front-end pages (index.html/game.html) + Cloudflare Workers proxy on /stream; no local cache or SHA, easy deploy.

Project overview
- Emularity (DOSBox) runs in-browser; the front-end mounts a zip as a drive.
- Game metadata: static/games/games.json; covers under static/games/img/<id>/cover.*

Flask quickstart (local dev)
- POSIX
```sh path=null start=null
pip3 install flask
# optional: pre-download game zips
git submodule update --init --recursive --remote && python3 ./static/games/download_data.py
python3 app.py
```

- Windows PowerShell
```powershell path=null start=null
python -m pip install flask
# optional: pre-download game zips
git submodule update --init --recursive --remote; python .\static\games\download_data.py
python .\app.py
```

- Refresh game data later
```sh path=null start=null
git submodule update --recursive --remote
python3 ./static/games/download_data.py
```

Static (Pages + Workers) quickstart
1) Workers (proxy /stream)
```sh path=null start=null
npm i -g wrangler
wrangler login
cd cloudflare-workers
# For pages.dev testing, allow the Pages origin
wrangler deploy --var ALLOW_ORIGIN="https://<your-pages>.pages.dev"
```
2) Pages (front-end)
- edit static/js/config.js and set your workers.dev origin:
```js path=null start=null
window.CDG_STREAM_ORIGIN = "https://<your-worker>.workers.dev";
```
- link this repo in Cloudflare Pages and deploy root directory.

Tips
- For pages.dev + workers.dev, make sure:
  - Worker deploy includes ALLOW_ORIGIN to your Pages URL
  - Front-end config sets window.CDG_STREAM_ORIGIN to your workers.dev URL
- For same-origin (custom domain), route /stream/* to Worker and leave config.js empty.
- In dark theme, sidebar readability is tuned via CSS variables; adjust in game.html if needed.

- Game metadata loading
  - Game metadata is read once at import time from static/games/games.json; a convenience list is derived for entries with cover images.
```python path=C:\Users\Administrator\cursor\chinese-dos-games-web\game_infos.py start=7
with open(os.path.join(root, 'static', 'games', 'games.json'), encoding='utf8') as f:
    content = f.read()
    game_infos = json.loads(content)

game_infos_with_cover = list()
for identifier, game_info in game_infos['games'].items():
    if 'coverFilename' in game_info.keys():
        game_infos_with_cover.append(game_info)
```

- Templates and front-end integration
  - Server-side templates live under templates/ and extend templates/base.html, which pulls Bootstrap and prefetches emulator assets from static/emularity/.
  - The game page templates/game.html constructs a DosBoxLoader and points it to a zipped game file under static/games/bin/<identifier>.zip, selecting drive type (cdrom/floppy/hdd) based on metadata. A small JS helper (static/js/game.js) toggles a CSS-based fullscreen mode for the canvas.

Operational prerequisites
- The application requires static/games/games.json and associated assets. Run the data-fetch commands above before starting the server, otherwise import of game_infos.py will fail.

Flask extra (optional)
- Admin: /admin/missing, zip diagnostics, cache stats are only in Flask mode.
- On-demand cache settings (`/bin/<id>.zip`): env vars GAMES_CACHE_MAX_GB, GAMES_SKIP_SHA.
- Stream proxy mode in Flask: USE_STREAM_PROXY=1; disable local /bin with DISABLE_BIN_ROUTE=1.

---

## Recent changes by Agent Mode (2025-10-08)

Overview of modifications applied to this fork to enable a lightweight, on-demand setup with Traditional Chinese support:

- On-demand download + server cache + mountZip
  - Added a route: `GET /bin/<identifier>.zip` in `app.py`.
  - Behavior: if `static/games/bin/<identifier>.zip` is missing or sha mismatch, download from `https://dos-bin.zczc.cz/<identifier>.zip`, verify SHA256 (from `games.json`), then cache and serve.
  - No server-side unzip. Front-end continues to use Emularity’s `mountZip`.

- Cache limit with LRU eviction
  - New env var `GAMES_CACHE_MAX_GB` (default 5 GiB) to cap total size in `static/games/bin`.
  - Eviction strategy removes least-recently-used zip files based on file atime; atime is updated on each serve.

- Language toggle (Simplified/Traditional)
  - New route: `GET /lang/<code>` where `<code>` ∈ {`zh-Hans`, `zh-Hant`} to set a cookie `lang` (30-day expiry).
  - Templates read `lang` from context and render labels and game names accordingly.

- Traditional Chinese generation
  - Runtime fallback (in `game_infos.py`): if `name.zh-Hant` is missing, attempt OpenCC `s2twp`; fallback to `zh-Hans` when OpenCC not present.
  - One-time converter script: `static/games/convert_zh_hant.py` which fills/overwrites missing or identical `zh-Hant` with `s2twp`-converted values and writes back to `games.json` (with timestamped backup).

- About page cache stats and index title i18n
  - About page shows current cache usage, limit, and file count.
  - Index page `<title>` reflects current language.

- Admin page for missing files and cache management
  - `GET /admin/missing`: shows a categorized list (all/error/ok), with keyword filter (`q`) and display limit (`limit`). Each item shows a status badge (error/missing).
  - `POST /admin/missing/mark`: mark a given identifier as missing (appends to `manual` array in `static/games/missing.json`).
  - `POST /admin/missing/rescan`: triggers background rescan (non-blocking) by dynamically loading `static/games/update_list.py`.
  - `POST /admin/cache/clear`: clears cached zip files under `static/games/bin`.
  - Navbar link "管理" points to `/admin/missing`.

- Auto background scan on first request
  - On Flask >= 3, `before_first_request` is removed. Implemented a one-time background scan via `@app.before_request` with a process-local flag and lock.

- Zip diagnostics endpoint
  - `GET /admin/zip/<identifier>/check`: returns json {exists, size, expected_sha256, actual_sha256, sha_match, zip_ok, skip_sha_check}.

- Theme toggle
  - `GET /theme/<mode>` sets `theme` cookie (light/dark). Navbar shows an icon-only toggle (☀️/🌙) and base `<body>` gets `theme-<mode>` class; dark theme overrides in `static/css/main.css`.

Paths touched (high level)
- `app.py`: on-demand cache route, LRU limit, lang cookie, context injection, search across names, cache stats for About.
- `game_infos.py`: ensure `zh-Hant` exists; runtime OpenCC fallback uses `s2twp`.
- `templates/`: language-aware UI across pages; navbar language switch; game page still uses `mountZip` but now points to `/bin/<identifier>.zip`.
- `static/games/convert_zh_hant.py`: one-time converter script.
- `README.md`: Traditional Chinese instructions with new on-demand and conversion guidance.

Operational notes
- Optional dependency: `opencc-python-reimplemented`. When present, runtime fallback produces better `zh-Hant` for entries missing it.
- Environment variable for cache cap:
  - PowerShell: `setx GAMES_CACHE_MAX_GB 10` (persists) or `$env:GAMES_CACHE_MAX_GB = 10` (session)
  - Bash: `export GAMES_CACHE_MAX_GB=10`
- Optional troubleshooting: skip SHA256 validation for downloads (diagnostics only)
  - PowerShell: `$env:GAMES_SKIP_SHA = 1; python app.py`
  - Bash: `GAMES_SKIP_SHA=1 python app.py`
- Pre-download is no longer required; still available via `python static/games/download_data.py`.
