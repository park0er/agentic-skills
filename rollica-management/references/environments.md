# 环境选择：正式 vs 东京私服

包装器一次只连一朵云。默认 **production**。东京必须显式选中，或由 PKO/东京线索推断。

永远不要用 `/Applications/Rollica.app` 里的公司 CLI 打东京服。

## 怎么选

```bash
python3 "<skill-dir>/scripts/rollica_management.py" --env production doctor
python3 "<skill-dir>/scripts/rollica_management.py" --env tokyo doctor
```

也可设 `ROLLICA_ENV=tokyo`。推断规则（`--env` 优先）：

| 线索 | 环境 |
|---|---|
| `--env tokyo` / `ROLLICA_ENV=tokyo` | tokyo |
| `--workspace pko`、`tokyo`、`东京`、`东京服` | tokyo |
| Issue 前缀 `PKO-3` | tokyo |
| `--workspace parko`、`miads`、`正式`、`公司` | production |
| `MIA-220` 或无线索 | production |

`Parko`（公司 slug `parko`）和 `Pko`（东京 slug `pko`）不是同一个工作区。查公司 Parko 用 `--env production --workspace parko`；查东京 Pko 用 `--env tokyo` 或 `--workspace pko`。

## 东京两种安装形态

脚本按这个顺序找 CLI，**不会**退回公司 Rollica.app：

1. `ROLLICA_CLI_PATH` 覆盖
2. Tokyo Desktop 内置 CLI：  
   `/Applications/Rollica Tokyo.app/Contents/Resources/app.asar.unpacked/resources/bin/multica`
3. 独立二进制：`~/.rollica-cli/bin/multica`

Profile（必须是 `mul_` PAT，且 `server_url` 指向东京机）按这个顺序找：

1. `ROLLICA_CONFIG_HOME` + `ROLLICA_PROFILE`
2. `~/.rollica-tokyo/profiles/*`（Tokyo Desktop 登录目录）
3. `~/.multica/profiles/*` 里 `server_url` 命中东京主机的项，优先名为 `a1`

东京主机标记默认包含 `141.147.189.28` 和内网 `10.0.0.244`。换 IP 时设 `ROLLICA_TOKYO_SERVER=<host>`。

`doctor` 的 `install_shape`：

- `tokyo-desktop` / `tokyo-desktop+cli`：装了 Tokyo.app 且能找到内置 CLI
- `cli-only`：只有 `~/.rollica-cli/bin/multica`
- `cli-only (Tokyo.app present but bundled CLI missing)`：App 在，但 asar 未解开 CLI，已改走独立二进制

## CLI-only 最小登录

```bash
~/.rollica-cli/bin/multica setup self-host \
  --server-url http://141.147.189.28 \
  --app-url http://141.147.189.28
~/.rollica-cli/bin/multica --profile a1 login --token mul_...
```

配置落在 `~/.multica/profiles/a1/config.json`。包装器发现这个 profile 即可，不必再装 Desktop。

## Tokyo Desktop 最小登录

安装 `/Applications/Rollica Tokyo.app`，打开并登录。配置预期在 `~/.rollica-tokyo/profiles/desktop-<host>/config.json`。内置 CLI 解开后优先用它；若 App 存在但 CLI 未解开，仍可用 `~/.rollica-cli` + 已有东京 profile。

## 覆盖变量

| 变量 | 作用 |
|---|---|
| `ROLLICA_ENV` | `production` 或 `tokyo` |
| `ROLLICA_CLI_PATH` | 强制 CLI 路径 |
| `ROLLICA_CONFIG_HOME` / `ROLLICA_PROFILE` | 强制配置目录和 profile 名 |
| `ROLLICA_TOKYO_SERVER` | 额外的东京主机标记 |

覆盖时仍要求 token 是 `mul_`，东京环境还要求 `server_url` 像东京私服。
