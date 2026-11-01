# -*- coding: utf-8 -*-
"""检查发布 ZIP 的必要文件与安全语义，不修改任何文件。"""

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_NAME = "pet-care-consultant"
REQUIRED = [
    "README.md",
    "package.json",
    "启动提示词.txt",
    "system-prompt.md",
    "agent.yaml",
    "agent-config.json",
    "knowledge/forbidden-foods.md",
    "companion/server.mjs",
    "companion/start.mjs",
    "companion/pet.mjs",
    "companion/protocol.mjs",
    "companion/index.html",
    "companion/styles.css",
    "companion/app.js",
    "companion/protocol.test.mjs",
    "companion/server.test.mjs",
    "tools/build_export.py",
    "tools/build_release.py",
]
FORBIDDEN = {"__pycache__", ".git", "node_modules", "dist", ".runtime"}


def main():
    candidates = sorted((ROOT / "dist").glob("pet-care-consultant-trae-v*.zip"))
    if not candidates:
        print("FAIL: 没有找到发布 ZIP，请先运行 python tools/build_release.py")
        return 1
    archive_path = candidates[-1]
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        missing = [name for name in REQUIRED if "{}/{}".format(ROOT_NAME, name) not in names]
        leaked = [name for name in names if any(part in FORBIDDEN for part in Path(name).parts)]
        prompt = archive.read("{}/system-prompt.md".format(ROOT_NAME)).decode("utf-8")
        startup = archive.read("{}/启动提示词.txt".format(ROOT_NAME)).decode("utf-8")

    failures = []
    if missing:
        failures.append("缺少必要文件：{}".format("、".join(missing)))
    if leaked:
        failures.append("包含不应发布的文件：{}".format("、".join(leaked)))
    if "## 动态宠物联动（本地可选展示）" not in prompt:
        failures.append("缺少动态宠物联动规则")
    if "不是死亡诊断" not in prompt or "必然死亡" not in prompt:
        failures.append("危险演示缺少非死亡诊断约束")
    if "本回答仅为喂养科普，不能替代执业兽医面诊" not in prompt:
        failures.append("免责声明原句缺失或已漂移")
    if "node companion/start.mjs" not in startup:
        failures.append("启动提示词未包含本地服务启动命令")

    if failures:
        print("FAIL: " + archive_path.name)
        for failure in failures:
            print("  - " + failure)
        return 1

    print("PASS: {} files={}".format(archive_path.name, len(names)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
