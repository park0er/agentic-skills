# precise-doc-download CHANGELOG

## 2026-06-29 — whiteboard-fusion-all-modes

- 白板 fusion 不再限单文档：`export_materials.py` 改为对 `out-dir` 下**所有** `.md`（递归，排除 Export_Audit_Report）跑 fusion，folder / wiki 模式同样自动补白板。因为占位符自带 token，每个 `.md` 自描述，批量无需额外参数。

## 2026-06-29 — whiteboard-fusion-via-feishu-cli

- 新增 `scripts/fuse_whiteboards.py`：feishu2md 自带的画板导出会报 `99991672` scope 错并丢弃白板，故改为用原生 `feishu` CLI 渲染白板。
- `feishu-docx/core/parsers/document.py` 打补丁：`--keep-whiteboard-empty` 占位符现在内嵌画板 token（`【白板 序号N】<!--wb:TOKEN-->`），fusion 按 token 匹配，避免顺序错位（含 grid 内嵌白板）。
- `export_materials.py`：单文档模式自动跑白板 fusion（`--keep-whiteboard-empty` 自动开启），新增 `--skip-whiteboard-fusion`、`--feishu-bin`。folder/wiki 模式提示按文档单独跑。
- `references/toolchain.md`：更新依赖（lark-oapi/pydantic/httpx/mistune），记录 `.venv_export`，记录 passport reauth 流程（勿换 v2）。
- 已在「Agent阶段性总结和后续规划汇报」实测：6/6 白板按 token 渲染并替换占位符，无残留 marker。

## 2026-06-17 — precise-doc-download-rename

- 将 skill 名称调整为 `precise-doc-download`，更贴近“文档精细化下载”的语义。
- 继续保持手动触发策略：仅在显式 `/precise-doc-download` 或 `$precise-doc-download` 调用时使用。
- 清理 Python `__pycache__`，避免发布派生产物。

## 2026-06-17 — rename-manual-only-trigger

- 将 skill 从 `feishu-materials` 重命名为 `precise-doc-download`，语义改为“文档精细化下载”。
- 收紧 `description`：必须显式 `/precise-doc-download` 或 `$precise-doc-download` 调用，禁止默认触发，避免和真实 Feishu skill 冲突。
- 将 UI 元数据设置为非隐式调用。

## 2026-06-17 — initial-feishu2md-wrapper

- 新增 `feishu-materials` skill，固化项目取飞书材料时优先使用本地 `feishu2md` 工具链的规则。
- 提供安全包装脚本，复用外部工具目录但不复制 token、app secret 或生成物。
- 增加画板/白板检测与原生 Feishu 导出兜底说明。
