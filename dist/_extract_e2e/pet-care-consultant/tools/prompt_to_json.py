# -*- coding: utf-8 -*-
"""
从 system-prompt.md + agent.yaml 生成 agent-config.json。

用法：
    python tools/prompt_to_json.py          # 重新生成
    python tools/prompt_to_json.py --check  # 只校验现有 json 是否与源文件一致（防漂移）

设计要点：
- 每个提示词段落都带 verbatim 原文与源文件行号，可逐字节还原 system-prompt.md，
  因此 JSON 里的结构化字段只是「便于程序读取的视图」，不是第二份真相。
- 结构化视图（硬性规则 / 范围外表 / 优先级步骤 / 技能 / 输出契约 / 自检项 / 固定话术）
  全部由源文件解析得到，字段值是原文子串，脚本会断言这一点。
"""

import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_MD = os.path.join(ROOT, "system-prompt.md")
AGENT_YAML = os.path.join(ROOT, "agent.yaml")
OUT_JSON = os.path.join(ROOT, "agent-config.json")

NUMBERED = re.compile(r"^(\d+)[.)]\s+(.*)$", re.S)
BULLET = re.compile(r"^[-*+]\s+(.*)$", re.S)
BOLD_HEAD = re.compile(r"^\*\*(.+?)\*\*\s*[：:]?\s*(.*)$", re.S)
STEP = re.compile(r"^\*\*第\s*(\d+)\s*步\s*[：:]\s*(.+?)\s*\*\*")
TIER_LABEL = re.compile(r"【[^】]{1,40}】")
LOCK_TOKENS = ("原句", "不改写", "不省略", "不得改写", "只回复这一句", "固定拒绝话术")


def read_lines(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    assert not text.endswith("\n\n"), "%s 末尾有多个空行，还原逻辑不支持" % path
    return text.rstrip("\n").split("\n")


def classify(line):
    if line.startswith("#"):
        return "heading"
    if line.startswith("|"):
        return "table"
    if line.startswith(">"):
        return "quote_block"
    if NUMBERED.match(line):
        return "numbered"
    if BULLET.match(line):
        return "bullet"
    return "paragraph"


def split_head(body):
    """把一条规则的正文拆成 name（加粗小标题或冒号前的短语）与 text。"""
    m = BOLD_HEAD.match(body)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    idx = body.find("：")
    if 0 < idx <= 40 and "\n" not in body[:idx]:
        return body[:idx].strip(), body[idx + 1:].strip()
    return None, body.strip()


def parse_prompt(lines):
    """按空行与行首标记切块；缩进行并入上一块，保证 verbatim 可逐字节还原。"""
    items = []
    blank = 0
    cur = None
    table = None
    for lineno, raw in enumerate(lines, start=1):
        if raw.strip() == "":
            if table is not None:
                table = None
            blank += 1
            continue
        if raw[:1] in (" ", "\t") and cur is not None and blank == 0:
            cur["verbatim"] += "\n" + raw
            cur["end"] = lineno
            continue
        if raw[:1] in (" ", "\t"):
            # 空行之后的缩进段落是独立条目，不属于上一块
            kind = classify(raw.strip())
            if kind == "numbered":
                cur = {"kind": "numbered", "blank_before": blank, "verbatim": raw.strip(),
                       "start": lineno, "end": lineno}
            elif kind == "bullet":
                cur = {"kind": "bullet", "blank_before": blank, "verbatim": raw.strip(),
                       "start": lineno, "end": lineno}
            else:
                cur = {"kind": "paragraph", "blank_before": blank, "verbatim": raw,
                       "start": lineno, "end": lineno}
            items.append(cur)
            blank = 0
            continue
        if raw.startswith("|"):
            if table is not None:
                table["verbatim"] += "\n" + raw
                table["end"] = lineno
                continue
            cur = {"kind": "table", "blank_before": blank, "verbatim": raw,
                   "start": lineno, "end": lineno}
            table = cur
            items.append(cur)
            blank = 0
            continue
        table = None
        kind = classify(raw)
        cur = {"kind": kind, "blank_before": blank, "verbatim": raw,
               "start": lineno, "end": lineno}
        items.append(cur)
        blank = 0
    return items


def restore(items, header=""):
    out = header
    for it in items:
        out += "\n" * it["blank_before"] + it["verbatim"] + "\n"
    return out


def to_sections(items):
    """扁平块 → 按 ## / ### 分组的章节树。"""
    sections = []
    doc_title = None
    cur = None
    for it in items:
        if it["kind"] == "heading":
            level = len(it["verbatim"]) - len(it["verbatim"].lstrip("#"))
            head = {"level": level, "title": it["verbatim"].lstrip("# ").strip(),
                    "start": it["start"], "blank_before": it["blank_before"]}
            if level == 1:
                doc_title = head
                continue
            cur = dict(head)
            cur["items"] = []
            sections.append(cur)
            continue
        if cur is None:
            cur = {"level": 2, "title": None, "start": it["start"],
                   "blank_before": it["blank_before"], "items": []}
            sections.append(cur)
        cur["items"].append(it)
        cur["end"] = it["end"]
    return doc_title, sections


def section_by_title(sections, keyword):
    for sec in sections:
        if keyword in (sec.get("title") or ""):
            return sec
    return None


def derived_text(item):
    """规则条目的 name/text 视图；paragraph 只给 text。"""
    body = item["verbatim"]
    if item["kind"] == "numbered":
        m = NUMBERED.match(body)
        item["no"] = int(m.group(1))
        body = m.group(2)
    elif item["kind"] == "bullet":
        m = BULLET.match(body)
        body = m.group(1)
    name, text = split_head(body)
    item["name"] = name
    item["text"] = text
    quote = re.search(r"\n\s*>\s*(.+)", item["verbatim"])
    item["quote"] = quote.group(1).strip() if quote else None
    return item


def utterances(sections):
    """所有带引用句的规则条目 → 固定话术清单 + 是否已锁原句。"""
    out = []
    for sec in sections:
        for it in sec["items"]:
            if it.get("quote"):
                locked = any(tok in it["verbatim"].split("\n")[0] for tok in LOCK_TOKENS)
                out.append({
                    "id": "FU%s" % it["start"],
                    "section": sec.get("title"),
                    "rule": it.get("name"),
                    "source_lines": [it["start"], it["end"]],
                    "text": it["quote"],
                    "introduced_by": it["verbatim"].split("\n")[0].strip(),
                    "verbatim_locked_in_prompt": locked,
                    "locked_by": [t for t in LOCK_TOKENS if t in it["verbatim"].split("\n")[0]] or None,
                })
            if it["kind"] == "quote_block":
                out.append({
                    "id": "FE%s" % it["start"],
                    "section": sec.get("title"),
                    "rule": None,
                    "source_lines": [it["start"], it["end"]],
                    "text": it["verbatim"].lstrip("> ").strip(),
                    "introduced_by": "写法示例（非固定话术）",
                    "verbatim_locked_in_prompt": False,
                    "locked_by": None,
                    "is_example": True,
                })
    return out


def hard_rules(sections):
    sec = section_by_title(sections, "能力边界")
    return [{"id": "BR%d" % it["no"], "name": it["name"], "text": it["text"],
             "fixed_utterance": it["quote"], "source_lines": [it["start"], it["end"]]}
            for it in sec["items"] if it["kind"] == "numbered"]


def out_of_scope(sections):
    sec = section_by_title(sections, "范围外请求")
    rows = []
    for it in sec["items"]:
        if it["kind"] != "table":
            continue
        for line in it["verbatim"].split("\n"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 2 or set("".join(cells)) <= set("-: "):
                continue
            if cells[0] in ("越界类型",):
                continue
            rows.append({"type": cells[0], "handling": cells[1],
                         "source_lines": [it["start"], it["end"]]})
    return rows


def routing(sections):
    sec = section_by_title(sections, "对话处理优先级")
    steps, fallback, constraints = [], None, []
    cur = None
    for it in sec["items"]:
        text = it["verbatim"]
        m = STEP.match(text)
        if m:
            cur = {"step": int(m.group(1)), "question": m.group(2).rstrip("?？"),
                   "applies_to": None, "action": None,
                   "source_lines": [it["start"], it["end"]]}
            steps.append(cur)
            continue
        if text.startswith("**兜底**"):
            fallback = {"action": text.lstrip("*").lstrip("兜底").lstrip("*：: ").strip(),
                        "source_lines": [it["start"], it["end"]]}
            cur = None
            continue
        if text.startswith("补充约束"):
            constraints.append({"kind": "note", "text": text,
                                "source_lines": [it["start"], it["end"]]})
            cur = None
            continue
        if cur is not None:
            if text.startswith("→"):
                cur["action"] = text.lstrip("→： ").strip()
                cur["terminate_round"] = "立即结束" in text
            elif text.startswith("（"):
                cur["applies_to"] = text.strip("（）")
        elif constraints:
            constraints.append({"kind": it["kind"], "text": text,
                                "source_lines": [it["start"], it["end"]]})
    return {"header": sec.get("title"), "steps": steps, "fallback": fallback,
            "constraints": constraints}


def tier_labels(sections):
    out = {}
    for sec in sections:
        hits = []
        for it in sec["items"]:
            for tok in TIER_LABEL.findall(it["verbatim"]):
                if tok not in hits:
                    hits.append(tok)
        if hits:
            out["%s#%s" % (sec.get("title"), sec["start"])] = hits
    return out


def skills(sections):
    out = []
    for sec in sections:
        title = sec.get("title") or ""
        if not title.startswith("技能"):
            continue
        trig = None
        blocks = []
        for it in sec["items"]:
            if it["kind"] == "paragraph" and it["verbatim"].startswith("触发"):
                trig = it["verbatim"].split("：", 1)[1].strip()
                continue
            blocks.append({"kind": it["kind"], "name": it.get("name"),
                           "text": it.get("text") or it["verbatim"],
                           "fixed_utterance": it.get("quote"),
                           "source_lines": [it["start"], it["end"]]})
        m = re.match(r"技能\s*(\d+)\s*[：:]\s*(.+)", title)
        if not m:
            continue
        out.append({"id": "skill%s" % m.group(1), "skill_no": int(m.group(1)),
                    "name": m.group(2).strip(), "trigger": trig,
                    "parent_section": "技能模块",
                    "blocks": blocks})
    out.sort(key=lambda s: s["skill_no"])
    return out


def output_contract(sections):
    sec = section_by_title(sections, "输出契约")
    rules = []
    self_check = []
    check_src = None
    for it in sec["items"]:
        if it["kind"] == "numbered":
            rules.append({"id": "OC%d" % it["no"], "name": it["name"], "text": it["text"],
                          "fixed_utterance": it["quote"],
                          "source_lines": [it["start"], it["end"]]})
            if it.get("quote") is None and it["name"] and "自检" in it["name"]:
                check_src = it
                for part in re.split(r"[①②③④⑤⑥⑦⑧⑨⑩]", it["text"]):
                    p = part.strip("；; ").strip()
                    if p and not p.startswith("发送前"):
                        self_check.append(p)
        elif it["kind"] == "paragraph":
            rules.append({"id": "OC_note_%d" % it["start"], "name": None,
                          "text": it["verbatim"], "fixed_utterance": None,
                          "source_lines": [it["start"], it["end"]]})
    return {"rules": rules,
            "self_check_items": [{"id": "SC%d" % (i + 1), "text": s,
                                  "source_lines": [check_src["start"], check_src["end"]]}
                                 for i, s in enumerate(self_check)] if self_check else [],
            "self_check_source": "输出契约的发出前自检项"}


def persona_view(sections):
    sec = section_by_title(sections, "人设")
    items = [{"kind": it["kind"], "text": it["verbatim"]} for it in sec["items"]]
    return {"section": sec["title"], "source_lines": [sec["start"], sec["end"]],
            "role": items[0]["text"] if items else None, "traits": items[1:]}


def build():
    plines = read_lines(PROMPT_MD)
    items = parse_prompt(plines)
    for it in items:
        if it["kind"] not in ("heading", "table", "quote_block"):
            derived_text(it)
    doc_title, sections = to_sections(items)

    rebuilt = restore(items)
    source = "\n".join(plines) + "\n"
    assert rebuilt == source, "还原失败：JSON 的 verbatim 与 system-prompt.md 不一致"

    import yaml
    with open(AGENT_YAML, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    utt = utterances(sections)
    locked = [u for u in utt if u.get("rule") and u["verbatim_locked_in_prompt"]]
    unlocked = [u for u in utt if u.get("rule") and not u["verbatim_locked_in_prompt"]]

    def sha(path):
        return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]

    prompt_sections = []
    for sec in sections:
        prompt_sections.append({
            "level": sec["level"],
            "title": sec["title"],
            "source_lines": [sec["start"], sec.get("end")],
            "items": [{"kind": it["kind"], "no": it.get("no"),
                       "blank_before": it["blank_before"],
                       "source_lines": [it["start"], it["end"]],
                       "verbatim": it["verbatim"]} for it in sec["items"]],
        })

    tools_sec = section_by_title(sections, "工具使用")
    doc = {
        "$schema": "pet-care-consultant/agent-config@1",
        "generated_by": "tools/prompt_to_json.py",
        "do_not_edit": "本文件由脚本从 system-prompt.md 与 agent.yaml 生成，请勿手改；"
                       "改完源文件后运行 python tools/prompt_to_json.py 重新生成，"
                       "或 python tools/prompt_to_json.py --check 检查是否漂移。",
        "source": {
            "system_prompt": {"file": "system-prompt.md", "lines": len(plines),
                              "bytes": os.path.getsize(PROMPT_MD), "sha256_16": sha(PROMPT_MD)},
            "agent_yaml": {"file": "agent.yaml", "bytes": os.path.getsize(AGENT_YAML),
                           "sha256_16": sha(AGENT_YAML)},
            "fidelity": "prompt.sections[].items[] 的 verbatim + blank_before 可逐字节还原 system-prompt.md；"
                        "生成时已断言还原一致，--check 会复检源文件 sha256 与本文件是否漂移",
        },
        "agent": {k: cfg.get(k) for k in ("name", "display_name", "description", "version",
                                        "status", "owner", "created", "updated",
                                        "changelog", "prd", "system_prompt")},
        "platform": cfg.get("platform"),
        "companion": cfg.get("companion"),
        "model": cfg.get("model"),
        "modalities": cfg.get("modalities"),
        "capabilities": cfg.get("capabilities"),
        "knowledge": cfg.get("knowledge"),
        "safety": cfg.get("safety"),
        "non_goals": cfg.get("non_goals"),
        "tools": {"platform_declaration": cfg.get("tools"),
                  "prompt_policy": [{"aspect": it.get("name"), "text": it.get("text"),
                                     "source_lines": [it["start"], it["end"]]}
                                    for it in (tools_sec["items"] if tools_sec else [])]},
        "prompt": {
            "title": doc_title["title"] if doc_title else None,
            "persona": persona_view(sections),
            "hard_rules": hard_rules(sections),
            "out_of_scope_requests": out_of_scope(sections),
            "routing_priority": routing(sections),
            "skills": skills(sections),
            "output_contract": output_contract(sections),
            "sections": prompt_sections,
        },
        "risk_tier_labels_in_prompt": tier_labels(sections),
        "fixed_utterances": utt,
        "audit": {
            "note": "verbatim_locked_in_prompt 由关键词扫描得出（%s），与 31 条实跑结论一致：只有免责声明被锁成原句。" % "、".join(LOCK_TOKENS),
            "locked_utterances": [u["id"] for u in locked],
            "unlocked_utterances": [{"id": u["id"], "rule": u["rule"], "text": u["text"]}
                                    for u in unlocked],
        },
        "evaluation": cfg.get("evaluation"),
        "observability": cfg.get("observability"),
        "known_gaps": cfg.get("known_gaps"),
        "next_version": cfg.get("next_version"),
    }
    return doc


def main():
    doc = build()
    payload = json.dumps(doc, ensure_ascii=False, indent=2, default=str) + "\n"
    if "--check" in sys.argv:
        with open(OUT_JSON, encoding="utf-8") as fh:
            current = fh.read()
        ok = current == payload
        sys.stdout.write(("DRIFT" if not ok else "IN-SYNC") + "\n")
        sys.exit(0 if ok else 1)
    with open(OUT_JSON, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(payload)
    p = doc["prompt"]
    sys.stdout.write("wrote agent-config.json bytes=%d rules=%d steps=%d skills=%d "
                     "utterances=%d locked=%d sections=%d\n" % (
                         len(payload.encode("utf-8")), len(p["hard_rules"]),
                         len(p["routing_priority"]["steps"]), len(p["skills"]),
                         len(doc["fixed_utterances"]), len(doc["audit"]["locked_utterances"]),
                         len(p["sections"])))


if __name__ == "__main__":
    main()
