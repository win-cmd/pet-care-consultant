# -*- coding: utf-8 -*-
"""用真实字体度量复核简历是否落在 1 页内（不依赖 Word/LibreOffice）。"""
import sys
import docx
from PIL import ImageFont

RESUME = r"D:\新建文件夹\个人简历\邓慧婷_AI产品经理实习_简历_美化版_2026-10-30.docx"
F = r"C:\Windows\Fonts\msyh.ttc"
EMU_MM = 36000.0

d = docx.Document(RESUME)
sec = d.sections[0]
cw = (sec.page_width - sec.left_margin - sec.right_margin) / EMU_MM
usable = (sec.page_height - sec.top_margin - sec.bottom_margin) / EMU_MM

cache = {}


def font(sz):
    key = round(sz * 4)
    if key not in cache:
        cache[key] = ImageFont.truetype(F, int(round(sz * 96 / 72)))
    return cache[key]


def line_h(sz, mult):
    a, b = font(sz).getmetrics()
    return (a + b) * 25.4 / 96 * mult


def wrap(text, sz, indent_mm):
    f = font(sz)
    avail_px = (cw - indent_mm) / 25.4 * 96
    n, cur = 1, 0.0
    for ch in text:
        w = f.getlength(ch)
        if cur + w > avail_px:
            n += 1
            cur = w
        else:
            cur += w
    return n


def sz_of(p):
    return max([(r.font.size.pt if r.font.size else 9.0) for r in p.runs] or [9.0])


total = 0.0
rows = []
for p in d.paragraphs:
    t = p.text
    if not t.strip():
        continue
    sz = sz_of(p)
    pf = p.paragraph_format
    indent = (pf.left_indent or 0) / EMU_MM
    mult = pf.line_spacing if isinstance(pf.line_spacing, float) else 1.10
    n = wrap(t, sz, indent)
    before = (pf.space_before.pt if pf.space_before else 0) * 25.4 / 72
    after = (pf.space_after.pt if pf.space_after else 0) * 25.4 / 72
    h = n * line_h(sz, mult) + before + after
    total += h
    rows.append((n, sz, round(h), t[:24]))

hdr = 0.0
for p in d.tables[0].rows[0].cells[0].paragraphs:
    if not p.text.strip():
        continue
    sz = sz_of(p)
    pf = p.paragraph_format
    mult = pf.line_spacing if isinstance(pf.line_spacing, float) else 1.10
    after = (pf.space_after.pt if pf.space_after else 0) * 25.4 / 72
    hdr += wrap(p.text, sz, 0) * line_h(sz, mult) + after

cell = d.tables[0].rows[0].cells[1]
pic = cell.paragraphs[0].runs[0]._element.findall('.//' + '{http://schemas.openxmlformats.org/drawingml/2006/main}ext')
photo_h = int(pic[0].get('cy')) / 914400 * 25.4 if pic else 0

total += max(hdr, photo_h)
for n, sz, h, t in rows:
    print(f"{n}L {sz:>4}pt {h:>3}mm  {t}")
print(f"header_text={hdr:.0f}mm photo={photo_h:.0f}mm")
print(f"TOTAL={total:.0f}mm  usable={usable:.0f}mm  slack={usable-total:+.0f}mm  -> {'1 页 OK' if total <= usable else '溢出'}")
