# oracle-vpn-setup CHANGELOG

## 2026-09-27 — initial-release

- 初版：把 2026-07 到 08 东京 Oracle VPN 从 0 到 1 的实际搭建整理成不绑定区域的流程，目标是下一台美国机器。
- 内容：Home Region 与账号约束（美国机器必须新注册账号或付费）、机型选择与额度查询、网络和两层防火墙、3x-ui 非交互安装、REALITY 与订阅数据库字段、分流规则、防闲置回收、验收清单、按阶段整理的踩坑清单。
- 脚本：collect-ocids.sh（已在东京 DEFAULT profile 实测）、oracle-grab.sh（由实测版参数化而来）、server-bootstrap.sh、install-3xui.sh、verify-server.sh（已在东京 A1 只读实测全部通过）、anti-reclaim（取自 A1 线上版本，新增内存参数传 0 表示只压 CPU）。
- 已知情况：server-bootstrap.sh 和 install-3xui.sh 还没在全新机器上完整跑过，第一次在美国机器上使用时要逐步核对输出。
