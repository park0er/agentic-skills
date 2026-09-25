# 路由分流规则（Routing Rules）

让 VPN 做智能分流：**国内网站/内网直连、海外走代理、广告拦截**。核心目标：规则简单稳定、不依赖外部 RULE-SET URL（照搬奈云的 hardcoded keyword 模式）。

## 关键认知：三种订阅格式能否自带规则

这是最容易踩坑的地方。3x-ui 能出两种订阅，客户端支持三种格式，**能否携带路由规则取决于格式**：

| 格式 | 3x-ui 端点 | 带节点 | 带规则 | 谁用 |
|---|---|---|---|---|
| **base64**（`vless://` 列表） | `/parko-sub/<subId>` | ✅ | ❌ 格式上没有放规则的地方 | Shadowrocket / v2rayN / NekoBox |
| **Clash YAML** | `/parko-clash/<subId>` | ✅ | ✅ `rules:` 段 | Clash Verge / Mihomo / Stash |
| **Shadowrocket .conf**（`[Rule]`） | 需手工生成 | ✅ | ✅ | Shadowrocket |

> **商业机场"自动配好 Shadowrocket"的原理**：同一订阅 URL 检测客户端 User-Agent，是 Shadowrocket 就返回 .conf 格式，是 Clash 就返回 Clash YAML。3x-ui **没有**这个 UA 识别 + SR 格式生成能力，只出 base64 和 Clash 两种。

**结论**：
- Clash Verge → 直接拉 `/parko-clash/` 就自带规则（服务器已烤，见下）。
- Shadowrocket → 走 base64 拿不到规则；要么用 Clash URL（部分版本支持），要么手工导入 `.conf`（见"Shadowrocket 方案"）。

## 方案 A：服务器端烤规则（推荐，一处维护，全客户端生效）

3x-ui v3.4.2 原生支持把规则烤进 Clash 订阅。前端在 Settings → 订阅 → "Clash / Mihomo" 标签页，对应两个 DB 设置项：

| 设置 key | 作用 |
|---|---|
| `subClashEnableRouting` | 开关：是否在生成的 Clash YAML 里注入全局路由规则 |
| `subClashRules` | 规则文本：加在每个 Clash 订阅的 `MATCH,PROXY` **之前**（换行分隔，每行一条） |

规则里的代理策略名 = Clash 订阅里的 proxy-group 名，本机是 **`PROXY`**。3x-ui 会自动在末尾补 `MATCH,PROXY` 作兜底，所以 `subClashRules` 以 `GEOIP,CN,DIRECT` 结尾即可。

### 写入方法（Python，避免 shell 转义）

```bash
ssh -i "$SSH_KEY" ubuntu@<IP> "sudo cp /etc/x-ui/x-ui.db /etc/x-ui/x-ui.db.bak.\$(date +%s)"
ssh -i "$SSH_KEY" ubuntu@<IP> 'sudo python3 << "PYEOF"
import sqlite3
rules = """DOMAIN-KEYWORD,admarvel,REJECT
... (完整规则见本文件末尾"标准规则集") ...
GEOIP,CN,DIRECT"""
conn = sqlite3.connect("/etc/x-ui/x-ui.db"); c = conn.cursor()
c.execute("UPDATE settings SET value=? WHERE key=\x27subClashRules\x27", (rules,))
c.execute("SELECT COUNT(*) FROM settings WHERE key=\x27subClashEnableRouting\x27")
if c.fetchone()[0]==0:
    c.execute("INSERT INTO settings (key,value) VALUES (\x27subClashEnableRouting\x27,\x27true\x27)")
else:
    c.execute("UPDATE settings SET value=\x27true\x27 WHERE key=\x27subClashEnableRouting\x27")
conn.commit(); conn.close(); print("done")
PYEOF'
ssh -i "$SSH_KEY" ubuntu@<IP> "sudo systemctl restart x-ui"
```

### 验证

```bash
curl -s "http://<IP>:2096/parko-clash/parko" | grep -c "DIRECT\|PROXY\|REJECT"   # 应 >100
curl -s "http://<IP>:2096/parko-clash/parko" | tail -3   # 结尾应是 GEOIP,CN,DIRECT 然后 MATCH,PROXY
```

## 方案 B：Clash Verge 本地覆盖（个人额外层，可选）

Clash Verge 的每个 profile 可挂一个 "rules override" 文件（`prepend`/`append`/`delete`）。位置：
```
~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/profiles/<rulesUID>.yaml
```
profile 的 `option.rules` 字段指向该文件。格式：
```yaml
prepend:
  - 'DOMAIN-SUFFIX,xiaomi.com,DIRECT'
  - ...
  - 'GEOIP,CN,DIRECT'
append: []
delete: []
```
`prepend` 的规则在订阅自带规则**之前**评估。

> **注意冗余**：若已用方案 A 服务器烤规则，Clash Verge 拉下来就自带规则，本地覆盖会重复（无害但不干净）。二选一，推荐只用方案 A。改完需在 Clash Verge 里重新载入 profile 才生效。

## 方案 C：Shadowrocket .conf（手工导入）

base64 订阅带不了规则。给 Shadowrocket 用户一份 `.conf` 手工导入（AirDrop → Shadowrocket 打开）。模板见 `scripts/parko-shadowrocket.conf`。要点：

- `[Proxy]` 定义 VLESS+REALITY 节点：`名称 = vless, IP, 443, username=UUID, tls=1, flow=xtls-rprx-vision, sni=..., fingerprint=chrome, public-key=..., short-id=..., peer=...`
- **Shadowrocket 内置策略 `PROXY`**（= 当前选中节点）、`DIRECT`、`REJECT`——规则用这些内置名**不绑定具体节点**，所以即使 `[Proxy]` 那行解析失败连不上，用户保留现有能连的节点、规则照样生效。
- `[Rule]` 段规则同标准集，末尾 `GEOIP,CN,DIRECT` + `FINAL,PROXY`。
- REALITY 参数名各 Shadowrocket 版本略有差异（`public-key`/`pbk`、`short-id`/`sid`）；连不上就让用户保留已有节点，只取规则。

## 标准规则集（照搬奈云 hardcoded 模式）

结构（顺序即优先级）：
1. **去广告 REJECT** — admarvel/admaster/adsage/.../doubleclick.net/mmstat.com 等
2. **小米内网/公司 DIRECT** — mioffice.cn, xiaomi.com/.srv/.net, mi.com, olap.srv, mi-dun.com, mitvos.com, multica.ai, typeless-static.com
3. **本地/私有 IP DIRECT** — 10/8, 172.16/12, 192.168/16, 127/8, 100.64/10, 17/8(Apple), 198.18/16, 224/4, IPv6 私有段
4. **Apple/iCloud DIRECT** — apple.com, apple-cloudkit.com, icloud.com, icloud-content.com, mzstatic.com, aaplimg.com, cdn-apple.com, akadns.net
5. **国内大厂 keyword DIRECT** — baidu/alibaba/alicdn/alipay/taobao/tencent/bilibili/weibo/douyin/bytedance/xiaomi/huawei/netease/meituan/pinduoduo/kuaishou/jingdong/officecdn
6. **国内域名后缀 DIRECT** — qq.com, weixin.com, wechat.com, gtimg.com, qcloud.com, myqcloud.com, qpic.cn, tenpay.com, tmall.com, jd.com, 360buyimg.com, iqiyi.com, youku.com, ykimg.com
7. **海外服务 PROXY** — google/youtube/facebook/twitter/instagram/telegram(keyword) + openai/chatgpt/anthropic/claude/github/githubusercontent/githubcopilot/wikipedia/t.me/telegram.org(suffix) + Telegram IP 段
8. **`GEOIP,CN,DIRECT`** — 兜底前地理判断
9. **`MATCH,PROXY`**（Clash 由 3x-ui 自动补 / SR 用 `FINAL,PROXY`）— 其余海外走代理

完整规则文本见 `scripts/parko-shadowrocket.conf`（SR 格式）与 `scripts/clash-rules-prepend.yaml`（Clash 格式）。两者内容一致，仅语法与兜底写法不同。

## 客户端订阅链接（当前 IP 141.147.189.28）

- Clash（自带规则）：`http://141.147.189.28:2096/parko-clash/parko`
- base64（仅节点）：`http://141.147.189.28:2096/parko-sub/parko`
- Shadowrocket：导入 `scripts/parko-shadowrocket.conf`
