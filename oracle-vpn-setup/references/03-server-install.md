# 03 服务器初始化、3x-ui、REALITY、订阅

以下变量在后文中通用，agent 先填好再给用户：
```bash
KEY="<SSH 私钥绝对路径>"        # 路径含空格，务必加引号
IP="<Reserved 公网 IP>"
chmod 600 "$KEY"
ssh -i "$KEY" ubuntu@"$IP"
```

多台电脑都可以用同一把 key 同时连（iCloud 会同步 key 文件）。SSH 只在管理时需要，日常翻墙走 443，跟 SSH 无关。

## 1. 初始化与调优（一次到位）

```bash
scp -i "$KEY" scripts/server-bootstrap.sh scripts/verify-server.sh ubuntu@"$IP":~
ssh -i "$KEY" ubuntu@"$IP" 'sudo bash ~/server-bootstrap.sh'
```

脚本做的事（重复执行不会出问题）：
1. iptables 放行 443/tcp、443/udp、2096/tcp（插到 REJECT 规则之前），并持久化保存
2. **BBR + fq**：跨境线路丢包多，默认的 cubic 会把丢包误判成拥塞而大幅降速，表现为**下载远低于上传**。东京那次开 BBR 前下载 1 Mbps，开之后 42 Mbps
3. TCP 缓冲区调到 16 MB，开启 mtu_probing 和 fastopen：线路延迟越高（美国比东京高得多），需要的缓冲区越大
4. **MSS clamp 1360**：蜂窝网络 MTU 小，又常屏蔽 ICMP，大包会被静默丢弃，表现为 **WiFi 能连、5G 连不上**。脚本会自动识别主网卡名（x86 上是 `ens3`，ARM 上是 `enp0s6`），不要写死
5. 2 GB swap，swappiness 10：1 GB 内存的机器防 OOM
6. x-ui 的 `LimitNOFILE=1048576`：默认 1024 个文件描述符，并发连接一多就不够用（x-ui 还没安装时会先写好，等安装后生效）

原理的详细讲解见 `oracle-vpn-ops` 的 performance-tuning.md，以及 protofly 上的 BBR 讲解页。

## 2. 安装 3x-ui（非交互）

安装脚本支持环境变量方式非交互安装（`XUI_NONINTERACTIVE=1`，或者 stdin 不是 TTY 时自动进入非交互模式）。`scripts/install-3xui.sh` 对这个过程做了封装：

```bash
scp -i "$KEY" scripts/install-3xui.sh ubuntu@"$IP":~
# 密码通过 read -s 在服务器上输入，不经过命令行参数，也不写进 shell 历史
ssh -t -i "$KEY" ubuntu@"$IP" \
  'sudo XUI_USERNAME=park0er XUI_PANEL_PORT=2053 XUI_WEB_BASE_PATH=/parko-3xui-dashboard/ bash ~/install-3xui.sh'
```

注意：
- 远程执行时 `bash <(curl ...)` 这种 process substitution 会失败，要先下载成文件再执行（脚本已经这样处理）。
- 装完用 `sudo /usr/local/x-ui/x-ui setting -show true` 核对。
- 改用户名或密码：`sudo /usr/local/x-ui/x-ui setting -username U -password P && sudo systemctl restart x-ui`。**改完请用户重复确认一次密码**，东京那次就因为密码少打一位返工过。

## 3. 访问面板（只走 SSH 隧道）

```bash
ssh -L 2053:localhost:2053 -i "$KEY" ubuntu@"$IP"     # 窗口保持打开，Ctrl+C 关闭
# 浏览器打开 http://localhost:2053/parko-3xui-dashboard/
```

本机 2053 端口被占用时才会冲突；本机其他 localhost 服务不受影响。多台电脑可以同时开隧道。

## 4. 创建 VLESS + REALITY 入站

**推荐在面板里点选**，稳定可靠：Inbounds → Add Inbound：

| 字段 | 值 |
|---|---|
| Protocol | vless |
| Port | 443 |
| Transmission | TCP |
| Security | Reality |
| uTLS / Fingerprint | chrome |
| Dest / Target | `<SNI>:443` |
| SNI (serverNames) | `<SNI>` |
| Keys | 点 Get New Cert 自动生成，或在服务器上执行 `xray x25519` |
| Short IDs | 16 位 hex 最稳妥（`openssl rand -hex 8`） |
| Client flow | `xtls-rprx-vision` |
| Client email / subId | 按用户的个性化设置（email 用来区分用户和设备） |

**SNI 怎么选**：
- 选支持 TLS 1.3 + H2 的大站。可以在服务器上执行 `/usr/local/x-ui/bin/xray-linux-* tls ping <域名>` 验证。
- 新版 Xray 对 `apple.com`、`icloud.com` 会打一条 WARNING，提示这类域名可能增加被封风险。东京那次继续用 apple.com，实测没问题。美国机器可以考虑换一个本地大站。
- **最关键的一点：服务端的 dest/serverNames 必须和客户端的 SNI 完全一致。** 改服务端之后，所有静态导入的客户端（二维码、vless:// 链接、`.conf` 文件）都要重新导入。东京那次就是服务端改了一半没有同步，导致 Shadowrocket 连不上。

也可以用 API 自动创建（需要先带 CSRF token 登录：GET 登录页拿 `csrf-token` meta → POST `/login` 并带 `X-CSRF-Token` 头 → 登录后**再 GET 一次 `/panel/`** 拿新 token → POST `/panel/api/inbounds/add`）。东京那次在这个流程上多次遇到 403，**除非要批量操作，否则用面板手动创建**。

## 5. 订阅

3x-ui 自带订阅服务，默认端口 2096。数据库 `settings` 表里的相关 key（以 3.4.2 / 3.7.0 实测为准）：

| key | 值（示例） | 说明 |
|---|---|---|
| `subEnable` | `true` | base64 订阅开关 |
| `subPort` | `2096` | |
| `subPath` | `/parko-sub/` | 前后都要有 `/` |
| `subURI` | `http://<IP>:2096/parko-sub/` | **必须带完整路径**，只写 `http://IP:2096` 的话，面板复制出来的链接会变成 `http://IP:2096parko` |
| `subClashEnable` | `true` | **默认关闭**，不开就没有 Clash 订阅 |
| `subClashPath` | `/parko-clash/` | |
| `subClashURI` | `http://<IP>:2096/parko-clash/` | |
| `subClashEnableRouting` | `true` | 允许在订阅里内置规则 |
| `subClashRules` | 规则文本 | 见 04 |

`inbounds` 表：`share_addr` 设为公网 IP，`share_addr_strategy` 设为 `custom`。不设的话，订阅和分享链接里的地址会是 `localhost`。

这些设置可以在面板的 Settings → Subscription 里改，也可以直接改数据库（先 `cp /etc/x-ui/x-ui.db{,.bak.$(date +%s)}` 备份，用 python sqlite3 修改，然后 `systemctl restart x-ui`）。**如果是停服务后替换整个 db 文件，要先删掉 `x-ui.db-wal` 和 `x-ui.db-shm`**，否则 SQLite 会重放 WAL，把旧配置写回去。

验证（在用户的 Mac 上执行，走公网访问）：
```bash
curl -s -o /dev/null -w '%{http_code}\n' "http://$IP:2096/parko-clash/parko"   # 应返回 200
curl -s "http://$IP:2096/parko-clash/parko" | grep -E 'rules:|MATCH'
```

## 6. 从已有机器迁移（复刻东京配置）

想让新机器和东京用**同一套 UUID 和 REALITY 密钥**时（用户切换机器只需要换 IP）：把旧机器的 `/etc/x-ui/x-ui.db` 拷过来，替换后改 `share_addr`、`subURI`、`subClashURI` 为新 IP。按上面说的先删 wal/shm。

想让新机器独立时（推荐美国机器这样做，两台机器互不影响）：重新生成密钥和 UUID，只照搬规则文本和订阅路径风格。
