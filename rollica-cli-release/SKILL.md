---
name: rollica-cli-release
description: 一键构建、打包、校验并发布 Rollica 跨平台独立的 CLI / Daemon 二进制（及可选东京 Desktop App）到个人 GitHub 仓库（park0er/rollica-cli）。覆盖 darwin/arm64、darwin/amd64、linux/arm64、linux/amd64、windows/amd64。自动生成含 SHA-256 签名的 checksums.txt 与自适应安装脚本 install.sh，注入 update-source 标识，并直接在终端输出即拷即用的单行更新安装命令。触发词：发布rollica cli、打包二进制、更新私服二进制、rollica cli release、发布到github、个人二进制发版、publish rollica cli、编译多平台multica。
---

# Rollica CLI 个人发版技能 (rollica-cli-release)

用于为赵锡盛个人开发环境与东京私服基础设施一站式构建、打包、校验并发布跨平台的 `multica` CLI / Daemon 二进制到个人 GitHub 仓库（`park0er/rollica-cli`）。

## 核心职责

1. **多平台矩阵编译**：自动交叉编译 5 大操作系统与 CPU 架构：
   - Apple Silicon Mac (`darwin/arm64`)
   - Intel Mac (`darwin/amd64`)
   - 64 位 Linux (`linux/amd64`)
   - ARM64 Linux (`linux/arm64`，适配 Oracle Cloud A1 东京云主机)
   - Windows 64 位 (`windows/amd64`)
2. **制品规范打包与校验**：
   - 生成 `multica-cli-<version>-<os>-<arch>.tar.gz`（Windows 为 `.zip`）
   - 计算所有压缩包的 SHA-256 哈希并写入 `checksums.txt`
3. **自适应安装脚本更新**：
   - 同步打包 `install.sh`，运行时自动检测客户端 `uname -s` 与 `uname -m`
   - 在安装时自动在 `~/.rollica-cli/update-source` 写入更新源标识 `park0er/rollica-cli`，并提示持久化环境变量 `export ROLLICA_UPDATE_REPO="park0er/rollica-cli"`
4. **自动化 GitHub 发布**：
   - 使用 `gh release create` / `gh release upload` 推送至 `park0er/rollica-cli`
5. **即拷即用命令回显**：
   - 执行完成后，必须在回复末尾显式输出单行安装命令，方便用户在本地或私服直接粘贴回车。

## 使用流程与操作指南

### 1. 执行打包发布脚本

在 Rollica 仓库根目录下执行技能内置脚本：

```bash
# 仅本地编译打包并预览产物（不上传）
~/.agents/skills/rollica-cli-release/scripts/package-cli.sh <version>

# 编译打包并一键发布至 GitHub Releases
~/.agents/skills/rollica-cli-release/scripts/package-cli.sh <version> --upload
```

参数说明：
- `<version>`：发版版本号，如 `v0.0.7` 或 `0.0.7`。
- `--upload`：打包校验通过后，自动调用 GitHub CLI（`gh`）推送到 `park0er/rollica-cli`。
- `--repo`：指定 GitHub 仓库，默认 `park0er/rollica-cli`。
- `--repo-dir`：指定 Rollica 本地代码仓库目录，默认当前目录。

### 2. 回复与交付要求

每次完成发布后，**必须在回复末尾提供即拷即用的单行命令**，格式如下：

```bash
# 本地 Mac / Linux 一行安装更新
curl -fsSL https://github.com/park0er/rollica-cli/releases/download/<version>/install.sh | bash
```

同时提示用户验证版本：
```bash
multica --version
```
