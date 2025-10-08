from flask import Flask
from flask import render_template, redirect, url_for, make_response, request, send_file, abort, jsonify

from game_infos import game_infos, game_infos_with_cover
import json
import os
import hashlib
import urllib.request
import urllib.parse
import tempfile
import time
import threading
import importlib.util
from flask import flash

number_to_show_on_index = 42

app = Flask(__name__)

# Constants for on-demand download cache
ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.normcase(os.path.join(ROOT, 'static', 'games', 'bin'))
REMOTE_PREFIX = "https://dos-bin.zczc.cz/"
BUF_SIZE = 65536
# Cache size limit (bytes). Default 5 GiB; override with env GAMES_CACHE_MAX_GB
try:
    MAX_CACHE_BYTES = int(float(os.getenv('GAMES_CACHE_MAX_GB', '5')) * (1024 ** 3))
except Exception:
    MAX_CACHE_BYTES = 5 * (1024 ** 3)

# Optional: allow skipping SHA256 check for troubleshooting (0 by default)
try:
    SKIP_SHA_CHECK = bool(int(os.getenv('GAMES_SKIP_SHA', '0')))
except Exception:
    SKIP_SHA_CHECK = False


def _fmt_size(num_bytes: int) -> str:
    try:
        num = float(num_bytes)
    except Exception:
        return str(num_bytes)
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB']
    i = 0
    while num >= 1024 and i < len(units) - 1:
        num /= 1024.0
        i += 1
    return f"{num:.2f} {units[i]}"


def _current_lang():
    code = request.cookies.get('lang')
    if code in ('zh-Hans', 'zh-Hant'):
        return code
    return 'zh-Hant'


def _current_theme():
    t = (request.cookies.get('theme') or '').lower()
    if t in ('light', 'dark'):
        return t
    return 'light'


@app.context_processor
def inject_lang():
    return dict(lang=_current_lang(), theme=_current_theme())


def _cache_file_entries():
    entries = []
    if not os.path.isdir(CACHE_DIR):
        return entries
    for de in os.scandir(CACHE_DIR):
        if not de.is_file():
            continue
        name = de.name
        if not name.lower().endswith('.zip'):
            continue
        if name.endswith('.part'):
            continue
        try:
            st = de.stat()
            atime = getattr(st, 'st_atime', st.st_mtime)
            entries.append((de.path, st.st_size, atime))
        except FileNotFoundError:
            pass
    return entries


def _cache_total_size():
    return sum(size for _, size, __ in _cache_file_entries())


def _ensure_cache_limit():
    entries = _cache_file_entries()
    total = sum(size for _, size, __ in entries)
    if total <= MAX_CACHE_BYTES:
        return
    entries.sort(key=lambda t: t[2])  # by atime asc
    for path, size, _ in entries:
        try:
            os.remove(path)
        except Exception:
            continue
        total -= size
        if total <= MAX_CACHE_BYTES:
            break


def _sha256_file(path):
    sha256 = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def _ensure_cached_zip(identifier):
    """
    Ensure the zip for a game identifier exists and has correct sha256.
    If missing or invalid, download it to the cache directory.
    Returns the absolute file path to the cached zip.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    dest_path = os.path.normcase(os.path.join(CACHE_DIR, f"{identifier}.zip"))

# Get expected sha from game_infos
    gi = game_infos['games'].get(identifier)
    if not gi:
        abort(404)
    expected_sha = gi.get('sha256')

    # If exists and sha ok (or skipping), return
    if os.path.isfile(dest_path):
        if SKIP_SHA_CHECK or not expected_sha:
            return dest_path
        try:
            if _sha256_file(dest_path) == expected_sha:
                return dest_path
        except Exception:
            pass

    # Download to temp file then move
    url = REMOTE_PREFIX + urllib.parse.quote(identifier) + '.zip'
    fd, tmp_path = tempfile.mkstemp(prefix=f"{identifier}.", suffix=".part", dir=CACHE_DIR)
    os.close(fd)
    try:
        urllib.request.urlretrieve(url, tmp_path)
        if expected_sha and not SKIP_SHA_CHECK:
            actual_sha = _sha256_file(tmp_path)
            if actual_sha != expected_sha:
                # Remove bad file
                try:
                    os.remove(tmp_path)
                finally:
                    # Print diagnostic to server log
                    print(f"[SHA MISMATCH] id={identifier} expected={expected_sha} actual={actual_sha}")
                    abort(502, description='Downloaded file hash mismatch')
        # Atomic move into place
        os.replace(tmp_path, dest_path)
        # Enforce cache limit after adding
        _ensure_cache_limit()
        return dest_path
    except Exception as e:
        # Clean up partial download
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        finally:
            abort(502, description=str(e))


@app.route('/lang/<code>')
def set_lang(code):
    if code not in ('zh-Hans', 'zh-Hant'):
        abort(400)
    resp = redirect(request.headers.get('Referer') or url_for('index'))
    resp.set_cookie('lang', code, max_age=30 * 24 * 3600)
    return resp


@app.route('/theme/<mode>')
def set_theme(mode):
    mode = (mode or '').lower()
    if mode not in ('light', 'dark'):
        abort(400)
    resp = redirect(request.headers.get('Referer') or url_for('index'))
    resp.set_cookie('theme', mode, max_age=365 * 24 * 3600)
    return resp


@app.route('/')
def index():
    game_infos_to_show = game_infos_with_cover[:number_to_show_on_index - 1]
    return render_template('index-imgs.html', game_infos=game_infos_to_show, game_count=len(game_infos['games']))


@app.route('/about')
def about():
    entries = _cache_file_entries()
    total = sum(size for _, size, __ in entries)
    info = {
        'total': total,
        'max': MAX_CACHE_BYTES,
        'count': len(entries),
        'total_human': _fmt_size(total),
        'max_human': _fmt_size(MAX_CACHE_BYTES),
    }
    return render_template('about.html', games=game_infos['games'], cache_info=info)


@app.route('/games/')
def games():
    return render_template('games.html', games=game_infos['games'])


@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    if query is None:
        return render_template('error.html'), 404
    query = str(query)
    search_games = dict()
    for identifier, value in game_infos['games'].items():
        names = value.get('name', {})
        zh_hans = names.get('zh-Hans', '')
        zh_hant = names.get('zh-Hant', '')
        en = names.get('en', '')
        if query in zh_hans or query in zh_hant or query in en:
            search_games[identifier] = value
    return render_template('search.html', games=search_games, query=query)


@app.route('/games/<identifier>/')
def game(identifier):
    game_info = game_infos["games"].get(identifier)
    if not game_info:
        abort(404)
    return render_template('game.html', game_info=game_info)


@app.route('/bin/<identifier>.zip')
def game_bin(identifier):
    """Serve game zip via on-demand download + server cache."""
    cached = _ensure_cached_zip(identifier)
    # Update atime for LRU and enforce limit
    try:
        os.utime(cached, None)
    except Exception:
        pass
    _ensure_cache_limit()
    return send_file(cached, mimetype='application/zip', as_attachment=False, conditional=True)


# ----- Admin: missing games -----
import zipfile

@app.route('/admin/zip/<identifier>/check', methods=['GET'])
def admin_zip_check(identifier):
    gi = game_infos['games'].get(identifier)
    if not gi:
        return jsonify({'error': 'unknown identifier'}), 404
    expected_sha = gi.get('sha256')
    path = os.path.join(CACHE_DIR, f"{identifier}.zip")
    exists = os.path.isfile(path)
    size = os.path.getsize(path) if exists else 0
    actual_sha = _sha256_file(path) if exists else None
    sha_match = (actual_sha == expected_sha) if (actual_sha and expected_sha) else None
    zip_ok = None
    if exists:
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                bad = zf.testzip()
                zip_ok = (bad is None)
        except Exception:
            zip_ok = False
    return jsonify({
        'identifier': identifier,
        'exists': exists,
        'size': size,
        'expected_sha256': expected_sha,
        'actual_sha256': actual_sha,
        'sha_match': sha_match,
        'zip_ok': zip_ok,
        'skip_sha_check': SKIP_SHA_CHECK,
    })


# ----- Admin: missing games -----

def _load_missing_info():
    path = os.path.join(ROOT, 'static', 'games', 'missing.json')
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf8') as f:
            return json.load(f)
    except Exception:
        return None


def _start_rescan_in_background(prefix: str = None, threads: int = None):
    """Start a background scan by dynamically loading the scanner script."""
    prefix = prefix or REMOTE_PREFIX
    try:
        threads = int(threads or os.getenv('SCAN_THREADS', '20'))
    except Exception:
        threads = 20
    script_path = os.path.join(ROOT, 'static', 'games', 'update_list.py')

    def _runner():
        try:
            if os.path.isfile(script_path):
                spec = importlib.util.spec_from_file_location("_upd_list", script_path)
                mod = importlib.util.module_from_spec(spec)
                assert spec.loader is not None
                spec.loader.exec_module(mod)
                # call scan(prefix=..., concurrency=...)
                mod.scan(prefix=prefix, concurrency=threads)
        except Exception:
            # Swallow in background to avoid crashing the app
            pass

    t = threading.Thread(target=_runner, daemon=True)
    t.start()


@app.route('/admin/missing', methods=['GET'])
def admin_missing():
    info = _load_missing_info()
    started = request.args.get('started') == '1'

    # Filtering parameters
    q = (request.args.get('q') or '').strip()
    try:
        limit = int(request.args.get('limit') or 0)
    except Exception:
        limit = 0
    group = (request.args.get('group') or 'all').lower()
    if group not in ('all', 'error', 'ok'):
        group = 'all'

    # Build status for all games
    games_map = game_infos.get('games', {})
    all_ids = sorted(games_map.keys())

    missing_set = set()
    manual_set = set()
    if info and isinstance(info, dict):
        missing_set = set(info.get('missing', []) or [])
        manual_set = set(info.get('manual', []) or [])
    combined_missing = missing_set | manual_set

    items = []  # list of dict: {id, name, status}
    for ident in all_ids:
        g = games_map.get(ident, {})
        name = (g.get('name', {}) or {}).get('zh-Hant') or ident
        status = None
        if ident in combined_missing:
            status = 'missing'
        else:
            path = os.path.join(CACHE_DIR, f"{ident}.zip")
            if os.path.isfile(path):
                # quick zip check
                z_ok = None
                try:
                    with zipfile.ZipFile(path, 'r') as zf:
                        bad = zf.testzip()
                        z_ok = (bad is None)
                except Exception:
                    z_ok = False
                status = 'ok' if z_ok else 'error'
            else:
                status = 'ok'  # 未下載者不先判壞，顯示為可玩（按需下載）
        items.append({'id': ident, 'name': name, 'status': status})

    # Apply keyword filter
    if q:
        items = [it for it in items if (q in it['id'] or q in it['name'])]

    # Counters
    total_all = len(items)
    total_error = sum(1 for it in items if it['status'] == 'error')
    total_ok = sum(1 for it in items if it['status'] == 'ok')

    # Apply group filter
    if group == 'error':
        items = [it for it in items if it['status'] == 'error']
    elif group == 'ok':
        items = [it for it in items if it['status'] == 'ok']

    # Apply limit
    if limit and limit > 0:
        items_display = items[:limit]
    else:
        items_display = items

    cache_stats = {
        'total': _cache_total_size(),
        'max': MAX_CACHE_BYTES,
    }
    cache_stats['total_human'] = _fmt_size(cache_stats['total'])
    cache_stats['max_human'] = _fmt_size(cache_stats['max'])

    cache_cleared = request.args.get('cache_cleared') == '1'

    return render_template(
        'admin_missing.html',
        info=info,
        started=started,
        q=q,
        limit=limit,
        group=group,
        items_display=items_display,
        total_all=total_all,
        total_error=total_error,
        total_ok=total_ok,
        cache_stats=cache_stats,
        cache_cleared=cache_cleared,
    )


@app.route('/admin/missing/rescan', methods=['POST'])
def admin_missing_rescan():
    _start_rescan_in_background()
    return redirect(url_for('admin_missing', started=1))


@app.route('/admin/cache/clear', methods=['POST'])
def admin_cache_clear():
    # Remove cached zip files safely (only .zip inside CACHE_DIR)
    removed = 0
    if os.path.isdir(CACHE_DIR):
        for de in os.scandir(CACHE_DIR):
            try:
                if de.is_file() and de.name.lower().endswith('.zip'):
                    os.remove(de.path)
                    removed += 1
            except Exception:
                continue
    return redirect(url_for('admin_missing', cache_cleared=1))


@app.route('/admin/missing/mark', methods=['POST'])
def admin_missing_mark():
    ident = (request.form.get('identifier') or '').strip()
    if not ident:
        return redirect(url_for('admin_missing'))
    path = os.path.join(ROOT, 'static', 'games', 'missing.json')
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf8') as f:
                data = json.load(f)
        except Exception:
            data = {}
    # Ensure keys exist
    data.setdefault('prefix', REMOTE_PREFIX)
    data.setdefault('scanned', 0)
    data.setdefault('missing_count', data.get('missing_count', 0))
    data.setdefault('missing', data.get('missing', []))
    data.setdefault('manual', data.get('manual', []))
    if ident not in data['manual']:
        data['manual'].append(ident)
    # write back
    try:
        with open(path, 'w', encoding='utf8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return redirect(url_for('admin_missing'))


@app.route('/games/<identifier>/logo/emularity_color_small.png')
def emularity_logo(identifier):
    return redirect(url_for('static', filename='emularity/emularity_color_small.png'), code=301)


# One-time auto background scan on first request (Flask>=3 compatibility)
_auto_scan_flag = False
_auto_scan_lock = threading.Lock()

@app.before_request
def _auto_scan_once():
    global _auto_scan_flag
    if not _auto_scan_flag:
        with _auto_scan_lock:
            if not _auto_scan_flag:
                _start_rescan_in_background()
                _auto_scan_flag = True


if __name__ == '__main__':
    app.run(debug=True)
