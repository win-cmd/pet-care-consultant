# -*- coding: utf-8 -*-
"""生成可复现的 Trae 养宠顾问 ZIP，排除缓存、日志与上一版发布包。"""

import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
EXCLUDED_PARTS = {".git", "__pycache__", "node_modules", "dist", ".runtime", ".pytest_cache"}
EXCLUDED_NAMES = {".Rhistory"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}


def selected_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.name in EXCLUDED_NAMES or path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        yield path, Path("pet-care-consultant") / relative


def build():
    version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    DIST.mkdir(exist_ok=True)
    output = DIST / "pet-care-consultant-trae-v{}.zip".format(version)
    files = list(selected_files())
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, arcname in files:
            archive.write(source, arcname.as_posix())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return output, len(files), digest


def main():
    output, count, digest = build()
    print("wrote {} files={} bytes={} sha256={}".format(
        output.name, count, output.stat().st_size, digest))


if __name__ == "__main__":
    main()
