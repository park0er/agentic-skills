# 04 客户端接入、分流规则、分享

## 订阅格式和客户端的对应关系

| 格式 | 地址 | 带不带规则 | 适用客户端 |
|---|---|---|---|
| Clash YAML | `http://IP:2096/parko-clash/<subId>` | 带（服务器内置） | Clash Verge / Mihomo / Stash |
| base64 | `http://IP:2096/parko-sub/<subId>` | 不带，只有 `vless://` 节点 | v2rayN / NekoBox |
| `vless://` 链接或二维码 | 面板 → client → Copy URL / QR | 不带 | Shadowrocket 扫码 |
| Shadowrocket `.conf` | 手动导入文件 | 带 | Shadowrocket（**东京那次最终用的是这种**） |

- Clash Verge 导入 base64 订阅会报 "invalid yaml"，必须用 Clash 地址。
- 3x-ui 输出的 Clash YAML 不带 `mixed-port`、`dns` 这些顶层字段，Clash Verge 会自动补全，不需要处理。导入后要**把这个 profile 设为当前使用**，并确认 mode 是 Rule，不是 Direct。
- 商业机场能直接配好 Shadowrocket，是因为它按 User-Agent 返回不同格式；3x-ui 没有这个功能。东京那次尝试让 Shadowrocket 读 Clash 订阅没有成功，最后用手动导入 `.conf` 解决。
- 二维码里存的就是 `vless://` 配置本身，不是链接，扫码后不依赖任何订阅服务。

## 分流规则（沿用东京那套）

思路：去广告 → 公司内网和私有 IP 直连 → Apple 直连 → 国内大厂直连 → 海外服务走代理 → `GEOIP,CN,DIRECT` → `MATCH,PROXY`。规则**直接写在配置里**，不引用外部 RULE-SET，因为从国内拉 GitHub 上的规则集本身就可能失败。

规则原文就用 `oracle-vpn-ops` 里的两个文件，不要另起一份：
- Clash 格式：`~/.agents/skills/oracle-vpn-ops/scripts/clash-rules-prepend.yaml`
- Shadowrocket 格式：`~/.agents/skills/oracle-vpn-ops/scripts/parko-shadowrocket.conf`

### 在服务器内置规则（Clash 订阅自动带上）

`subClashRules` 每行一条，3x-ui 会插到 `MATCH,PROXY` 之前，所以规则以 `GEOIP,CN,DIRECT` 结尾就行。策略组名称用 `PROXY`。写入方法（从 yaml 中去掉引号和 `- ` 前缀后，逐行拼接）：

```bash
ssh -i "$KEY" ubuntu@"$IP" 'sudo cp /etc/x-ui/x-ui.db /etc/x-ui/x-ui.db.bak.$(date +%s)'
# 把规则文本写进 rules.txt 并上传，然后：
ssh -i "$KEY" ubuntu@"$IP" 'sudo python3 - <<"PY"
import sqlite3
rules=open("/home/ubuntu/rules.txt").read().strip()
c=sqlite3.connect("/etc/x-ui/x-ui.db")
for k,v in (("subClashRules",rules),("subClashEnableRouting","true")):
    if c.execute("select 1 from settings where key=?",(k,)).fetchone():
        c.execute("update settings set value=? where key=?",(v,k))
    else:
        c.execute("insert into settings(key,value) values(?,?)",(k,v))
c.commit()
PY
sudo systemctl restart x-ui'
```

服务器内置了规则之后，Clash Verge 本地就不要再加同样的 rules override，避免维护两份。

### Shadowrocket `.conf`

复制 `parko-shadowrocket.conf`，把 `[Proxy]` 那一行的 IP、UUID、public-key、short-id、sni 改成新机器的值，节点名改成新名称。规则部分用的是内置策略 `PROXY`、`DIRECT`、`REJECT`，不绑定节点名。通过 AirDrop 发到手机，用 Shadowrocket 打开导入。

## 给别人开账号

每个人或每台设备建一个 client（email 用来区分）。给对方单独的 subId，并设置 `limitIp`。东京的例子：`yidi@vpn`，limitIp 4。具体命令见 `oracle-vpn-ops` 的 client-management.md。

## 看到陌生 IP 先别下结论

`ss -tn state established '( sport = :443 )'` 能看到连接来源。东京那次看到一个美国 IP 占了一半连接，差点当成被盗用，实际是用户自己的链式代理出口。**判断有人盗用之前，先问用户有没有链式代理、多台设备或者和家人共用。**
