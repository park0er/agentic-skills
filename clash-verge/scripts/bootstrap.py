#!/usr/bin/env python3
"""
Clash Verge parko profile bootstrap — 新机器全自动搭建

用法:
    python3 bootstrap.py                          # 用默认 parko 订阅 URL
    python3 bootstrap.py <parko_url>              # 自定义订阅 URL
    python3 bootstrap.py <parko_url> <name>       # 自定义 URL + profile 名

前置条件:
    1. 已安装 Clash Verge Rev 并启动过一次（生成数据目录）
    2. 当前办公网络可达 parko 订阅服务器（默认 http://141.147.189.28:2096）

效果:
    - 下载 parko 订阅注册为 remote profile
    - 从 templates/ 拷贝 extend script + rules override 并绑定到 parko
    - 开启 TUN + 系统代理（写 verge.yaml）
    - 设置 parko 为 current profile
    - 不碰 GUI（用户只需启动/重启 Clash Verge 让配置生效）

执行后:
    启动（或重启）Clash Verge GUI → 跑 /clash-verge 做连通性验证
"""
import os
import re
import sys
import time
import random
import string
import urllib.request
from pathlib import Path

DATA_DIR = Path.home() / "Library" / "Application Support" / "io.github.clash-verge-rev.clash-verge-rev"
PROFILES_DIR = DATA_DIR / "profiles"
PROFILES_YAML = DATA_DIR / "profiles.yaml"
VERGE_YAML = DATA_DIR / "verge.yaml"
SCRIPT_TEMPLATE = Path(__file__).parent.parent / "templates" / "extend-script.js"
RULES_TEMPLATE = Path(__file__).parent.parent / "templates" / "rules-override.yaml"

DEFAULT_PARKO_URL = "http://141.147.189.28:2096/parko-clash/parko"
DEFAULT_NAME = "parko"


def gen_uid():
    """生成 12 位 base62 uid（与 Clash Verge GUI 生成的格式一致）"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(12))


def now_ts():
    return int(time.time())


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "clash-verge-bootstrap/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, 'wb') as f:
        f.write(r.read())


def read_text(p):
    return p.read_text(encoding='utf-8')


def write_text(p, s):
    p.write_text(s, encoding='utf-8')


def set_flag(text, key, val):
    """YAML 单行 flag 替换。匹配 `key: oldval` → `key: val`。不存在则追加。"""
    pattern = rf'^{re.escape(key)}: .*$'
    replacement = f'{key}: {val}'
    if re.search(pattern, text, flags=re.MULTILINE):
        return re.sub(pattern, replacement, text, count=1, flags=re.MULTILINE)
    return text.rstrip() + f"\n{replacement}\n"


def main():
    # 参数解析
    parko_url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PARKO_URL
    profile_name = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_NAME

    # 前置检查
    if not DATA_DIR.exists():
        die(
            f"Clash Verge 数据目录不存在: {DATA_DIR}\n"
            f"请先安装 Clash Verge Rev 并启动一次以初始化目录。"
        )
    if not PROFILES_YAML.exists():
        die(f"profiles.yaml 不存在: {PROFILES_YAML}\n请先启动一次 Clash Verge。")
    if not SCRIPT_TEMPLATE.exists():
        die(f"extend-script 模板缺失: {SCRIPT_TEMPLATE}")
    if not RULES_TEMPLATE.exists():
        die(f"rules-override 模板缺失: {RULES_TEMPLATE}")

    profiles_yaml = read_text(PROFILES_YAML)

    # 幂等性：检测是否已导入同名 profile
    if f'name: {profile_name}' in profiles_yaml:
        die(
            f"profiles.yaml 已含 name: {profile_name}，不重复导入。\n"
            f"如需重建请先在 GUI 删除该 profile 再跑本脚本。"
        )

    # 生成 uid
    remote_uid = gen_uid()
    script_uid = gen_uid()
    rules_uid = gen_uid()
    ts = now_ts()
    print(f"[1/6] 生成 uid: remote={remote_uid} script={script_uid} rules={rules_uid}")

    # 下载订阅
    remote_file = PROFILES_DIR / f"{remote_uid}.yaml"
    print(f"[2/6] 下载订阅 → {remote_file.name}  ({parko_url})")
    try:
        download(parko_url, remote_file)
    except Exception as e:
        die(f"下载订阅失败: {e}\nURL: {parko_url}")

    # 写 extend script（替换模板注释里的占位 uid）
    script_file = PROFILES_DIR / f"{script_uid}.js"
    script_content = read_text(SCRIPT_TEMPLATE)
    script_content = script_content.replace("saDMY9wRANlr.js", f"{script_uid}.js")
    write_text(script_file, script_content)
    print(f"[3/6] 写 extend script → {script_file.name}")

    # 写 rules override
    rules_file = PROFILES_DIR / f"{rules_uid}.yaml"
    write_text(rules_file, read_text(RULES_TEMPLATE))
    print(f"[4/6] 写 rules override → {rules_file.name}")

    # 修改 profiles.yaml：追加 3 条 items + 设 current
    new_entries = (
        f"- uid: {script_uid}\n"
        f"  type: script\n"
        f"  name: null\n"
        f"  file: {script_uid}.js\n"
        f"  updated: {ts}\n"
        f"- uid: {rules_uid}\n"
        f"  type: rules\n"
        f"  name: null\n"
        f"  file: {rules_uid}.yaml\n"
        f"  updated: {ts}\n"
        f"- uid: {remote_uid}\n"
        f"  type: remote\n"
        f"  name: {profile_name}\n"
        f"  file: {remote_uid}.yaml\n"
        f"  url: {parko_url}\n"
        f"  extra:\n"
        f"    upload: 0\n"
        f"    download: 0\n"
        f"    total: 0\n"
        f"    expire: 0\n"
        f"  updated: {ts}\n"
        f"  option:\n"
        f"    update_interval: 720\n"
        f"    allow_auto_update: true\n"
        f"    script: {script_uid}\n"
        f"    rules: {rules_uid}\n"
        f"  home: {parko_url}\n"
    )
    profiles_yaml = profiles_yaml.rstrip() + "\n" + new_entries
    profiles_yaml = re.sub(r'^current: .*', f'current: {remote_uid}',
                           profiles_yaml, count=1, flags=re.MULTILINE)
    write_text(PROFILES_YAML, profiles_yaml)
    print(f"[5/6] 注册到 profiles.yaml，current={profile_name}({remote_uid})")

    # 修改 verge.yaml：开 TUN + 系统代理
    if VERGE_YAML.exists():
        verge_yaml = read_text(VERGE_YAML)
        verge_yaml = set_flag(verge_yaml, 'enable_tun_mode', 'true')
        verge_yaml = set_flag(verge_yaml, 'enable_system_proxy', 'true')
        write_text(VERGE_YAML, verge_yaml)
        print(f"[6/6] 开启 TUN + 系统代理 (verge.yaml)")
    else:
        print(f"[6/6] 跳过 verge.yaml（文件不存在，将由 GUI 首次启动创建）")

    print()
    print("✅ Bootstrap 完成。下一步：")
    print(f"  1. 启动（或重启）Clash Verge GUI 让配置生效")
    print(f"  2. 跑 /clash-verge 做连通性验证")
    print()
    print("生成的文件：")
    print(f"  {remote_file.name}  ← 远程订阅")
    print(f"  {script_file.name}  ← extend script")
    print(f"  {rules_file.name}  ← rules override")


if __name__ == '__main__':
    main()
