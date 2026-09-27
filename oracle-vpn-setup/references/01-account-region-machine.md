# 01 账号、区域、机型

## 1. Home Region

- Always Free 资源**只在 Home Region 免费**，注册时选定，之后不能改（Oracle 官方文档 "Always Free Resources"）。
- 免费账号不能靠订阅其他区域来多拿一份免费额度。要在别的区域开机器，要么新注册一个账号，要么升级 Pay As You Go 后付费使用。
- 注册时的信用卡验证会做一次小额授权再撤销。**之后 Oracle 还会周期性地重复这个验证**（官方 FAQ："may periodically check the validity of your card"），跟抢机没有关系，也不会真正扣款。只要不主动升级 Pay As You Go 就不会收费。

### 美国区域怎么选（从国内连过去）

| 区域 | 标识 | 从国内连 | 备注 |
|---|---|---|---|
| US West (San Jose) | `us-sanjose-1` | 美国区里延迟最低（西海岸） | 单 AD，A1 容量可能紧张 |
| US West (Phoenix) | `us-phoenix-1` | 比 San Jose 稍远 | 老牌大区 |
| US East (Ashburn) | `us-ashburn-1` | 东海岸，延迟明显更高 | 最大的区 |
| US Midwest (Chicago) | `us-chicago-1` | 居中 | |

AD 数量和 A1 容量随时间会变。注册后用 `scripts/collect-ocids.sh` 实测 AD 列表，**不要照搬这张表**。有多个 AD 的区域，抢机脚本会轮流尝试各个 AD，抢到的概率更高。

美国到国内的 RTT 大约是东京的 3 到 4 倍。**跨境链路越长，BBR 和 TCP 缓冲区越重要**（原理见 03 和 06）。延迟敏感的用途（网页、聊天）东京更合适；美国机器适合需要美国出口 IP 的场景。

## 2. 机型

| | VM.Standard.A1.Flex | VM.Standard.E2.1.Micro |
|---|---|---|
| 架构 | ARM64 (Ampere) | x86_64 (AMD) |
| 免费额度 | 标准是合计 4 OCPU / 24 GB，**可能被砍**（东京账号实测只有 2 OCPU / 12 GB） | 最多 2 台，每台 1/8 OCPU / 1 GB |
| 网卡带宽 | 按 OCPU 计（2 OCPU 实测标称 2 Gbps） | 0.48 Gbps |
| 开机难度 | 常见 `Out of host capacity`，需要抢 | 一般能直接开 |
| 回收判定 | CPU、网络、**内存**三项 | CPU、网络两项 |

**推荐做法**：先开 E2.1.Micro 把 VPN 跑起来；同时后台挂抢机脚本抢 A1；抢到 A1 后迁移过去，E2 留作备机。

**关于速度的实测结论**：单连接速度的瓶颈是跨境链路，不是机型。东京 E2 的单线程加密能力约 11 Gbps，实际 VPN 速度只有 42 Mbps。换成 A1 带来的是**并发能力**（内存 1 GB 到 12 GB），单连接不会明显变快。不要为了单连接提速去等 A1。

### 先查额度，再决定抢多大

东京账号按 4C/24G 抢时，一直被 `LimitExceeded`（HTTP 400）硬拒绝，这是**额度问题**，跟库存无关，重试多少次都没用。开抢前先查一下：

```bash
oci limits value list --compartment-id "$TENANCY" --service-name compute --all \
  --query "data[?contains(name,'standard-a1')].{name:name,value:value}" --output table --profile US
# 看 standard-a1-core-count 和 standard-a1-memory-count（东京账号实测是 2 和 12）
# 一定要加 --all，否则结果分页，会漏掉这两项
```

`OCPUS` 和 `MEM_GB` 按查到的上限设置。

## 3. 镜像

- 选 **Canonical Ubuntu 22.04**。**E2 选 x86 版，A1 选 aarch64 版**。镜像列表里 "Minimal aarch64" 是 ARM 版，不带 aarch64 后缀的才是 x86 版。
- Minimal 和完整版都可以。**BBR 在两个版本上都默认不开**，东京那次下载慢跟 Minimal 无关。1 GB 内存的 E2 用 Minimal 更省资源。
- Boot volume 用默认的 50 GB。免费额度合计 200 GB，要给后面的 A1 留够空间。

## 4. 控制台开机要点

- Networking 里新建 VCN 和 **public subnet**。
- 公网 IP 开关有时是灰色的（东京那次遇到过），可以先建实例，再按 02 补上。
- SSH key 选 "Generate a key pair for me"，**当场下载私钥**，存到用户指定的目录。之后 `chmod 600`。
- 保存 `.pub` 公钥，抢机脚本创建 A1 时要用。

## 5. OCI CLI（第一次使用时配置）

```bash
brew install oci-cli      # 已装过就跳过
```

让用户在控制台 Profile → API keys → Add API key → Generate API Key Pair，下载私钥（`.pem`）到密钥目录，然后把 Configuration File Preview 的文本发过来。agent 把它**追加**到 `~/.oci/config`，写成一个新的 profile：

```ini
[US]
user=ocid1.user.oc1..<...>
fingerprint=<..>
tenancy=ocid1.tenancy.oc1..<...>
region=us-sanjose-1
key_file=/absolute/path/to/xxx.pem     # 路径里不能有反斜杠转义，用原始路径
```

```bash
chmod 600 ~/.oci/config "<pem 路径>"
oci iam region list --profile US --output table     # 验证
```

注意：控制台给出的 `key_file` 是 `# TODO` 占位符，而且用户粘贴时路径里常带 `\ ` 转义，**要改成不带转义的真实绝对路径**。

## 6. 抢机

```bash
# 1. 采集 OCID（输出可直接 export）
bash scripts/collect-ocids.sh US            # 参数是 ~/.oci/config 里的 profile 名

# 2. 先前台跑一轮验证参数：返回 "Out of host capacity" = 参数全对，只差容量
PROFILE=US COMPARTMENT=... SUBNET=... IMAGE=... ADS="AD1 AD2" \
SSH_PUB_KEY=... DISPLAY_NAME=parko-vpn-us-a1 OCPUS=2 MEM_GB=12 \
  bash scripts/oracle-grab.sh

# 3. 后台常驻（Mac 不能休眠；日志文件名按 profile 区分，不会和东京的混在一起）
nohup env PROFILE=US ... bash scripts/oracle-grab.sh > ~/oracle-grab-US.out 2>&1 &
tail -n 20 ~/oracle-grab-US.log
```

错误类型和含义：

| 日志 | 含义 | 处理 |
|---|---|---|
| `Out of host capacity` | 正常，没有库存 | 继续等 |
| `LimitExceeded` / quota | 额度不够或已有 A1 | 调小 OCPUS/MEM_GB，或清理现有实例 |
| 429 | 请求太频繁 | 脚本会自动退避 |
| `RequestException ... timed out` | 本机网络抖动，请求根本没发出去 | 无害，不代表抢到过 |

每天定时提醒用 Multica autopilot 做（默认 profile、workspace、agent 见全局 agent rules）。
