#!/usr/bin/env python3
"""
Static evals for rollie-summarize.

These checks validate the skill contract that matters before runtime:
- the trigger description covers all intended sources
- Feishu routes through the current feishu skill
- old MCP/Credential-based workflows are prohibited rather than executable
- the output contract preserves Obsidian and Feishu provenance rules
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8")


def check(name: str, passed: bool, evidence: str) -> dict[str, object]:
    return {"name": name, "passed": passed, "evidence": evidence}


def main() -> int:
    skill = read("SKILL.md")
    source = read("references/source_routing.md")
    output = read("references/output_contract.md")
    user_profile = read("references/user_profile.md")
    evals = json.loads(read("evals/evals.json"))

    checks = [
        check(
            "eval cases exist",
            len(evals.get("evals", [])) >= 3,
            f"{len(evals.get('evals', []))} eval cases found",
        ),
        check(
            "frontmatter name is rollie-summarize",
            "name: rollie-summarize" in skill,
            "SKILL.md frontmatter contains expected name",
        ),
        check(
            "description covers broad source types",
            all(token in skill for token in ["飞书文档", "X/Twitter", "公众号文章", "任意网页 URL", "本地文件"]),
            "SKILL.md description includes Feishu, X/Twitter, WeChat, URL, and local file triggers",
        ),
        check(
            "Feishu uses current skill",
            "feishu fetch <url>" in skill and "feishu fetch <url>" in source,
            "Feishu routing points to feishu fetch",
        ),
        check(
            "old Feishu MCP is only prohibited",
            "不要使用 `mcp_feishu_*`" in skill and "不使用旧命令" in source,
            "old mcp_feishu commands are described as forbidden, not as a workflow",
        ),
        check(
            "X/Twitter route avoids login bypass",
            all(token in source for token in ["X Article", "不读取本地密码文件", "不代替用户登录", "不绕过登录墙"]),
            "X/Twitter routing handles articles while prohibiting credential/login bypass",
        ),
        check(
            "four-section output exists",
            all(token in skill for token in ["核心内容总结", "逻辑硬伤分析", "对盛总的价值提炼", "具体行动项"]),
            "SKILL.md requires the four Rollie sections",
        ),
        check(
            "Obsidian output contract exists",
            "Rollie/Rollie的报告厅" in output and "ls " in output,
            "output_contract.md fixes and verifies the Obsidian target directory",
        ),
        check(
            "Feishu provenance is preserved",
            "<!-- feishu:" in output,
            "output_contract.md includes Feishu provenance comment",
        ),
        check(
            "user profile updated away from MCP",
            "飞书 CLI / feishu skill" in user_profile and "飞书 MCP" not in user_profile,
            "user_profile.md references current Feishu tooling",
        ),
    ]

    print(json.dumps({"checks": checks}, ensure_ascii=False, indent=2))
    failed = [item for item in checks if not item["passed"]]
    if failed:
        print(f"\nFAILED: {len(failed)} static eval checks failed", file=sys.stderr)
        return 1
    print(f"\nPASSED: {len(checks)} static eval checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
