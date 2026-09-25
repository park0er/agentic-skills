# TODO — icloud-materialization-doctor

## 状态

- v1 (download-side dataless detection) — **已完整恢复**。`scripts/icloud_materialization_doctor.py`
  里的 `check` / `fix` 子命令是工作版本。
- v2 (upload-side diagnostics + dry-run housekeeping) — **2026-05-14 添加**。
  新增 `upload-check` / `housekeeping-suggest`；SKILL.md 加了 multi-machine pitfall +
  correlation-not-causation 章节，明确不再宣称"做了 X 就修好"的因果。

## 历史背景（保留作教训）

2026-05-13 晚发生过一次本 skill 的 Python 脚本因 iCloud + git corruption 丢失的事件
（详见 `../agent-sync-doctor/ISSUES-2026-05-13-codex-data-loss.md` 如果它存在）。
当时一度只剩 SKILL.md。后续从其他 Mac / iCloud Recently Deleted 等位置恢复了脚本。
**这就是为什么 Factory 现在不放在 git 里、靠 `archives/` 快照做版本管理**（FACTORY.md
有详细说明）。

## v2 后的潜在改进（非紧急）

### 上传侧

- [ ] `upload-check` 增加"识别 stuck 持续时间"维度。当前我们能看到 `last:11.67h ago`
  这种字段但没有解析出来；如果把"卡了多久"的分布算出来（最久的、中位、>1h 的数量），
  分诊会更精准。
- [ ] `upload-check --json` 里给每个 brctl pending 项的 size + path 解析出来，让
  agent-sync-doctor 能拿来直接 cross-reference。当前只给了汇总计数。
- [ ] 给 `housekeeping-suggest` 加 `--include-old-sessions=Nd` 选项，用户显式
  opt-in 才会把 N 天以上的 Codex sessions JSONL / Claude project history 列进
  removal candidates。**默认仍然不动**这些（用户对话历史不可重建）。
- [ ] `--apply` 的 build artifact 清单里如果包含父目录是 plugin cache 的（如
  `~/.claude/plugins/cache/...`），输出"已知会被插件重新装回来"提示 —— 不阻止删除，
  但让用户知道清理可能不持久。

### Multi-machine handling

- [ ] 给 `upload-check` 增加 `--remote <hostname>` 模式：跨 ssh 在另一台 Mac 上
  跑诊断、把 JSON 输出拿回来本地展示。这样可以在 follower 机器上一眼看 originator
  的 pending 队列。
- [ ] 与 agent-sync-doctor 配合：在 `arrive` / `handoff` 流程里自动跑 upload-check，
  如果发现 originator 那边有未推上去的内容就 abort handoff。

### Sandbox / 平台

- [ ] 探索 macOS 26 Endpoint Security 是否有 entitlement 能让 sandboxed 进程
  跑 `brctl status`。当前的"hang past 15s"降级路径没问题，但能拿到一手数据更好。
- [ ] 加一条 evals 测试：模拟 brctl unavailable / brctl hang / brctl 正常返回
  三个场景的 stub 输出，验证 upload-check 三种降级都正确。

## 调用契约（agent-sync-doctor 依赖）

agent-sync-doctor 的 `icloud_materialization_report()` 调用形如：

```python
subprocess.run(
    ["python3", str(script), "check", "--json", "--paths", str(icloud_root)],
    capture_output=True, text=True, timeout=60,
)
```

返回 schemaVersion=1 的 JSON：
- 顶层 `summary.datalessCount` / `summary.ready`
- `paths[].dataless_samples[]`

v2 新增的 `upload-check --json` 输出**与 download-side schema 不冲突**（两者
都是 schemaVersion=1，但 `subcommand` 字段区分）。当前 agent-sync-doctor 不依赖
upload-check —— 如果将来要加，看 SKILL.md 里 *JSON 输出 schema* 节。
