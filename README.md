# chinese-dos-games-web
此專案可在瀏覽器中遊玩「中文 DOS 遊戲」。有兩種運行方式可選：
- Flask 版本：功能最完整（側欄操作/連結/管理頁/快取/診斷），但需要有伺服器（local server 或雲主機）。
- Static 版本：介面較精簡（已補上操作/連結側欄），可 Serverless 部署（本 repo 以 Cloudflare Pages + Workers 示範）。 👉[點我線上玩](https://chinese-dos-games-web.pages.dev)

本 repo 預設展示 Static 版本，並以 Cloudflare Pages（前端）+ Workers（/stream 代理）部署為例。

本分支已改為「按需下載（On-Demand）+ 伺服器快取（LRU）+ mountZip」方案，支援簡/繁切換，可切換明亮或暗黑主題，並提供一次性繁體化腳本。

## 兩種版本比較（重點）

| 項目 | Flask 版本 | Static 版本 |
| --- | --- | --- |
| 畫面/功能 | 最完整：頁面側欄（操作/連結/作弊）、管理頁、Zip 診斷、快取資訊 | 精簡：頁面側欄（操作/連結/作弊）+ 主題/語系；無後端管理頁與快取診斷 |
| 部署條件 | 需要伺服器（可本機或雲主機） | 可 Serverless（Cloudflare Pages + Workers） |
| 取得 Zip | 預設 /bin 按需下載 + 伺服器快取；或 /stream 代理；或遠端掛載（需 CORS） | 依賴 Workers 的 /stream 代理遠端 Zip；不落地，不需快取 |
| SHA 驗證 | 有（/bin 模式） | 無（純代理串流） |
| CORS 需求 | 無（同源 /bin）或由 /stream 代理解決 | 若使用 workers.dev 與 pages.dev，靠 Worker 回傳 CORS 標頭與前端 config 指定絕對 URL |

## 功能特點（Flask）
- 按需下載：首次進入遊戲時，伺服器才從遠端抓取該遊戲 zip，驗證 SHA256 後快取到本機。
- 伺服器快取：快取路徑為 `static/games/bin`，預設上限 5 GiB，採 LRU 自動清理（刪除最久未用檔案）。
- 無需伺服器端解壓：前端透過 Emularity 的 `mountZip` 直接掛載 zip。
- 簡/繁切換：導覽列可切換 `简体/繁體`，所有頁面與遊戲名稱會依 cookie 語系顯示（`zh-Hans`/`zh-Hant`）。
- 一次性繁體化：提供 `s2twp`（臺灣用語）轉換腳本，將 `games.json` 中缺少或未繁體化的名稱補齊 `zh-Hant`。
- 關於頁顯示快取資訊：目前使用量 / 上限、檔案數量。
- 管理頁面：`/admin/missing` 可檢視缺檔清單、重新掃描、清空快取、以關鍵字與筆數篩選清單；伺服器首次請求會自動啟動背景掃描。

## 安裝與執行

### 1) 從 Git 取得專案（Clone）
- Linux/macOS（bash）：
```sh
git clone --recursive https://github.com/anomixer/chinese-dos-games-web.git
cd chinese-dos-games-web
```
- Windows PowerShell：
```powershell
git clone --recursive https://github.com/anomixer/chinese-dos-games-web.git
Set-Location .\chinese-dos-games-web
```

（可跳過）若你想預先下載所有遊戲（原作者版本，會吃掉很大硬碟空間來存放遊戲zip檔）：
- Linux/macOS（bash）：
```sh
python3 ./static/games/download_data.py
```
- Windows PowerShell：
```powershell
python .\static\games\download_data.py
```

### 2) 安裝依賴
```sh
pip install -r requirements.txt
```

### 3) 啟動伺服器（本機開發）
```sh
python app.py
```
啟動後瀏覽器開啟首頁 ( http://localhost:5000 )，選擇遊戲即可。首次進入遊戲會觸發下載與快取；之後再進入同款遊戲將直接命中快取。

## 疑難排解
若遊戲頁顯示 failed to download game data
- 先直接打開 `/bin/<identifier>.zip` 看 HTTP 狀態碼（例如：`http://localhost:5000/bin/%E6%8C%87%E7%8E%AF%E7%8E%8B.zip`）。
- 檢查 zip 診斷：`/admin/zip/<identifier>/check`，看 `zip_ok`（zip 結構是否有效）與 `sha_match`（是否與 games.json 一致）。
- 若狀態為 502，主因可能為「SHA256 不一致」。伺服器日誌會印出 [SHA MISMATCH] 與 expected/actual 供比對。
- 臨時繞過（僅供測試）：
  - PowerShell：`$env:GAMES_SKIP_SHA = 1; python app.py`
  - Bash：`GAMES_SKIP_SHA=1 python app.py`
- 若確認遠端檔案已變更，可更新 `games.json` 對應遊戲的 `sha256` 值，或改用你的鏡像來源；對於「存在但壞掉」的檔案，可在管理頁對該遊戲執行「標記缺檔」。

- 切換語言：導覽列右側「繁體 / 简体」。
- 若要更改快取上限（預設 5 GiB）：
  - Linux/macOS（bash）：
    ```sh
    export GAMES_CACHE_MAX_GB=10
    python app.py
    ```
  - Windows PowerShell：
    ```powershell
    $env:GAMES_CACHE_MAX_GB = 10
    python app.py
    ```

### 4) 一次性繁體化（可選、建議）
此步驟會直接「寫回」 `static/games/games.json` 的 `name.zh-Hant` 欄位，使其為 `s2twp` 轉換後的繁體（臺灣用語）。

```sh
# 先安裝 OpenCC（若尚未安裝）
python -m pip install opencc-python-reimplemented

# 執行一次性轉換腳本：會先建立備份，再寫回 games.json
python static/games/convert_zh_hant.py
```

### 5)（可選）預先下載所有遊戲
本分支已改為按需下載，通常不需要預抓。但若你想離線使用，仍可：
```sh
python static/games/download_data.py
```

## 部署（Cloudflare Pages + Workers，Static 版本）

本 repo 已包含 Cloudflare Workers 專案（cloudflare-workers/），以及 Static 前端頁面（index.html、game.html）。

快速步驟（使用 pages.dev + workers.dev 測試網域）
1) 部署 Workers（/stream 代理）
- 安裝與登入
  ```sh
  npm i -g wrangler
  wrangler login
  ```
- 部署（允許的來源建議填你的 pages.dev 網域；也可先用 * 測試）
  ```sh
  cd cloudflare-workers
  wrangler deploy --var ALLOW_ORIGIN="https://你的專案.pages.dev"
  # 可選：指定 zip 鏡像
  # wrangler deploy --var REMOTE_PREFIX="https://your-mirror.example/"
  ```
  記下部署輸出的 workers.dev 網域，例如：https://your-subdomain.workers.dev

2) 設定前端指向 workers.dev
- 編輯 static/js/config.js
  ```js
  window.CDG_STREAM_ORIGIN = "https://your-subdomain.workers.dev";
  ```

3) 部署 Pages（前端）
- 在 Cloudflare Pages 連結本 repo，Build command 留空、Output directory 設根目錄（.）。
- 發佈完成後，打開 https://你的專案.pages.dev，選遊戲即可。

備註
- workers.dev 與 pages.dev 屬不同網域，需：
  1) Worker 回傳 CORS 標頭（wrangler.toml 的 ALLOW_ORIGIN 或 deploy 時 --var ALLOW_ORIGIN）
  2) 前端用 static/js/config.js 指定 workers.dev 絕對 URL
- 若改用自有網域且將 /stream/* 綁至 Worker，則可把 config.js 留空，前端直接用同源 /stream，無 CORS 顧慮。

你可以用兩種方式部署與測試：

A) 使用你自己的網域（同源，最簡，無 CORS）
- 把網域接入 Cloudflare DNS。
- 部署 Workers，設定路由把 `https://你的網域/stream/*` 指向 Worker。
- 將靜態站（本 repo）部署在相同網域（可用原本 Flask、或 Cloudflare Pages 綁定同網域）。
- 前端直接使用相對路徑 `/stream/<id>.zip`，同源無 CORS。

B) 直接用 Cloudflare 預設網域 pages.dev + workers.dev（快速測試）
- Pages 會提供 `https://你的專案.pages.dev`，Workers 會提供 `https://你的子域.workers.dev`。
- 這是跨網域，因此 Worker 需要回傳 CORS 標頭，前端也要呼叫絕對網址。
- 我已幫你調整：
  1) Worker 內建 CORS：wrangler.toml 變數 `ALLOW_ORIGIN="*"`（預設 *）。你也可改填你的 pages.dev 網域。
  2) 前端設定檔：`static/js/config.js`，把 `window.CDG_STREAM_ORIGIN` 設為你的 workers.dev，例如：
     ```js
     // static/js/config.js
     window.CDG_STREAM_ORIGIN = "https://your-subdomain.workers.dev";
     ```
  3) 遊戲頁 game.html 會自動使用 `${CDG_STREAM_ORIGIN}/stream/...`（若留空則用同源 `/stream`）。

部署步驟（快速）
1) Cloudflare Workers（代理 /stream）
- 進入 `cloudflare-workers/` 目錄：
  ```sh
  wrangler login
  wrangler deploy
  ```
- 如需修改上游來源（zip 鏡像）：
  ```sh
  wrangler deploy --var REMOTE_PREFIX="https://your-mirror.example/"
  ```

2) Cloudflare Pages（靜態站點）
- 直接把此 repo 綁定到 Pages 專案，根目錄發佈（不需 build 指令）。
- 若使用 workers.dev 測試網域，請編輯 `static/js/config.js`：
  ```js
  window.CDG_STREAM_ORIGIN = "https://your-subdomain.workers.dev";
  ```
- 發佈後，開 `https://你的專案.pages.dev`，選遊戲應會從 `workers.dev/stream/...` 取得 zip。

注意事項
- workers.dev 與 pages.dev 不同網域，必須依賴 Worker 的 CORS 標頭與前端設定的絕對 URL（上面已處理）。
- 若你切換到自己的網域並做 Workers 路由（同源），將 `static/js/config.js` 留空即可使用相對路徑 `/stream/...`，完全無 CORS 問題。
- Worker 已處理 Range 與常見檔案標頭；若你要更嚴謹，可將 ALLOW_ORIGIN 改為你的 Pages 正式網域。


## 改進內容（本分支）
- 新增後端路由 `/bin/<identifier>.zip` 實作「按需下載 + 伺服器快取 + SHA256 驗證」，前端仍以 `mountZip` 掛載。
- 加入 LRU 快取上限（預設 5 GiB，可用 `GAMES_CACHE_MAX_GB` 覆寫），自動清理最久未用 zip。
- 全站語系切換：以 cookie `lang`（`zh-Hans`/`zh-Hant`）控制，模板依 `lang` 動態顯示。
- 載入遊戲資料時，若缺少 `zh-Hant` 名稱，執行期後備使用 OpenCC `s2twp`（若無 OpenCC 則回退為 `zh-Hans`）。
- 提供 `static/games/convert_zh_hant.py`，一次性將 `games.json` 的缺漏繁體名稱以 `s2twp` 補齊並寫回。
- 在「關於」頁顯示快取使用量、上限與檔案數。
- 首頁 `<title>` 語系化。
- 管理頁：`/admin/missing`
  - 顯示：清單可切換「所有遊戲 / 壞掉 / 可玩」，每個項目尾註記 error/missing
  - 操作：重新掃描（背景）、快取用量顯示與一鍵清空、關鍵字與顯示筆數篩選、對壞掉項目一鍵「標記缺檔」（寫入 missing.json 的 manual）
- 啟動自動掃描：首次請求觸發背景掃描更新缺檔清單（相容 Flask 3：以 `before_request` + 旗標實作）。
- 主題切換：導覽列右上角圖示可在 light/dark 間切換（僅顯示圖示，設定保存在 theme cookie）。

## 與上游差異
- 不再要求啟動前先批次下載所有遊戲；改為按需下載、驗證並快取。
- 模板與搜尋支援 `zh-Hans`/`zh-Hant`/`en`。
- 新增管理頁（缺檔、壞掉、可玩分類、標記缺檔、Zip 診斷）。
- 新增主題切換（僅圖示）。

## 與上游比較（rwv vs anomixer）

| 項目 | 上游 rwv/chinese-dos-games-web | 本分支 anomixer/chinese-dos-games-web |
| --- | --- | --- |
| 遊戲取得方式 | 需先批次下載全部遊戲（1898套）才能啟動 | 按需下載：點進遊戲時才下載該 zip，並快取 |
| 快取機制 | 無（或使用者自行管理） | 伺服器快取 `static/games/bin`，並支援 LRU 上限（預設 5 GiB，可用 `GAMES_CACHE_MAX_GB` 覆寫） |
| 校驗與來源 | 使用固定來源 | 下載時校驗 SHA256；可切換 `REMOTE_PREFIX`，也可加上 Zip 診斷端點 |
| 解壓策略 | 可能需伺服器端處理 | 不解壓，前端以 Emularity `mountZip` 掛載（純 zip 流程） |
| 語系 | 以簡體為主 | 全站簡/繁切換（cookie `lang`），優先顯示 `zh-Hant`，搜尋支援 `zh-Hans/zh-Hant/en` |
| 繁體來源 | 無 | OpenCC `s2twp` 執行期補齊 + 一次性轉換腳本 `static/games/convert_zh_hant.py` |
| 管理頁 | 無 | `/admin/missing`：分類（所有/壞掉/可玩）、背景重新掃描、一鍵清空快取、關鍵字/筆數篩選、對壞掉項目一鍵「標記缺檔」（寫入 `missing.json` 的 `manual`） |
| Zip 診斷 | 無 | `/admin/zip/<id>/check`：回傳 exists/size/sha_match/zip_ok 等資訊 |
| 自動掃描 | 無 | 首次請求觸發背景掃描（Flask 3 相容實作） |
| 主題切換 | 無 | 導覽列圖示切換 light/dark（cookie `theme`） |
| 疑難排解 | 無 | 可選 `GAMES_SKIP_SHA=1` 協助診斷（僅測試用） |

> 提示：子專案 static/games（上游 chinese-dos-games）建議在你的 fork 維護；本分支會同時尊重掃描缺檔（`missing`）與人工標記（`manual`）。

## 鳴謝（Credits）
- [dreamlayers/em-dosbox: An Emscripten port of DOSBox](https://github.com/dreamlayers/em-dosbox)
- [db48x/emularity: easily embed emulators](https://github.com/db48x/emularity)


---

## 運行模式與環境變數

本分支支援三種 zip 取得模式，可用環境變數切換：

- stream_proxy（同源串流代理，推薦）
  - 說明：前端以同源 URL 請求 `/stream/<id>.zip`，後端即時串流遠端 zip，不落地存檔，避開遠端 CORS。
  - 設定：
    ```sh path=null start=null
    # PowerShell
    $env:USE_STREAM_PROXY = 1
    python app.py
    ```
  - 補充：可搭配 `STREAM_TIMEOUT_SECS`（預設 30）與 `STREAM_FALLBACK_TO_BIN`（預設 0）

- remote_mount（直接掛載遠端 URL）
  - 說明：前端直接請求 `REMOTE_PREFIX/<id>.zip`，無後端負擔，但需遠端提供 CORS。
  - 設定：
    ```sh path=null start=null
    # PowerShell
    $env:USE_REMOTE_MOUNT = 1
    python app.py
    ```

- cache_bin（按需下載 + 本機快取 + SHA 驗證）
  - 說明：伺服器於首次請求下載 zip 到 `static/games/bin`，並以 LRU 管理容量（`GAMES_CACHE_MAX_GB`）。
  - 設定：不設 `USE_STREAM_PROXY` / `USE_REMOTE_MOUNT` 即為此模式。

優先序：`USE_STREAM_PROXY=1` > `USE_REMOTE_MOUNT=1` > cache_bin

關聯環境變數一覽：
- `REMOTE_PREFIX`（預設 `https://dos-bin.zczc.cz/`）：遠端 zip 來源前綴
- `USE_STREAM_PROXY`（預設 0）：設定 1 => 啟用同源串流代理
- `USE_REMOTE_MOUNT`（預設 0）：設定 1 => 啟用直接掛載遠端 URL（需遠端 CORS）
- `DISABLE_BIN_ROUTE`（預設 0）：設定 1 => 停用 `/bin/<id>.zip` 路由（避免誤用本機快取）
- `STREAM_TIMEOUT_SECS`（預設 30）：串流代理逾時秒數
- `STREAM_FALLBACK_TO_BIN`（預設 0）：設定 1 => 串流代理失敗時回退 `/bin/<id>.zip`（需 `DISABLE_BIN_ROUTE=0`）
- `GAMES_CACHE_MAX_GB`（預設 5）：本機快取上限（GiB）

### 快速對照表（簡易）

| 模式 | 行為 | 需遠端 CORS | 伺服器負載 | 本機落地 | SHA 驗證 | 快速啟動 (PowerShell) |
| --- | --- | --- | --- | --- | --- | --- |
| stream_proxy | 同源 `/stream/<id>.zip` 串流代理 | 否 | 中等 | 否 | 否 | `$env:USE_STREAM_PROXY = 1` |
| remote_mount | 直接掛載 `REMOTE_PREFIX/<id>.zip` | 是 | 極低 | 否 | 否 | `$env:USE_REMOTE_MOUNT = 1` |
| cache_bin | `/bin/<id>.zip` 按需下載 + 本機快取 | 否 | 低-中 | 是 | 是 | `$env:USE_STREAM_PROXY=0; $env:USE_REMOTE_MOUNT=0; $env:DISABLE_BIN_ROUTE=0` |

小提醒：同時開啟時的優先序為 stream_proxy > remote_mount > cache_bin。

## 啟動範例（PowerShell）

- 串流代理、停用 /bin (完全網路下載，本機端都不存.zip)：
```powershell path=null start=null
$env:USE_STREAM_PROXY = 1
$env:DISABLE_BIN_ROUTE = 1
python app.py
```

- 串流代理 + 上游失敗回退 /bin（僅除錯用）：
```powershell path=null start=null
$env:USE_STREAM_PROXY = 1
$env:STREAM_FALLBACK_TO_BIN = 1
$env:DISABLE_BIN_ROUTE = 0
python app.py
```

- 直接掛載遠端（需 CORS，目前確定上游網站是可以的）：
```powershell path=null start=null
$env:USE_REMOTE_MOUNT = 1
python app.py
```


