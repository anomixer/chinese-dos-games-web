# Cloudflare Workers 部署說明（/stream 代理）

本工程提供一個 Workers 專案，用於代理 `/stream/<id>.zip` 到遠端 `REMOTE_PREFIX/<id>.zip`，以同源方式提供 zip，避免瀏覽器的 CORS 限制。

## 結構
- wrangler.toml：Workers 專案設定（可在此設定 `vars`）
- src/worker.js：Workers 程式，處理 `/stream/` 串流與（可選）其他路徑反向代理

## 先決條件
- 安裝 Wrangler
  ```sh
  npm i -g wrangler
  # 或使用 npx wrangler ...
  ```
- 登入 Cloudflare
  ```sh
  wrangler login
  ```

## 本機開發
```sh
# 於 cloudflare-workers 目錄下
wrangler dev
```

## 設定遠端來源
- wrangler.toml 預設：
  ```toml
  [vars]
  REMOTE_PREFIX = "https://dos-bin.zczc.cz/"
  ```
- 你也可以用 CLI 覆寫：
  ```sh
  wrangler kv:namespace list   # 如需
  wrangler deploy --var REMOTE_PREFIX="https://your-mirror.example/"
  ```

## 部署
```sh
wrangler deploy
```

## 綁定網域與路由（可選）
若你的站台已在 Cloudflare DNS 之下，建議使用路由把 `/stream/*` 交給 Workers：
1. 取得 zone_id（可在 Cloudflare 後台查詢）。
2. 編輯 wrangler.toml，取消註解 routes 並填入：
   ```toml
   [routes]
   zone_id = "<your_zone_id>"
   pattern = "example.com/stream/*"
   ```
3. 重新 deploy。

這樣一來：
- 同一個網域下，`/stream/<id>.zip` 將由 Workers 直接代理遠端 zip（同源，無 CORS）。
- 其他路徑仍由你的原站處理（你可以在 `vars.ORIGIN` 設定原站，例如 `https://your-flask-origin.example.com`，Workers 會將非 `/stream` 路徑反向代理到 ORIGIN）。

## 與 Flask 的搭配
- 你可以保留 Flask 站台，並把整個站台放在 Cloudflare 後面，配置路由只攔截 `/stream/*` 給 Workers。
- Flask 端維持目前的 `zip_url`（預設會指向同源 `/stream/<id>.zip` 若你啟用 USE_STREAM_PROXY），即可無縫工作。

## 注意事項
- 本實作會傳遞 Range 與常見的檔案標頭（Content-Length/Content-Range/Accept-Ranges/Last-Modified/ETag/Cache-Control/Content-Type）。
- 若上游無 Content-Length，瀏覽器仍可串流播放，但可能影響下載進度條行為。
- 若你使用 workers.dev 測試域名，前端從 Flask 網域呼叫 workers.dev 仍會有 CORS；建議用「路由到你的正式網域」的方式部署，確保同源。
