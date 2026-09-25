# parko Profile 架构

## 文件布局

所有文件位于 `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/`

```
profiles/
├── R6IdJowV5G47.yaml      ← 远程订阅 (parko 服务端下发，只读)
├── mqVZFrGZ3c3H.yaml      ← merge override (未使用)
├── saDMY9wRANlr.js         ← extend script (DNS + 链式代理) ← 可改
├── rJDbf1hBTouK.yaml       ← rules override (prepend/append/delete) ← 可改
├── pZEw27gIK62X.yaml       ← proxies override (未使用)
└── gBLx1BFIZUkw.yaml       ← groups override (未使用)

profiles.yaml               ← profile 元数据 (parko 对应的 override 文件关系)
clash-verge.yaml            ← 运行时合并后的完整配置
verge.yaml                  ← Clash Verge 自身配置
```

## 处理流程

```
远程订阅 (R6IdJowV5G47.yaml)
    │
    ├── merge: mqVZFrGZ3c3H.yaml          (空)
    ├── script: saDMY9wRANlr.js            (DNS + 链代)
    ├── rules: rJDbf1hBTouK.yaml           (prepend/delete/append)
    ├── proxies: pZEw27gIK62X.yaml         (空)
    └── groups: gBLx1BFIZUkw.yaml          (空)
    │
    ▼
clash-verge.yaml (最终运行时配置)
```

## 可改文件

### saDMY9wRANlr.js — Extend Script

运行时 `config` 对象在合并完成后传入脚本。脚本可以修改 DNS、proxy-groups、proxies 等任意字段。

本 profile 的 script 负责：
- TCP 保活参数
- DNS nameserver-policy（公司域名走 dhcp://en0）
- fake-ip-filter（避免内网域名 fake-ip 污染）
- fake-ip-range 切换（避开小米 198.18.0.0/16）
- 链式代理组装（parko-tokyo → 圣何塞静态ip2）

### rJDbf1hBTouK.yaml — Rules Override

三个数组字段：
- `prepend` — 在远程规则前插入（优先级最高）
- `delete` — 从远程规则中删除同名条目
- `append` — 在远程规则后追加（优先级最低）

典型用法：prepend DIRECT 规则 + delete 原有 PROXY 规则。

## 修改后的生效方式

在 Clash Verge GUI 中右键 parko profile → 刷新（或等自动刷新周期），修改即生效。
无需重启 Clash Verge。
