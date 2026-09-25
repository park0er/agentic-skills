# rollica-tokyo-ship CHANGELOG

## 2026-09-25 — desktop-asar-unpack-gate

- 东京 Desktop 上传前必须有可执行的 `app.asar.unpacked/resources/bin/multica`，zip 清单里也要有
- 写明 `-c overlay` 会替换 `electron-builder.yml`，overlay 必须 `extends: electron-builder.yml`
- Desktop 版本号跟 tag 走，不另起版本

## 2026-09-25 — initial-tokyo-ship

- initial release
- 把「A1 前后端部署 + GitHub CLI 五平台 + 东京 Apple Silicon Desktop」收成一次发版流程
- 固定：保留 .env/Postgres、GOPROXY 走 proxy.golang.org、Caddy `/health` 必须打到 backend、`tokyo-desktop` 不得抢 Latest
