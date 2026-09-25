# Oracle Cloud Operations

## Console Access

- URL: https://cloud.oracle.com/?region=ap-tokyo-1
- Tenancy: `zhaoxisheng2`
- Region: Japan East (Tokyo) — **cannot be changed**, all Free Tier resources here

## Key Console Paths

| Task | Navigation |
|---|---|
| Instance details | Compute → Instances → `parko-vpn-tokyo-arm` |
| Security List (firewall) | Networking → VCN → `vcn-20260704-1457` → Security Lists → Default |
| Route Table | Networking → VCN → Routing tab |
| Internet Gateway | Networking → VCN → Gateways tab |
| Reserved IPs | Networking → IP Management → Reserved Public IPs |
| VNIC / Public IP | Instance → Networking tab → Primary VNIC → IPv4 Addresses |

## Add Ingress Rule (open a port)

1. Networking → VCN → `vcn-20260704-1457` → Security Lists → Default
2. Add Ingress Rules:
   - Source CIDR: `0.0.0.0/0`
   - Protocol: TCP
   - Destination Port Range: `<port>`
3. Also add iptables rule on server (see daily-ops.md)

## Rotate / Change Public IP

### Via CLI (推荐，已配好 OCI CLI，全自动)

实测流程（2026-07-04 用此法把 `161.33.130.183` 换成 `141.147.189.28`）：

```bash
TENANCY="ocid1.tenancy.oc1..aaaaaaaamt2d6izfyb6znem55sbkdk7dzan4mvnrwdk2yumq2zpddfsd2poa"

# 1. 找到实例 → VNIC → private-ip
INSTANCE=$(oci compute instance list --compartment-id "$TENANCY" --lifecycle-state RUNNING \
  --query 'data[0].id' --raw-output 2>/dev/null)
VNIC=$(oci compute vnic-attachment list --compartment-id "$TENANCY" --instance-id "$INSTANCE" \
  --query 'data[0]."vnic-id"' --raw-output 2>/dev/null)
PRIVATE_IP=$(oci network private-ip list --vnic-id "$VNIC" \
  --query 'data[0].id' --raw-output 2>/dev/null)

# 2. 找到当前 reserved public IP 的 OCID
OLD_PUB=$(oci network public-ip list --compartment-id "$TENANCY" --scope REGION --lifetime RESERVED \
  --query 'data[0].id' --raw-output 2>/dev/null)

# 3. 摘掉旧 IP（VPN 临时断线几十秒）
oci network public-ip update --public-ip-id "$OLD_PUB" --private-ip-id "" --force

# 4. 创建并绑定新 Reserved IP
oci network public-ip create --compartment-id "$TENANCY" --lifetime RESERVED \
  --private-ip-id "$PRIVATE_IP" --display-name "parko-vpn-tokyo-v2" \
  --query 'data."ip-address"' --raw-output

# 5. 释放旧 IP（避免脱离实例的 Reserved IP 收费）
oci network public-ip delete --public-ip-id "$OLD_PUB" --force
```

换完 IP 后**必须**更新 3x-ui 的 `share_addr` / `subURI` / `subClashURI`（见 troubleshooting.md "IP Possibly Blocked"），并让客户端改订阅 URL。

> 换 IP 前先确认慢的原因**不是** BBR/MSS（见 performance-tuning.md）——本机的"慢"是 cubic 不是 IP 被墙，换 IP 无用。

### Via Console (手动备选)

1. Console → Instance → Networking → Primary VNIC → click VNIC name
2. IPv4 Addresses → ⋮ → Edit the private IP
3. Change Public IP type to "No public IP" → Save
4. Now assign new: same ⋮ → Edit → "Reserved public IP" → "Create new" → Save
5. Update server config (see troubleshooting.md "IP Possibly Blocked")

## Free Tier Limits

| Resource | Free Allowance |
|---|---|
| E2.1.Micro | 2 instances |
| A1.Flex (ARM) | 4 OCPU + 24 GB total (can be 1 or multiple instances) |
| Boot volume | 200 GB total |
| Object Storage | 20 GB |
| Outbound data | 10 TB/month |
| Reserved IPs | Attached to running instances = free; unattached = charged |

## A1.Flex Capacity Grab Script

Target: `VM.Standard.A1.Flex` — 4 OCPU / 24 GB RAM / 4 Gbps network

### Prerequisites (OCI CLI — 已配置完成 ✓)

OCI CLI 已装好并配置认证，无需重做。关键信息：

| Key | Value |
|---|---|
| CLI | oci-cli 3.89.0 (`brew install oci-cli`) |
| Config | `~/.oci/config` (权限 600) |
| API Key (.pem) | `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Iphone1/KEY/OracleCloud/zhaoxisheng@xiaomi.com-*.pem` |
| 验证 | `oci iam region list --output table` |

`~/.oci/config` 内容形如（API Key 从 Console → Profile → API keys → Add API Key 生成，下载私钥 + 复制 Configuration File Preview）：
```ini
[DEFAULT]
user=ocid1.user.oc1..aaaa...
fingerprint=97:22:6a:...
tenancy=ocid1.tenancy.oc1..aaaaaaaamt2d6izfyb6znem55sbkdk7dzan4mvnrwdk2yumq2zpddfsd2poa
region=ap-tokyo-1
key_file=/Users/park0er/Library/Mobile Documents/.../OracleCloud/zhaoxisheng@xiaomi.com-*.pem
```

> 提醒：这套 API Key 与登录服务器的 SSH Key 是**两回事**。SSH Key 进操作系统；API Key 认证 Oracle Cloud 身份，用于 CLI 调云资源。

### 采集到的 OCID（实测,可直接用）

| 参数 | 值 |
|---|---|
| compartment (= tenancy root) | `ocid1.tenancy.oc1..aaaaaaaamt2d6izfyb6znem55sbkdk7dzan4mvnrwdk2yumq2zpddfsd2poa` |
| AD（东京仅 1 个） | `xhDy:AP-TOKYO-1-AD-1` |
| subnet | `ocid1.subnet.oc1.ap-tokyo-1.aaaaaaaaxb3r2anyiz4hgbnoqmpfmjrt6qzc4imz7lvv3k6yg4fbvkeh5pxq` |
| Ubuntu 22.04 aarch64 镜像 | `ocid1.image.oc1.ap-tokyo-1.aaaaaaaal6ki4uyubrmgd4h633jco7b3vca46ddfvlnbnnt7owadvfmbvy3q` |
| SSH 公钥 | `~/Library/.../OracleCloud/ssh-key-2026-07-04.key.pub`（与 `-private.key` 配对，指纹 `SHA256:EU0QzJIsYmk1/tmKWhL5sznO341yYplMh+EheMwSfgU`） |

重新采集命令（换机器/换区域时用）：
```bash
oci iam availability-domain list --compartment-id "$TENANCY" --query 'data[*].name'
oci network subnet list --compartment-id "$TENANCY" --query 'data[*].{name:"display-name",id:id}'
oci compute image list --compartment-id "$TENANCY" --operating-system "Canonical Ubuntu" \
  --operating-system-version "22.04" --shape "VM.Standard.A1.Flex" \
  --sort-by TIMECREATED --sort-order DESC --query 'data[0].id' --raw-output
```

### 抢机脚本（已实测,见 scripts/oracle-a1-grab.sh）

脚本 `scripts/oracle-a1-grab.sh` 已填好上述 OCID，可直接跑。核心逻辑：循环 `oci compute instance launch`，遇 `Out of host capacity`（免费 A1 常态）继续重试，抢到后 macOS 弹通知 + 存 `~/oracle-a1-launch-success.json`。

```bash
# 后台常驻
nohup bash scripts/oracle-a1-grab.sh > ~/oracle-a1-grab.out 2>&1 &
tail -f ~/oracle-a1-grab.log     # 看进度
pkill -f oracle-a1-grab.sh       # 停止
```

**实测行为**：单次 launch 返回 `"message": "Out of host capacity."`（code InternalError, status 500）即证明参数全对、只差容量。带 `--wait-for-state RUNNING` 时 SDK 对 500 会内部重试，每轮约 99s + 60s 间隔 ≈ 2.5 分钟。容量释放随机（几小时~几天），耐心等通知。

> **配额提醒**：Free Tier A1 总量 4 OCPU / 24GB。若脚本报 `LimitExceeded`/`quota`（非 capacity），说明额度已用满或已有 A1 实例，需先在控制台清理。

1. Assign Reserved IP (or new one)
2. SSH in, set up iptables + 3x-ui (same steps as E2.1.Micro)
3. Update SKILL.md with new instance info
4. Optionally terminate E2.1.Micro to free up boot volume quota
