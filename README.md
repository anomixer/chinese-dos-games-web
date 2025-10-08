# chinese-dos-games-web
此專案可在瀏覽器中遊玩「中文 DOS 遊戲」，採用 Flask + Emularity（內含 DOSBox）實作。

本分支已改為「按需下載（On-Demand）+ 伺服器快取（LRU）+ mountZip」方案，支援簡/繁切換，可切換明亮或暗黑主題，並提供一次性繁體化腳本。

## 功能特點
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

## 部署建議（Render）
最小可行方案（不需改程式）：
- 新建 Web Service（Python）連結此 repo
- 加入 Persistent Disk，Mount Path 設為 `static/games/bin`（用來存放 zip 快取）
- 建置與啟動
  - Build command（可省略讓 Render 自動偵測）：
    ```sh
    pip install -r requirements.txt
    ```
  - Start command：
    ```sh
    gunicorn -b 0.0.0.0:$PORT app:app
    ```
- 設定環境變數（可選）：
  - `GAMES_CACHE_MAX_GB=10`（或你要的上限）
  - `REMOTE_PREFIX=https://dos-bin.zczc.cz/`（或你的鏡像）
- 部署後：
  - 首次進入某款遊戲會下載 zip 並寫入 Disk；之後命中快取
  - 管理頁 `/admin/missing` 可重新掃描、標記缺檔、清空快取
  - Zip 診斷 `/admin/zip/<identifier>/check` 檢查 zip_ok/sha_match 等

注意：Render 免費方案不支援 Persistent Disk。


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





