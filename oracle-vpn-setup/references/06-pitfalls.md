# 06 东京那次踩过的坑（按阶段）

每一条都是真实发生过的问题。新搭一台时逐条对照。

## 账号与开机
| 坑 | 表现 | 正确做法 |
|---|---|---|
| A1 额度被砍 | 按 4C/24G 抢一直 `LimitExceeded` | 先 `oci limits value list` 查额度，按上限抢 |
| 把网络超时当成抢到了 | 日志里出现 `RequestException`，用户以为抢到但失败了 | 这是本机网络超时，请求根本没发出去。完整 message 要写进日志，不要截断 |
| 信用卡又被验证一次 | 出现小额扣款后又撤销 | Oracle 周期性验卡，跟抢机无关 |
| 镜像选错架构 | A1 选了 x86 镜像，或 E2 选了 aarch64 镜像 | E2 用不带 aarch64 后缀的镜像 |
| 控制台错误提示残留 | 左下角还显示上一次的 "Out of capacity" | 以实际点 Create 后的结果为准 |
| 截图太大导致会话报错 | 模型报 "image dimensions exceed 2000 pixels" | 让用户直接复制文字（例如 API Key 的 config preview） |

## 网络
| 坑 | 表现 | 正确做法 |
|---|---|---|
| 创建时没分配公网 IP | 实例 Public IP 显示 "-" | 按 02 补 Reserved IP |
| 只开了 Security List | 端口还是不通 | iptables 也要放行 |
| 端口乱开 | 443、2096 之外又临时开了 8443 | 只开 22、443、2096，面板端口永远不对公网开放 |
| 换 IP 后订阅失效 | 客户端刷新订阅拉不到 | 刷新只会访问旧地址；新 IP 要改 `share_addr`、`subURI`、`subClashURI`，客户端要**改订阅 URL** |
| 用 CLI 改 Security List 覆盖了原规则 | 22 端口规则被删掉 | `update` 是整表覆盖，先读出原规则再合并 |

## 3x-ui
| 坑 | 表现 | 正确做法 |
|---|---|---|
| 远程执行 `bash <(curl ...)` | 远程 SSH 下执行失败 | 先下载成文件，再用环境变量非交互安装 |
| API 返回 403 | 请求缺少 CSRF token | 登录后重新 GET `/panel/` 拿新 token；非批量操作就用面板手动做 |
| 复制的链接缺少路径 | `http://IP:2096parko` | `subURI` 要写完整路径 `http://IP:2096/parko-sub/` |
| 链接里是 localhost | 分享出去别人连不上 | inbound 的 `share_addr` 设为公网 IP，strategy 设为 custom |
| 以为 3x-ui 不支持 Clash | 导入时报 invalid yaml | 打开 `subClashEnable`，使用 Clash 路径 |
| 替换 db 后改动失效 | 旧配置又回来了 | 先删掉 `x-ui.db-wal` 和 `x-ui.db-shm` |
| 密码输错一位 | 改完登录不上 | 改之前请用户确认两遍 |

## REALITY 与客户端
| 坑 | 表现 | 正确做法 |
|---|---|---|
| **服务端 SNI 改了一半** | Clash 订阅能用，Shadowrocket 连不上 | 服务端和客户端 SNI 必须一致；工具调用被打断后，要检查服务端**实际**是什么状态 |
| 误以为传输方式 `none` 有问题 | Shadowrocket 显示「传输方式 none」 | 在 Shadowrocket 里 none 就是 TCP，不用改 |
| 怀疑 `xtls-rprx-vision` | 速度慢时怀疑 flow 设置 | Vision 是推荐配置，跟速度无关 |
| Clash profile 没生效 | 导入后看不到节点 | 要把这个 profile 设为当前使用，mode 切到 Rule |
| Shadowrocket 读不了规则 | 用 Clash 订阅也不行 | 手动导入 `.conf` |

## 速度与连通
| 坑 | 表现 | 根因 | 做法 |
|---|---|---|---|
| **下载 1 Mbps、上传 30 Mbps** | 同一 WiFi 下，哥哥的节点正常 | cubic 在丢包线路上大幅降速 | 开 BBR（bootstrap 已包含） |
| **WiFi 能连、5G 连不上** | 只有蜂窝网络连不上 | MTU 9000 加上 PMTUD 被屏蔽 | MSS clamp 1360（bootstrap 已包含） |
| 先怪运营商、IP 段或机型 | 排查绕了很大一圈 | 同 WiFi、同机型下对比，唯一的变量在服务器 | 先查 BBR 和 MSS，再考虑换 IP |
| 换 IP 试图解决慢的问题 | 换了之后还是慢 | 慢的原因是 cubic | 同上 |
| 链式代理出口的上行成为瓶颈 | 下载 8 Mbps、上传 17 Mbps | 美国家宽出口的上行慢 | 先关掉链式出口直连测一次 |

## 运维与协作
| 坑 | 正确做法 |
|---|---|
| 文件都放在 `~/Downloads` | 项目文件放到 `~/coding/Foundations/AgentSetups/oracle-vpn/`（美国机器可以用 `oracle-vpn/us/` 子目录） |
| `tail -f` 看起来像卡住 | 它本来就会一直等待新内容；给用户一个汇总状态的脚本 |
| Multica 建错了 profile | 默认 profile、workspace、agent 以全局 agent rules 为准 |
| 说了「记住了」但没有持久化 | 用户的偏好写进 agent rules 或 memory，不要只说「记住了」 |
| 服务正在使用时做测试 | 只做只读检查；不重启 xray、不跑占满带宽的测速，除非用户同意 |
