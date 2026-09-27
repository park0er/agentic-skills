# 02 网络：VCN、公网 IP、两层防火墙

Oracle 实例能从公网访问需要四样东西：**Internet Gateway、路由、公网 IP、防火墙放行**。防火墙有两层：云上的 **Security List** 和系统里的 **iptables**。两层都要放行，漏掉任何一层端口都不通。

## 1. Internet Gateway 和路由

用控制台向导创建 VCN 时，通常会自动建好 Internet Gateway 和 `0.0.0.0/0` 路由，东京那次两样都已经有了。检查位置：

- VCN → Gateways：应有 Internet Gateway，状态 Available
- VCN → Routing → Default Route Table：应有 `0.0.0.0/0 → Internet Gateway`

CLI 检查：
```bash
oci network internet-gateway list --compartment-id "$TENANCY" --vcn-id "$VCN" --profile US
oci network route-table list --compartment-id "$TENANCY" --vcn-id "$VCN" --profile US \
  --query 'data[].{"name":"display-name",rules:"route-rules"}'
```

## 2. 公网 IP：用 Reserved IP

| | Ephemeral | Reserved |
|---|---|---|
| IP 会不会变 | 停机或重启可能变 | 固定，手动释放前不变 |
| 能否主动换 | 不能 | 能（IP 被墙时换新的） |
| 费用 | 免费 | 绑在运行中的实例上免费；**没绑实例时收费** |
| 速度 | 一样 | 一样 |

选 Reserved。IP 变了，已分发的订阅就全部失效。

控制台操作：实例 → Networking → Attached VNICs → 点 VNIC → IPv4 Addresses → 私有 IP 那行的 ⋮ → Edit → Reserved public IP → Create new → Update。

CLI 操作（agent 可以直接做）：
```bash
INSTANCE=<实例 OCID>
VNIC=$(oci compute vnic-attachment list --compartment-id "$TENANCY" --instance-id "$INSTANCE" \
  --query 'data[0]."vnic-id"' --raw-output --profile US)
PRIVATE_IP=$(oci network private-ip list --vnic-id "$VNIC" --query 'data[0].id' --raw-output --profile US)

# 如果已有 Ephemeral IP，先摘掉（Reserved 和 Ephemeral 不能同时挂）
EPH=$(oci network public-ip get --private-ip-id "$PRIVATE_IP" --query 'data.id' --raw-output --profile US 2>/dev/null)
[ -n "$EPH" ] && oci network public-ip delete --public-ip-id "$EPH" --force --profile US

oci network public-ip create --compartment-id "$TENANCY" --lifetime RESERVED \
  --private-ip-id "$PRIVATE_IP" --display-name "pip-vpn-us" \
  --query 'data."ip-address"' --raw-output --profile US
```

释放不用的 Reserved IP，否则会收费：`oci network public-ip delete --public-ip-id <OCID> --force`。

## 3. Security List（云防火墙）

在 VCN → Security → Default Security List → Add Ingress Rules 里添加，每条 Source CIDR 都是 `0.0.0.0/0`、协议 TCP：

| 端口 | 用途 | 要不要对公网开放 |
|---|---|---|
| 22 | SSH | 默认已开 |
| 443 | VLESS REALITY | **必须开** |
| 2096 | 3x-ui 订阅服务 | 需要客户端能拉订阅就开 |
| 2053 | 3x-ui 面板 | **绝对不开**，只走 SSH 隧道 |

**端口一次想清楚再开**。东京那次先后开了 443、2096，又临时开了一个 8443（多余，后来删掉了），用户对「为什么每次端口都不一样」很困惑。只开上表列出的端口，测试用的临时端口测完就删。

CLI 操作（注意：`update` 是**整表覆盖**，必须先读出现有规则，再把新规则合并进去）：
```bash
SL=<security list OCID>
oci network security-list get --security-list-id "$SL" --profile US \
  --query 'data."ingress-security-rules"' > ingress.json
# 用 python 往 ingress.json 里追加 443 和 2096 两条 TCP 规则后：
oci network security-list update --security-list-id "$SL" \
  --ingress-security-rules file://ingress.json --force --profile US
```
不熟悉这个流程的话，控制台手动加两条更安全。

## 4. iptables（系统防火墙）

Oracle 的 Ubuntu 镜像自带一套 iptables 规则，默认只放行 22。**只在 Security List 放行不够，还要在系统里放行。** `scripts/server-bootstrap.sh` 会处理这一步：它会把规则插到 REJECT 规则之前并持久化保存。

排查 443 不通时按这个顺序查：iptables → Security List → 路由表 → 公网 IP 是否已绑定。
