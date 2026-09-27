# 05 防闲置回收

## 规则

Oracle 官方文档 "Reclamation of Idle Compute Instances"：在 7 天窗口内，以下三项**同时**低于阈值时，实例会被判定为闲置并回收：
- CPU 95 分位 < 20%
- 网络利用率 < 20%
- 内存利用率 < 20%（**只对 A1 生效**）

只要有一项持续高于 20% 就安全。因为用的是 95 分位，每天有 5% 的时间（约 1.2 小时）负载超过 20% 就够。回收前 Oracle 会发邮件提醒。

VPN 机器平时的负载只有 1% 到 4%，三项都达不到阈值，**上线当天就要装保活**。

## 安装

```bash
scp -i "$KEY" scripts/anti-reclaim/* ubuntu@"$IP":~
ssh -i "$KEY" ubuntu@"$IP" 'sudo bash -s' <<'EOF'
install -m 755 ~ubuntu/oci-anti-reclaim.sh /usr/local/bin/oci-anti-reclaim.sh
install -m 644 ~ubuntu/oci-anti-reclaim.service ~ubuntu/oci-anti-reclaim.timer /etc/systemd/system/
apt-get install -y -qq stress-ng
systemctl daemon-reload && systemctl enable --now oci-anti-reclaim.timer
systemctl list-timers --all | grep anti-reclaim
EOF
```

按机型修改 service 里的 `ExecStart` 参数，格式是 `<秒数> <每核 CPU%> <每个 worker 的内存 MB>`：

| 机型 | 参数 | 说明 |
|---|---|---|
| A1 2C/12G | `10800 30 1280` | 每天 3 小时（12.5%），2 × 1280M ≈ 21% 内存 |
| A1 4C/24G | `10800 30 1300` | 4 × 1300M ≈ 21% |
| E2.1.Micro | `7200 40 0` | 只压 CPU。E2 不考核内存，而且只有 1 GB，压内存会 OOM |

`timer` 里的 `OnCalendar` 是**服务器时区**（默认 UTC）。选用户的非高峰时段：北京时间 05:00 = UTC 21:00。美国机器同样按北京时间来选，因为用户在国内使用。

`CPUSchedulingPolicy=idle` 和 `Nice=10` 保证有真实流量时保活进程自动让出 CPU，不影响 VPN 使用。

## 验证

```bash
systemctl list-timers --all | grep anti-reclaim
systemctl status oci-anti-reclaim.service      # 看是否 status=0/SUCCESS
journalctl -u oci-anti-reclaim.service --no-pager | tail -20
```

两个已知坑：
- 手动跑过一次之后，当天定时触发会输出 "already running, skip"，这是正常的防重入逻辑。
- `stress-ng` 参数换行时续行符写错，会被拆成两条命令，报 `--cpu: command not found`（exit 127）。
