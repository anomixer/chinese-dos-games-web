import inspect
import json
import os

root = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

with open(os.path.join(root, 'static', 'games', 'games.json'), encoding='utf8') as f:
    content = f.read()
    game_infos = json.loads(content)

# Ensure zh-Hant exists for all games; use OpenCC s2t if available
try:
    from opencc import OpenCC  # type: ignore
    _cc = OpenCC('s2twp')  # 改用臺灣用語轉換
except Exception:
    _cc = None

for identifier, game_info in list(game_infos.get('games', {}).items()):
    name = game_info.get('name', {})
    zh_hant = name.get('zh-Hant')
    if not zh_hant or not str(zh_hant).strip():
        src = name.get('zh-Hans', '')
        if _cc:
            try:
                name['zh-Hant'] = _cc.convert(src)
            except Exception:
                name['zh-Hant'] = src
        else:
            # Fallback: copy zh-Hans if converter not available
            name['zh-Hant'] = src
    # Normalize back
    game_info['name'] = name

# Filter out missing games if a scan result exists
_missing_path = os.path.join(root, 'static', 'games', 'missing.json')
if os.path.isfile(_missing_path):
    try:
        with open(_missing_path, 'r', encoding='utf8') as mf:
            miss = json.load(mf)
        missing_list = set(miss.get('missing', [])) | set(miss.get('manual', []))
        # Remove missing identifiers from the catalog
        for identifier in list(game_infos.get('games', {}).keys()):
            if identifier in missing_list:
                del game_infos['games'][identifier]
    except Exception:
        pass

game_infos_with_cover = list()
for identifier, game_info in game_infos['games'].items():
    if 'coverFilename' in game_info.keys():
        game_infos_with_cover.append(game_info)
