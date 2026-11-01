# -*- coding: utf-8 -*-
"""由 agent.yaml 与 system-prompt.md 生成 Trae 可直接粘贴的导出文件。"""

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "agent.yaml"
PROMPT = ROOT / "system-prompt.md"
OUTPUT = ROOT / "pet-care-consultant-export.md"


def build():
    agent = AGENT.read_text(encoding="utf-8")
    prompt = PROMPT.read_text(encoding="utf-8")
    first_agent_line = agent.splitlines()[0].strip()
    version = "2.0.0"
    marker = "Agent 元配置 v"
    if marker in first_agent_line:
        version = first_agent_line.split(marker, 1)[1].strip()

    content = (
        "# 养宠顾问 智能体配置导出（v{}）\n\n"
        "> 本文件由 `tools/build_export.py` 从 agent.yaml + system-prompt.md 生成，"
        "供直接粘贴到 Trae 使用。\n\n"
        "## 一、agent.yaml\n\n"
        "```yaml\n{}```\n\n"
        "---\n\n"
        "## 二、system-prompt.md\n\n"
        "```markdown\n{}```\n"
    ).format(version, agent, prompt)

    assert agent in content, "agent.yaml 未完整进入导出文件"
    assert prompt in content, "system-prompt.md 未完整进入导出文件"
    return content


def main():
    content = build()
    with OUTPUT.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    print("wrote pet-care-consultant-export.md bytes={} sha256_16={}".format(
        len(content.encode("utf-8")), digest))


if __name__ == "__main__":
    main()
