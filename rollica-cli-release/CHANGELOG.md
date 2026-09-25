# rollica-cli-release CHANGELOG

## 2026-09-07 — initial-release

- 初始发布 Rollica 跨平台独立二进制打包发布技能
- 支持 darwin/arm64、darwin/amd64、linux/arm64、linux/amd64、windows/amd64 五大平台交叉编译
- 自动生成 SHA-256 校验清单 checksums.txt 与多系统自适应 install.sh
- 自动注入 update-source 标识并支持一键推送到个人 GitHub Releases (park0er/rollica-cli)
- 运行完毕自动输出即拷即用的本地安装/更新单行命令
