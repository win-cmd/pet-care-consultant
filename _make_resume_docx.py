# -*- coding: utf-8 -*-
"""生成 AI 产品经理简历（单栏精修 / 严格 1 页 / 跨行用可迁移能力承接）。
输出到她的简历目录，不覆盖正在被 Word 占用的原文件。
"""
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_TAB_ALIGNMENT, WD_LINE_SPACING
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

OUT = r"D:\新建文件夹\个人简历\邓慧婷_AI产品经理实习_简历_美化版_2026-10-30.docx"
PHOTO = r"D:\新建文件夹\个人简历\52ab29e50231ebfc11fe7ef859c45689.jpg"
PHOTO_W_CM = 2.0

INK = RGBColor(0x1A, 0x1A, 0x1A)
ACCENT = RGBColor(0x1F, 0x5F, 0x4B)
MUTED = RGBColor(0x59, 0x59, 0x59)
FONT = "微软雅黑"
CONTENT_W = Cm(18.2)
BODY, TITLE, HEAD = 9.5, 10.0, 11.0
LINE = 1.10


def set_font(run, size, bold=False, color=INK):
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for k in ("w:eastAsia", "w:ascii", "w:hAnsi"):
        rfonts.set(qn(k), FONT)


def spacing(p, before=0, after=1.5, line=LINE):
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = line


def bottom_rule(p):
    ppr = p._element.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    edge = OxmlElement("w:bottom")
    for k, v in (("w:val", "single"), ("w:sz", "6"), ("w:space", "2"), ("w:color", "1F5F4B")):
        edge.set(qn(k), v)
    pbdr.append(edge)
    ppr.append(pbdr)


def heading(doc, text):
    p = doc.add_paragraph()
    set_font(p.add_run(text), HEAD, True, ACCENT)
    spacing(p, before=5, after=2.5)
    bottom_rule(p)
    return p


def entry(doc, left, right, desc=None):
    """标题行（可带同行描述）＋ 右对齐日期。"""
    p = doc.add_paragraph()
    p.paragraph_format.tab_stops.add_tab_stop(CONTENT_W, WD_TAB_ALIGNMENT.RIGHT)
    set_font(p.add_run(left), TITLE, True, INK)
    if desc:
        set_font(p.add_run(desc), BODY, False, INK)
    if right:
        set_font(p.add_run("\t" + right), 8.5, False, MUTED)
    spacing(p, before=1, after=1)
    return p


def bullet(doc, text, lead=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Cm(0.40)
    pf.first_line_indent = Cm(-0.40)
    set_font(p.add_run("• "), BODY, False, ACCENT)
    if lead:
        set_font(p.add_run(lead), BODY, True, INK)
    set_font(p.add_run(text), BODY, False, INK)
    spacing(p, after=1.2)
    return p


def plain(doc, text, size=BODY, color=INK, bold=False, after=1.2):
    p = doc.add_paragraph()
    set_font(p.add_run(text), size, bold, color)
    spacing(p, after=after)
    return p


doc = Document()
st = doc.styles["Normal"]
st.font.name = FONT
st.font.size = Pt(BODY)
st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(1.4)
sec.top_margin, sec.bottom_margin = Cm(1.0), Cm(0.8)

# ---------- 抬头 ----------
tbl = doc.add_table(rows=1, cols=2)
tbl.autofit = False
tbl.columns[0].width = Cm(15.1)
tbl.columns[1].width = Cm(3.1)
c0, c1 = tbl.rows[0].cells
c0.width, c1.width = Cm(15.1), Cm(3.1)

p = c0.paragraphs[0]
set_font(p.add_run("邓慧婷"), 16, True, INK)
set_font(p.add_run("　求职意向：AI 产品经理（实习）"), 10.5, True, ACCENT)
spacing(p, after=2)

p = c0.add_paragraph()
set_font(p.add_run("上海｜17374502316｜17374502316@163.com｜2001.02｜湖南怀化｜共青团员｜湖南农业大学 硕士（2026 届）"),
         8.5, False, MUTED)
spacing(p, after=2.5)

p = c0.add_paragraph()
set_font(p.add_run("跨行承接："), BODY, True, ACCENT)
set_font(p.add_run("数万份作业逐份评分 → 评测口径与判分留痕｜工程品控 → 验收标准与整改闭环｜"
                   "XGBoost-SHAP 可解释建模 → 判断模型能力边界｜设计主创 → 需求调研与方案落地"), BODY, False, INK)
spacing(p, after=0)

c1.vertical_alignment = WD_ALIGN_VERTICAL.TOP
pp = c1.paragraphs[0]
pp.alignment = 2
pp.add_run().add_picture(PHOTO, width=Cm(PHOTO_W_CM))
spacing(pp, after=0)

# ---------- 教育经历（荣誉与论文并进来，省一个独立小节） ----------
heading(doc, "教育经历")
entry(doc, "湖南农业大学｜风景园林 硕士｜全日制", "2023.09 – 2026.06")
bullet(doc, "国家奖学金（2025.10）｜湖南省研究生创新设计大赛一等奖（2024.12）｜湖南省风景园林学科竞赛一等奖。", lead="荣誉　")
bullet(doc, "共同作者 3 篇：《环境科学》（EI）、《应用生态学报》《长江流域资源与环境》（均 CSCD／北大核心）。", lead="论文　")

# ---------- 项目经历 ----------
heading(doc, "项目经历")
entry(doc, "养宠顾问智能体 · 0→1 产品设计与评测（个人项目 · 独立跨行自学）", "2026.10 – 至今")
plain(doc, "面向新手宠物主人的 7×24 喂养咨询智能体，只讲科学共识、不越界到诊断与用药；部署于 Trae（DeepSeek-V4.1-Flash）。",
      8.5, MUTED, after=1.5)

bullet(doc, "PRD 定 8 条安全红线（不确诊、不开药、不推剂量），落成 189 行系统提示词：5 步优先级判断、四档风险标签、10 项发前自检、敏感话术逐字锁定；"
             "提示词 10,210 字符超 Trae 智能体字段 10,000 字符上限后，改用一条启动提示词让 Agent 现场加载规则文件。",
       lead="产品定义与提示词工程　")

bullet(doc, "自建 31 条结构化用例（开跑前预写验收点，含 5 道诱导越界对抗题），回答原文逐字存档 18 份；"
             "五轮迭代严格通过率 80.6% → 100%、红线 0 违例、4 道急症题最新版重跑全部召回，全程只改提示词不放宽考卷标准；"
             "定位修复 6 类提示词缺陷（2 类是上一轮修法自己引入的新漏洞），实证区分 3 类平台问题与模型问题。",
       lead="评测体系与根因归因　")

bullet(doc, "推动研发落地 9 文件／890 行零依赖展示层（SVG＋CSS 猫狗动画、WebAudio 叫声，无第三方素材与 API Key），"
             "链路为 Agent 每轮一条 CLI → 本机服务 → SSE 推浏览器；我负责需求与验收标准，并与研发约定安全边界"
             "（只绑本机、Origin 校验、状态白名单、防注入渲染）。5 项自动化测试与浏览器 DOM 验收通过，"
             "2026-10-30 本机 Trae 端到端实跑通过（服务端 eventId 0→15）；高危食物仅作风险示意，不作死亡诊断。",
       lead="本地动态宠物联动（与研发协同实现）　")

bullet(doc, "交付 ZIP 包 62 文件，一条启动提示词即可在 Trae 打开使用；"
             "未完成项写成上线门槛：医疗用例未在 v2.0.0 重跑、联动未逐轮核对、听觉未验收、清单待执业兽医签字、无真实用户。",
       lead="交付物与诚实边界　")

entry(doc, "长株潭都市圈生态系统服务供需匹配研究｜研究者　", "2024.03 – 2026.05",
      desc="Python＋GeoXGBoost＋SHAP 归因建模，InVEST 与空间自相关处理上千条样本。")
entry(doc, "吉首市\"和美\"湘村设计｜主设计师　", "2024.04 – 2024.11",
      desc="居民意愿调研 → 省级专家评审 → 施工整改落地。")

# ---------- 实习 / 工作经历 ----------
heading(doc, "实习 / 工作经历")
entry(doc, "龙湖集团｜品控管理（上海）", "2026.07 – 2026.10")
bullet(doc, "负责生态景观落地品质核查，建立甲方视角的交付标准；对接现场与技术端跟进整改，形成\"标准→核查→整改→复验\"闭环。")
entry(doc, "深圳点猫科技有限公司｜儿童编程课助教（线上）", "2020.09 – 2025.03")
bullet(doc, "按课程标准逐份核查与评分数万份学员作业，输出易错点清单反哺课程优化。")

# ---------- 专业技能 ----------
heading(doc, "专业技能")
bullet(doc, "需求拆解与优先级、PRD 撰写、评测集与验收标准设计、上线门槛与风险红线定义、缺陷根因归因、与研发协同评审技术方案。", lead="产品能力　")
bullet(doc, "结构化提示词设计（优先级状态机、话术逐字锁定、发前自检项）、提示词注入与越界防护、Agent 平台实跑与人工判分（Trae／Qoder）；"
             "了解 RAG／知识库外挂与微调的适用边界（本项目未实现）。", lead="AI 能力　")
bullet(doc, "Python（geopandas／XGBoost／SHAP）、ArcGIS、InVEST、SPSS、Excel。", lead="数据与工具　")

doc.save(OUT)
print("OUT", OUT)
