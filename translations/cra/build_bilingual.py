#!/usr/bin/env python3
"""Build bilingual (EN/ZH) PDFs of Commission document C(2026) 5252.

English text is taken from the source PDF. Chinese text is a parallel
translation and is not part of the Commission original.
"""

from __future__ import annotations

import html
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BLOCKS_PATH = Path("/tmp/annex_merged.json")
FIG_DIR = ROOT / "figures"
OUT_DIR = Path("/workspace/output")
ARTIFACT_DIR = Path("/opt/cursor/artifacts")

MERGE_INTO_PREV = {"b080", "b163", "b270", "b278"}


def load_translations() -> dict[str, str]:
    zh: dict[str, str] = {}
    for path in sorted((ROOT / "zh").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        overlap = set(zh) & set(data)
        if overlap:
            raise SystemExit(f"duplicate translation ids in {path.name}: {sorted(overlap)[:5]}")
        zh.update(data)
    return zh


def prepare_blocks() -> list[dict]:
    blocks = json.loads(BLOCKS_PATH.read_text(encoding="utf-8"))
    prepared: list[dict] = []
    for block in blocks:
        if block["id"] in MERGE_INTO_PREV and prepared:
            prepared[-1]["text"] = prepared[-1]["text"].rstrip() + " " + block["text"].strip()
            prepared[-1]["kind"] = "h3"
            continue
        text = block["text"]
        text = text.replace("open- source", "open-source")
        text = text.replace("thirdparty", "third-party")
        text = text.replace(
            "taking place ELI: http://data.europa.eu/eli/reg_impl/2024/2690/oj. close",
            "taking place close",
        )
        if block["id"] == "b266" and "18.10.2024 ELI:" in text:
            text = text.replace("18.10.2024 ELI:", "18.10.2024, ELI:")
        item = dict(block)
        item["text"] = text
        prepared.append(item)
    return prepared


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def figure_number(text: str) -> int | None:
    match = re.match(r"Figure\s+(\d+)\s*:", text)
    if not match:
        return None
    return int(match.group(1))


CSS = r"""
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Liberation Serif", "Times New Roman", serif;
  font-size: 10.5pt;
  line-height: 1.45;
  color: #1a1a1a;
}
.cover { page-break-after: always; padding-top: 18mm; }
.kicker {
  font-family: "WenQuanYi Micro Hei", "Droid Sans Fallback", sans-serif;
  font-size: 11pt;
  letter-spacing: 0.04em;
}
h1, h2, h3 {
  font-family: "WenQuanYi Micro Hei", "Droid Sans Fallback", sans-serif;
  line-height: 1.35;
  page-break-after: avoid;
}
h1 { font-size: 16pt; margin: 16pt 0 8pt; border-bottom: 1.5pt solid #1a365d; padding-bottom: 3pt; }
h2 { font-size: 13pt; margin: 14pt 0 6pt; color: #1a365d; }
h3 { font-size: 11.5pt; margin: 12pt 0 6pt; color: #234e70; }
.en-h { font-family: "Liberation Serif", "Times New Roman", serif; font-weight: 700; }
.zh-h { display: block; font-weight: 700; margin-top: 2pt; }
.note {
  font-family: "WenQuanYi Micro Hei", "Droid Sans Fallback", sans-serif;
  font-size: 9.5pt;
  background: #f7f4ea;
  border: 1pt solid #e2d3a2;
  padding: 8pt 10pt;
  margin: 10pt 0 14pt;
}
.pair { margin: 0 0 9pt; page-break-inside: auto; }
.pair .en { margin: 0; }
.pair .zh {
  font-family: "WenQuanYi Micro Hei", "Droid Sans Fallback", sans-serif;
  background: #f3f7fb;
  border-left: 2.5pt solid #2b6cb0;
  margin: 3pt 0 0;
  padding: 4pt 8pt 5pt;
}
.num { font-weight: 700; }
.fn { font-size: 9pt; margin: 4pt 0 8pt; }
.fn .zh { font-size: 9pt; }
.caption { font-size: 9.5pt; font-style: italic; }
.figure { margin: 8pt 0 12pt; page-break-inside: auto; }
.figure img { width: 100%; height: auto; border: 0.5pt solid #d0d7de; }
.fig-note {
  font-family: "WenQuanYi Micro Hei", "Droid Sans Fallback", sans-serif;
  font-size: 9pt;
  margin-top: 4pt;
}
.fig-note table { width: 100%; border-collapse: collapse; }
.fig-note td { vertical-align: top; border-top: 0.4pt solid #e5e7eb; padding: 2pt 4pt; width: 50%; }
.toc { font-family: "WenQuanYi Micro Hei", "Droid Sans Fallback", sans-serif; font-size: 10pt; }
.toc div { margin: 2pt 0; }
.toc .l2 { margin-left: 12pt; }
.toc .l3 { margin-left: 24pt; }
.small { font-size: 9pt; color: #444; }
"""


def pair(en: str, zh: str, kind: str) -> str:
    css = "fn" if kind == "fn" else "pair"
    if kind == "fn":
        css = "pair fn"
    return (
        f'<div class="{css}">'
        f'<p class="en">{esc(en)}</p>'
        f'<p class="zh">{esc(zh)}</p>'
        f"</div>"
    )


def heading(level: str, en: str, zh: str) -> str:
    tag = {"h1": "h1", "h2": "h2", "h3": "h3"}[level]
    return (
        f"<{tag}><span class=\"en-h\">{esc(en)}</span>"
        f"<span class=\"zh-h\">{esc(zh)}</span></{tag}>"
    )


def figure_block(number: int, notes: dict[int, list[tuple[str, str]]]) -> str:
    image = FIG_DIR / f"figure_{number}.png"
    if not image.exists():
        return ""
    rows = notes.get(number, [])
    body = ""
    if rows:
        trs = []
        for en, zh in rows:
            trs.append(f"<tr><td>{esc(en)}</td><td>{esc(zh)}</td></tr>")
        body = (
            '<div class="fig-note"><p>图中文字对照（只译图内已有文字，不增补说明）</p><table>'
            + "".join(trs)
            + "</table></div>"
        )
    src = image.resolve().as_uri()
    return f'<div class="figure"><img src="{src}" alt="Figure {number}" />{body}</div>'


def render(title_en: str, title_zh: str, blocks_html: str, toc_html: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>{esc(title_zh)}</title>
<style>{CSS}</style>
</head>
<body>
<section class="cover">
<p class="kicker">EUROPEAN COMMISSION<br />欧盟委员会</p>
<p class="kicker">Brussels, 27.7.2026　布鲁塞尔，2026年7月27日<br />C(2026) 5252 final</p>
<h1><span class="en-h">{esc(title_en)}</span><span class="zh-h">{esc(title_zh)}</span></h1>
<div class="note">
<p><b>译本说明（不属于委员会原文）</b></p>
<p>本文件是欧盟委员会文件 C(2026) 5252 的中英对照译本。英文按原文照录；中文是对照译文，不增加、不删去原文的实质内容。条例编号、日期、网址与原文保持一致。图示保留原图，图下只列出图内已有文字的中文对照。本译本不具有委员会文件的法律效力；对《网络弹性法案》的权威解释只能由欧洲联盟法院作出。</p>
<p class="small">Translator's note, not part of the Commission text. English follows the source. Chinese is a parallel translation and does not add or remove substantive content.</p>
</div>
{toc_html}
</section>
{blocks_html}
</body>
</html>
"""


def chrome_pdf(html_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    profile = Path(f"/tmp/chrome-pdf-{pdf_path.stem}")
    cmd = [
        "google-chrome",
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--no-first-run",
        "--no-pdf-header-footer",
        "--virtual-time-budget=120000",
        f"--user-data-dir={profile}",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    except subprocess.TimeoutExpired:
        if not pdf_path.exists() or pdf_path.stat().st_size < 1000:
            raise
        # Headless Chrome writes the PDF and then sometimes does not exit.


def heading_level(text: str) -> str:
    match = re.match(r"^(\d+(?:\.\d+)*)\s", text)
    if not match:
        return "h2"
    depth = match.group(1).count(".")
    if depth <= 0:
        return "h1"
    if depth == 1:
        return "h2"
    return "h3"


def blocks_to_html(blocks: list[dict], zh: dict[str, str]) -> str:
    parts: list[str] = []
    for block in blocks:
        kind = block["kind"]
        en = block["text"]
        chinese = zh[block["id"]]
        if kind == "heading":
            parts.append(heading(heading_level(en), en, chinese))
            continue
        if kind == "figure":
            number = figure_number(en)
            parts.append(pair(en, chinese, "caption"))
            if number is not None:
                parts.append(figure_block(number, FIGURE_NOTES))
            continue
        css_kind = "fn" if kind == "fn" else "pair"
        parts.append(pair(en, chinese, css_kind))
    return "\n".join(parts)


def toc_html(blocks: list[dict], zh: dict[str, str]) -> str:
    rows = ['<div class="toc"><h2><span class="en-h">Contents</span><span class="zh-h">目录</span></h2>']
    for block in blocks:
        if block["kind"] != "heading":
            continue
        level = heading_level(block["text"])
        css = {"h1": "", "h2": "l2", "h3": "l3"}[level]
        rows.append(
            f'<div class="{css}">{esc(block["text"])}<br />{esc(zh[block["id"]])}</div>'
        )
    rows.append("</div>")
    return "\n".join(rows)


def load_annex_blocks() -> list[dict]:
    from extract_annex import extract

    blocks = extract()
    for block in blocks:
        block["text"] = block["text"].replace("thirdparty", "third-party")
    return blocks


def assign_ids(blocks: list[dict], zh: dict[str, str]) -> None:
    ids = [key for key in zh if re.fullmatch(r"b\d{3}", key)]
    ids.sort()
    if len(ids) != len(blocks):
        raise SystemExit(f"block count {len(blocks)} != translation count {len(ids)}")
    for block, key in zip(blocks, ids):
        block["id"] = key


def build_annex(zh: dict[str, str]) -> Path:
    blocks = load_annex_blocks()
    assign_ids(blocks, zh)
    html_path = ROOT / "build" / "annex.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    document = render(
        "ANNEX — Commission guidance on the application of Regulation (EU) 2024/2847 (Cyber Resilience Act)",
        "附件 — 委员会关于适用条例(EU) 2024/2847（《网络弹性法案》）的指南",
        blocks_to_html(blocks, zh),
        toc_html(blocks, zh),
    )
    html_path.write_text(document, encoding="utf-8")
    pdf_path = OUT_DIR / "C_2026_5252_annex_guidance_ZH-EN.pdf"
    chrome_pdf(html_path, pdf_path)
    return pdf_path


def build_communication(zh: dict[str, str]) -> Path:
    pairs = [
        ("COMMUNICATION TO THE COMMISSION", zh["c_h"], "h1"),
        (
            "Approval of the content of the draft Communication from the Commission - "
            "Commission guidance on the application of Regulation (EU) 2024/2847 (Cyber Resilience Act)",
            zh["c_title"],
            "h2",
        ),
        (
            "Regulation (EU) 2024/2847 of the European Parliament and of the Council of 23 October 2024 "
            "on horizontal cybersecurity requirements for products with digital elements and amending "
            "Regulations (EU) No 168/2013 and (EU) 2019/1020 and Directive (EU) 2020/1828 (the ‘Cyber "
            "Resilience Act’ or ‘CRA’) entered into force on 10 December 2024.",
            zh["c_p1"],
            "p",
        ),
        (
            "Chapter IV of the CRA applies from 11 June 2026. Reporting obligations laid down in Article "
            "14 apply from 11 September 2026. The Regulation applies in its entirety from 11 December 2027.",
            zh["c_p2"],
            "p",
        ),
        (
            "Article 26 requires the Commission to publish guidance that will assist economic operators in "
            "applying the CRA, with a particular focus on facilitating compliance by microenterprises and "
            "small and medium-sized enterprises.",
            zh["c_p3"],
            "p",
        ),
        (
            "It is therefore important that economic operators are provided with timely guidance, to assist "
            "their preparations towards compliance with the CRA.",
            zh["c_p4"],
            "p",
        ),
        (
            "Given the rules’ imminent entry into application and the time needed to translate the guidance "
            "into all EU official languages, the Commission is called upon to approve the content of the "
            "draft Communication to the Commission on guidance on the application of Regulation (EU) "
            "2024/2847 (Cyber Resilience Act).",
            zh["c_p5"],
            "p",
        ),
        (
            "The guidance in the Annex to the Communication will be formally adopted by the Commission "
            "at a later date, when all language versions are available. It is only from that moment that it will "
            "apply.",
            zh["c_p6"],
            "p",
        ),
        (
            "The draft guidance is enclosed as an annex to this Communication.",
            zh["c_p7"],
            "p",
        ),
    ]
    body = []
    for en, chinese, kind in pairs:
        if kind in {"h1", "h2"}:
            body.append(heading(kind, en, chinese))
        else:
            body.append(pair(en, chinese, "pair"))
    html_path = ROOT / "build" / "communication.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    document = render(
        "COMMUNICATION TO THE COMMISSION",
        zh["c_h"],
        "\n".join(body),
    )
    html_path.write_text(document, encoding="utf-8")
    pdf_path = OUT_DIR / "C_2026_5252_communication_ZH-EN.pdf"
    chrome_pdf(html_path, pdf_path)
    return pdf_path


FIGURE_NOTES: dict[int, list[tuple[str, str]]] = {
    1: [
        ("Start", "开始"),
        ("Is the FOSS a product with digital elements?", "该自由及开源软件是否为含数字元素产品？"),
        ("Are you responsible for publishing the FOSS?", "你是否负责发布该自由及开源软件？"),
        ("Are you placing it on the market in the course of a commercial activity?", "你是否在商业活动过程中将其投放市场？"),
        ("Are you a legal person (i.e. not a natural person)?", "你是否为法人（即不是自然人）？"),
        ("Is the FOSS intended for commercial activities?", "该自由及开源软件是否旨在用于商业活动？"),
        ("Do you systematically provide support for that FOSS?", "你是否系统性地为该自由及开源软件提供支持？"),
        ("Are you a not-for-profit organisation?", "你是否为非营利组织？"),
        ("Manufacturer", "制造商"),
        ("Outside of CRA scope", "不属于CRA适用范围"),
        ("Open-source software steward", "开源软件管理者"),
        ("Yes / No", "是 / 否"),
        ("Not a product: for example, documentation, sample code, training material, research projects", "不属于产品：例如文件、示例代码、培训材料、研究项目"),
        ("For example, charging price; monetising other services through that FOSS; monetising from processing of personal data; bundling with support services exceeding cost recuperation; accepting donations with intention to profit", "例如：收取价款；通过该自由及开源软件变现其他服务；通过处理个人数据变现；与超出成本回收的支持服务捆绑；接受捐赠且具有营利意图"),
        ("Not-for-profit organisation set up in such a way that ensures that all earnings after costs are used to achieve not-for-profit objectives", "以确保扣除成本后的全部收益用于实现非营利目的的方式设立的非营利组织"),
    ],
    2: [
        ("Determines conformity assessment (CA) procedure", "决定合格评定（CA）程序"),
        ("Core functionality of an operating system", "操作系统的核心功能"),
        ("Ancillary functionality 1 (calculator)", "辅助功能1（计算器）"),
        ("Ancillary functionality 2 (graphics editor)", "辅助功能2（图形编辑器）"),
        ("Ancillary functionality 3 (browser)", "辅助功能3（浏览器）"),
        ("Legend", "图例"),
        ("Core functionality of important or critical product category", "重要或关键产品类别的核心功能"),
        ("Ancillary functionality", "辅助功能"),
    ],
    3: [
        ("Core functionality of important or critical product category", "重要或关键产品类别的核心功能"),
        ("Core functionality of a specific product", "某一具体产品的核心功能"),
        ("Not an important or critical product, because core functionality exceeds the definition of the product category", "不是重要或关键产品，因为核心功能超出该产品类别的定义"),
        ("Example: The core functionality of Security orchestration, automation and response (SOAR) includes incident response, which is not part of the core functionality of a SIEM.", "示例：安全编排、自动化与响应（SOAR）的核心功能包括事件响应，而事件响应不属于安全信息与事件管理（SIEM）的核心功能。"),
        ("Legend: core functionality of important or critical product category; core functionality falling short of/exceeding that of an important or critical product category", "图例：重要或关键产品类别的核心功能；未达到或超出重要或关键产品类别的核心功能"),
    ],
    4: [
        ("Core functionality of important or critical product category", "重要或关键产品类别的核心功能"),
        ("Core functionality of a specific product", "某一具体产品的核心功能"),
        ("Not an important or critical product, because core functionality falls short of the definition", "不是重要或关键产品，因为核心功能未达到该定义"),
        ("Example: a log collection tool performs some functions of a SIEM, but lacks the ability to correlate data and generate actionable security insights.", "示例：日志收集工具履行SIEM的部分功能，但不具备关联数据并生成可据以采取行动的安全洞见的能力。"),
    ],
    5: [
        ("Determines conformity assessment (CA) procedure", "决定合格评定（CA）程序"),
        ("Core functionality of important or critical product category", "重要或关键产品类别的核心功能"),
        ("Core functionality of a specific product", "某一具体产品的核心功能"),
        ("Ancillary functionality 1 (calculator)", "辅助功能1（计算器）"),
        ("Ancillary functionality 2 (graphics editor)", "辅助功能2（图形编辑器）"),
        ("Ancillary functionality 3 (text editor)", "辅助功能3（文本编辑器）"),
        ("If not equal, then default category", "如果不相等，则为默认类别"),
        ("If equal, then important or critical", "如果相等，则为重要或关键"),
        ("Ancillary functionality", "辅助功能"),
    ],
    6: [
        ("Determines conformity assessment (CA) procedure", "决定合格评定（CA）程序"),
        ("Core functionality of software that searches for, removes, or quarantines malicious software", "搜索、清除或隔离恶意软件的软件的核心功能"),
        ("Ancillary functionality 1 (disk-cleaning)", "辅助功能1（磁盘清理）"),
        ("Ancillary functionality 2 (anti-tracking)", "辅助功能2（反跟踪）"),
        ("No hEN", "无协调标准（hEN）"),
        ("Available cited harmonised standard (hEN)", "已有被引用的协调标准（hEN）"),
        ("Functionality covered by hEN", "协调标准所涵盖的功能"),
    ],
    7: [
        ("No hEN (no PoC)", "无协调标准（无符合性推定）"),
        ("Available cited harmonised standard (hEN)", "已有被引用的协调标准（hEN）"),
        ("PoC for core functionality", "对核心功能的符合性推定"),
        ("Ancillary functionality 1 (disk-cleaning)", "辅助功能1（磁盘清理）"),
        ("Ancillary functionality 2 (anti-tracking)", "辅助功能2（反跟踪）"),
    ],
    8: [
        ("hEN (PoC)", "协调标准（符合性推定）"),
        ("No hEN (no PoC)", "无协调标准（无符合性推定）"),
        ("PoC for core functionality", "对核心功能的符合性推定"),
        ("Ancillary functionality 1 (disk-cleaning)", "辅助功能1（磁盘清理）"),
        ("Ancillary functionality 2 (anti-tracking)", "辅助功能2（反跟踪）"),
    ],
    9: [
        ("Start", "开始"),
        ("Is any part of the product’s data processing happening at a distance?", "该产品的数据处理是否有任何部分在远程进行？"),
        ("Not CRA RDPS", "不属于CRA意义上的远程数据处理解决方案"),
        ("Any relevant risks still to be included in risk assessment", "任何相关风险仍须纳入风险评估"),
        ("Is such remote data processing necessary for a function of the product?", "此类远程数据处理是否为该产品的某一功能所必需？"),
        ("Treat as external dependency", "作为外部依赖项对待"),
        ("Risks stemming from this dependency must be included in the risk assessment and mitigated through product-level controls", "源于该依赖项的风险必须纳入风险评估，并通过产品层面的控制加以缓解"),
        ("Is such remote data processing developed under your responsibility?", "此类远程数据处理是否在你的责任下开发？"),
        ("Treat as component", "作为组件对待"),
        ("Risks stemming from integration of this component must be included in the risk assessment and mitigated through product-level controls; due diligence should also be carried out to support risk mitigation", "源于集成该组件的风险必须纳入风险评估，并通过产品层面的控制加以缓解；还应当开展尽职调查以支持风险缓解"),
        ("CRA RDPS", "CRA意义上的远程数据处理解决方案"),
        ("Include in the cybersecurity risk assessment and ensure implementation of the essential cybersecurity requirements for the product as a whole", "纳入网络安全风险评估，并确保对作为整体的产品实施基本网络安全要求"),
        ("Yes / No", "是 / 否"),
    ],
    10: [
        ("The product: a banking app", "产品：银行应用程序"),
        ("The app itself, installed on the device", "应用程序本身，安装在设备上"),
        ("I want to make a payment", "我要进行付款"),
        ("The RDPS authenticating the customer and initiating the payment (banking interface)", "认证客户并发起付款的远程数据处理解决方案（银行接口）"),
        ("Bank’s environment:", "银行的环境："),
        ("Account management and ledger", "账户管理与分类账"),
        ("Records transaction and sends back output", "记录交易并返回输出"),
        ("The data centre where services are hosted", "托管服务的数据中心"),
        ("Authenticate, check balance, initiate transfer", "认证、查询余额、发起转账"),
        ("Transfer executed and send updated balance", "转账已执行并发送更新后的余额"),
        ("Mitigations on your product", "在你的产品上采取的缓解措施"),
        ("Risks for the product", "对该产品的风险"),
        ("Example: Strong authentication of input, verification of responses, graceful degradation", "示例：对输入进行强认证、核验响应、平稳降级"),
        ("Example: If bank’s environment fails or is compromised", "示例：如果银行环境发生故障或遭到破坏"),
    ],
}


def main() -> None:
    zh = load_translations()
    communication = build_communication(zh)
    annex = build_annex(zh)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    for pdf in (communication, annex):
        target = ARTIFACT_DIR / pdf.name
        target.write_bytes(pdf.read_bytes())
        print(pdf, pdf.stat().st_size)


if __name__ == "__main__":
    main()
