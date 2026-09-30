#!/usr/bin/env python3
"""生成给 Clash Meta for Android 用的完整配置（含节点，不入库）。

背景：Clash Meta for Android 的「覆写 / Override」只支持全局设置项
（端口、DNS、ipv6、mode 等），其源码里的 ConfigurationOverride 没有
rules 字段，所以它无法像 Clash Verge 那样挂一份「规则覆写」。

它吃规则的唯一入口是完整配置文件（含 proxies + proxy-groups + rules）。
本脚本把订阅和自定义规则合并成一份完整 yaml，输出到 android/config.yaml。

订阅地址放在 android/subscription-url.txt（不入库）。输出文件也含节点信息，
已在 .gitignore 里排除，只在本机使用。
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent
SUB_FILE = REPO / "android" / "subscription-url.txt"
OUT = REPO / "android" / "config.yaml"
RULES_YAML = REPO / "clash" / "rules.yaml"


def fetch_subscription() -> str:
    if not SUB_FILE.exists():
        sys.exit(f"缺少本机私有订阅地址文件: {SUB_FILE}")
    sub_url = SUB_FILE.read_text(encoding="utf-8").strip()
    proc = subprocess.run(
        ["curl", "-s", "--max-time", "30", "--config", "-"],
        input="url = " + json.dumps(sub_url) + "\n",
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        sys.exit(f"拉取订阅失败: {proc.stderr}")
    if "proxies:" not in proc.stdout:
        sys.exit("订阅内容异常：没有 proxies 段")
    return proc.stdout


def load_prepend_rules() -> list:
    rules = []
    in_block = False
    for line in RULES_YAML.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("prepend:"):
            in_block = True
            continue
        if s.startswith("append:"):
            in_block = False
            continue
        if in_block and s.startswith("- "):
            rules.append(s[2:].strip().strip("'"))
    return rules


def merge(sub_text: str, extra_rules: list) -> str:
    lines = sub_text.splitlines()
    try:
        idx = next(i for i, l in enumerate(lines) if l.rstrip() == "rules:")
    except StopIteration:
        sys.exit("订阅里找不到 rules: 段")

    head = lines[: idx + 1]
    tail = lines[idx + 1 :]
    insert = []
    for r in extra_rules:
        if not any(t.strip() == "- " + r for t in tail):
            insert.append("  - " + r)
    return "\n".join(head + insert + tail) + "\n"


def main() -> None:
    sub = fetch_subscription()
    extra = load_prepend_rules()
    if not extra:
        sys.exit("clash/rules.yaml 里没读到任何规则")

    merged = merge(sub, extra)
    if not merged.lstrip().startswith("mixed-port:"):
        sys.exit("生成的配置结构异常")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(merged, encoding="utf-8")
    OUT.chmod(0o600)

    n_rules = len(re.findall(r"^  - ", merged, re.M))
    print(f"已生成 {OUT}")
    print(f"  额外插入规则: {len(extra)} 条")
    print(f"  总规则数: {n_rules}")
    print("  该文件含节点信息，已在 .gitignore 排除，不要提交。")


if __name__ == "__main__":
    main()
