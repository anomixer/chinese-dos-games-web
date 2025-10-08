# Project context summary (2025-10-08)

This file summarizes the changes and decisions made during today’s session to evolve anomixer/chinese-dos-games-web into a lightweight, Traditional Chinese–friendly, on‑demand Chinese DOS games site.

## Core feature changes

- On‑demand download + server cache + mountZip
  - New route: GET /bin/<identifier>.zip
  - Behavior: if static/games/bin/<identifier>.zip missing or sha mismatch, download from REMOTE_PREFIX + <identifier>.zip, verify SHA256 (games.json), then cache and serve
  - No server‑side unzip. Emularity mounts the zip directly via DosBoxLoader.mountZip

- Cache size limit with LRU eviction
  - Env: GAMES_CACHE_MAX_GB (default 5 GiB)
  - Enforce after adding files and on serve; deletes least‑recently‑used zip by atime

- Optional SHA bypass (diagnostics)
  - Env: GAMES_SKIP_SHA=1 to bypass SHA check while investigating remote changes
  - Logs [SHA MISMATCH] with expected/actual when mismatch is detected

- Search improvements
  - Search across zh‑Hans / zh‑Hant / en

- Language & Theme toggle
  - /lang/<code> where code ∈ {zh‑Hans, zh‑Hant} (cookie: lang)
  - /theme/<mode> where mode ∈ {light, dark} (cookie: theme)
  - Navbar shows only icon for theme (☀️/🌙)

- Traditional Chinese default UI
  - Templates default to zh‑Hant and render based on lang cookie across all pages

- About page shows cache stats
  - Current usage, limit, and file count

## Admin UX

- Admin page: /admin/missing
  - Categorized list: all / error / ok (with keyword q and limit)
  - Status badges for each item (error/missing)
  - POST /admin/missing/mark: mark an identifier as missing (appends to manual in static/games/missing.json)
  - POST /admin/missing/rescan: background rescan via static/games/update_list.py
  - POST /admin/cache/clear: removes cached zip under static/games/bin

- Zip diagnostics
  - GET /admin/zip/<identifier>/check → {exists, size, expected_sha256, actual_sha256, sha_match, zip_ok, skip_sha_check}

- Auto background scan (Flask 3 compatible)
  - Implemented via @app.before_request + a process‑local flag and lock

## Data and submodule

- static/games (submodule — now points to fork)
  - .gitmodules updated to https://github.com/anomixer/chinese-dos-games.git
  - README.md: Traditional Chinese + comparison table (rwv vs anomixer)
  - CONTRIBUTING.md: Traditional Chinese
  - convert_zh_hant.py: one‑time s2twp conversion (OpenCC) to fill zh‑Hant back into games.json (+ backup)
  - update_list.py: HEAD/Range GET scanner → outputs static/games/missing.json
  - missing.json: added manual list and seeded with "指环王" (upstream zip invalid)
  - .gitignore: includes bin/ to avoid caching zip in VCS

## Template/UI updates

- base.html: language‑aware labels; theme icon toggle; zh‑Hant default; navbar points to standard endpoints
- index-imgs.html / games.html / search.html / about.html / game.html: dynamic zh‑Hant/zh‑Hans rendering; search placeholders; labels; link texts
- game.html: zip URL now from /bin/<id>.zip; added cache‑busting query (?v=sha[:8]) to mitigate stale caches

## App wiring and compatibility

- Flask 3 compatibility: replaced before_first_request with before_request + flag/lock
- Exposed set_lang, set_theme endpoints

## Docs

- README.md
  - Clone + submodule init instructions (bash/PowerShell)
  - Optional predownload command (original upstream flow)
  - Local dev: python app.py
  - Render deployment guide: requirements.txt, gunicorn start command, disk mount to static/games/bin, env vars
  - Note: Render free tier doesn’t support persistent disks (use Hobby/Fly.io/external storage)
  - Troubleshooting: /admin/zip/<id>/check; GAMES_SKIP_SHA
  - Comparison table (rwv vs anomixer)

- WARP.md
  - Documented all new features/routes; admin page; zip diagnostics; auto scan; theme toggle; operational notes

## Branches & Git

- Submodule (static/games): feature/web-integration → merged (fast‑forward) into master and pushed
- Web (main repo): feature/on-demand-admin-theme → merged (fast‑forward) into master and pushed
- Deleted feature branches locally and on GitHub

## Render CI/CD and files

- requirements.txt added (flask, gunicorn, opencc-python-reimplemented)
- Removed render.yaml (disks not supported on free tier). Use UI to create Web Service; mount disk on Hobby plan or keep free testing without persistent cache

## Experiments (local‑only)

- app2.py + templates (*2.html) to test direct remote zip mounting (no local cache)
  - Uses REMOTE_PREFIX and direct URL mounting (subject to CORS). Created separate base2.html and v2 templates to avoid breaking original app
  - Not pushed yet; meant for local feasibility testing (CORS/latency)

## Recommendations & next steps

- For production with persistent cache: Fly.io (Volume) or Render Hobby (Disk) → mount static/games/bin; optionally add CDN in front
- For fully serverless: move cache to external object storage (R2/S3) and add a storage adapter or re‑implement zip delivery via serverless functions; add signed/302 delivery to avoid function timeouts for large zips
- Optional: add a v3 proxy‑stream route (no local cache) to avoid CORS and support Render Free testing; later place CDN in front

## Key env vars

- GAMES_CACHE_MAX_GB: total on‑disk cache cap (GiB; default 5)
- REMOTE_PREFIX: upstream zip base URL (default https://dos-bin.zczc.cz/)
- GAMES_SKIP_SHA: set 1 to skip SHA checks for diagnostics

## Notable routes

- User
  - /, /games/, /games/<identifier>/
  - /search?q=...
  - /lang/<code>, /theme/<mode>

- Admin
  - /admin/missing (GET), /admin/missing/rescan (POST), /admin/missing/mark (POST)
  - /admin/cache/clear (POST)
  - /admin/zip/<identifier>/check (GET)

- Zip delivery
  - /bin/<identifier>.zip (on‑demand + cache + SHA)

## Known caveats

- Some upstream zip files exist but are invalid archives (e.g., "指环王"). Use manual missing list or switch to a working mirror
- If using Render free tier, zip cache won’t persist across restarts (no disk). Use Hobby or Fly.io Volume for persistence
