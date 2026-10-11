#!/usr/bin/env python3
"""Extract annex paragraphs in an order that matches the translation blocks."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf

PDF = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/"
    "C_2026_5252_1_EN_annexe_acte_autonome_cp_part1_v3_kXuCPwXXxAuG8Uj44Ar0o2Vros_131456_8718.pdf"
)
OUT = Path("/tmp/cra_work/annex_blocks.json")

PARA_START = re.compile(r"^(\d+)\.\s+\S")
EXAMPLE_START = re.compile(r"^Example\s+\d+\s*:")
FIGURE_START = re.compile(r"^Figure\s+\d+\s*:")
FN_START = re.compile(r"^(\d+)\s+\S")
HEADING_START = re.compile(r"^\d+(?:\.\d+)*\s+\S")


def join_parts(parts: list[str]) -> str:
    text = ""
    for part in parts:
        part = re.sub(r"\s+", " ", part).strip()
        if not part:
            continue
        if not text:
            text = part
            continue
        if text.endswith("-") and part[:1].islower():
            text += part
        else:
            text += " " + part
    text = re.sub(r" +", " ", text).strip()
    return text


def visual_lines(page: pymupdf.Page) -> list[dict]:
    raw: list[dict] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            spans = line["spans"]
            text = "".join(span["text"] for span in spans).strip()
            if not text:
                continue
            y0 = line["bbox"][1]
            if y0 < 55 or y0 > 770:
                continue
            raw.append(
                {
                    "x": line["bbox"][0],
                    "y": y0,
                    "size": spans[0]["size"],
                    "font": spans[0]["font"],
                    "text": text,
                }
            )
    raw.sort(key=lambda row: (row["y"], row["x"]))
    grouped: list[dict] = []
    for row in raw:
        if grouped and abs(row["y"] - grouped[-1]["y"]) < 1.6:
            grouped[-1]["parts"].append(row)
            grouped[-1]["size"] = max(grouped[-1]["size"], row["size"])
        else:
            grouped.append({"y": row["y"], "x": row["x"], "size": row["size"], "font": row["font"], "parts": [row]})
    lines = []
    for group in grouped:
        parts = sorted(group["parts"], key=lambda part: part["x"])
        text = join_parts([part["text"] for part in parts])
        fonts = {part["font"] for part in parts}
        lines.append(
            {
                "x": min(part["x"] for part in parts),
                "y": group["y"],
                "size": group["size"],
                "font": parts[0]["font"],
                "fonts": fonts,
                "text": text,
            }
        )
    return lines


def is_footnote(line: dict) -> bool:
    if FIGURE_START.match(line["text"]):
        return False
    if abs(line["size"] - 9) < 0.3 and "Italic" in line["font"]:
        return False
    # Footnote markers are 6 pt; wrapped footnote lines are 10 pt at the left margin.
    if line["size"] <= 6.2:
        return True
    if line["size"] <= 10.2 and line["x"] < 100:
        return True
    return False


def is_heading(line: dict) -> bool:
    if line["size"] < 13.5:
        return False
    if "Display" not in line["font"] and abs(line["size"] - 14) > 0.3:
        return False
    return True


def heading_continues(line: dict) -> bool:
    return is_heading(line) and not HEADING_START.match(line["text"])


def extract() -> list[dict]:
    doc = pymupdf.open(PDF)
    blocks: list[dict] = []
    current: dict | None = None
    page_notes: dict[int, list[str]] = {}

    def flush() -> None:
        nonlocal current
        if current is None:
            return
        current["text"] = join_parts(current.pop("parts"))
        if current["text"]:
            blocks.append(current)
        current = None

    def ensure(kind: str, page: int, first: str | None = None) -> None:
        nonlocal current
        flush()
        current = {"kind": kind, "start_page": page, "pages": [page], "parts": []}
        if first:
            current["parts"].append(first)

    for page_index in range(4, doc.page_count):
        page_no = page_index + 1
        notes: list[str] = []
        note_parts: list[str] | None = None
        for line in visual_lines(doc[page_index]):
            text = line["text"]
            if is_footnote(line):
                if FN_START.match(text) and line["size"] <= 6.2:
                    if note_parts:
                        notes.append(join_parts(note_parts))
                    note_parts = [text]
                elif note_parts is not None:
                    note_parts.append(text)
                else:
                    note_parts = [text]
                continue
            if note_parts:
                notes.append(join_parts(note_parts))
                note_parts = None

            if is_heading(line):
                if current and current["kind"] == "heading" and heading_continues(line):
                    current["parts"].append(text)
                    if page_no not in current["pages"]:
                        current["pages"].append(page_no)
                    continue
                ensure("heading", page_no, text)
                continue

            if PARA_START.match(text) and line["x"] < 115 and line["size"] > 10.5:
                number = PARA_START.match(text).group(1)
                ensure("para", page_no, text)
                current["num"] = int(number)
                continue

            if EXAMPLE_START.match(text):
                ensure("example", page_no, text)
                continue

            if FIGURE_START.match(text):
                ensure("figure", page_no, text)
                continue

            if text == "•" or text.startswith("• "):
                ensure("bullet", page_no, text)
                current["last_y"] = line["y"]
                continue

            if current and current["kind"] == "figure" and line["size"] <= 10:
                current["parts"].append(text)
                current["last_y"] = line["y"]
                if page_no not in current["pages"]:
                    current["pages"].append(page_no)
                continue

            if current and current["kind"] == "heading":
                ensure("body", page_no, text)
                current["last_y"] = line["y"]
                continue

            if current and current["kind"] == "figure":
                ensure("body", page_no, text)
                current["last_y"] = line["y"]
                continue

            if current is None:
                ensure("body", page_no, text)
                current["last_y"] = line["y"]
                continue

            # A full-width line ends a bullet list and starts body text.
            if current["kind"] == "bullet" and line["x"] < 85:
                ensure("body", page_no, text)
                current["last_y"] = line["y"]
                continue

            # Unnumbered prose is split where the source leaves a paragraph gap.
            same_page = page_no == current["pages"][-1]
            if (
                current["kind"] == "body"
                and line["x"] < 85
                and same_page
                and line["y"] - current.get("last_y", line["y"]) > 20
            ):
                ensure("body", page_no, text)
                current["last_y"] = line["y"]
                continue

            current["parts"].append(text)
            current["last_y"] = line["y"]
            if page_no not in current["pages"]:
                current["pages"].append(page_no)

        if note_parts:
            notes.append(join_parts(note_parts))
        if notes:
            page_notes[page_no] = notes

    flush()

    merged: list[dict] = []
    for block in blocks:
        if block["kind"] == "example" and merged and merged[-1]["kind"] == "example":
            merged[-1]["text"] = join_parts([merged[-1]["text"], block["text"]])
            for page in block["pages"]:
                if page not in merged[-1]["pages"]:
                    merged[-1]["pages"].append(page)
            continue
        if (
            block["kind"] == "example"
            and merged
            and merged[-1]["kind"] in {"para", "body"}
            and block["start_page"] == merged[-1]["pages"][-1]
        ):
            merged[-1]["text"] = join_parts([merged[-1]["text"], block["text"]])
            for page in block["pages"]:
                if page not in merged[-1]["pages"]:
                    merged[-1]["pages"].append(page)
            continue
        if block["kind"] == "bullet" and merged and merged[-1]["kind"] == "bullet":
            merged[-1]["text"] = join_parts([merged[-1]["text"], block["text"]])
            for page in block["pages"]:
                if page not in merged[-1]["pages"]:
                    merged[-1]["pages"].append(page)
            continue
        merged.append(block)

    collapsed: list[dict] = []
    index = 0
    while index < len(merged):
        block = merged[index]
        if (
            collapsed
            and block["kind"] == "body"
            and collapsed[-1]["kind"] == "body"
            and block["text"].endswith(":")
            and len(block["text"]) < 160
            and index + 1 < len(merged)
            and merged[index + 1]["kind"] == "bullet"
        ):
            collapsed[-1]["text"] = join_parts([collapsed[-1]["text"], block["text"]])
            for page in block["pages"]:
                if page not in collapsed[-1]["pages"]:
                    collapsed[-1]["pages"].append(page)
            index += 1
            continue
        collapsed.append(block)
        index += 1
    merged = collapsed

    # Attach each page's footnotes after the last block that occupies that page.
    last_for_page: dict[int, int] = {}
    for index, block in enumerate(merged):
        for page in block["pages"]:
            last_for_page[page] = index

    inserts: dict[int, list[str]] = {}
    for page, notes in page_notes.items():
        anchor = last_for_page.get(page)
        if anchor is None:
            raise SystemExit(f"footnote on page {page} has no anchor")
        inserts.setdefault(anchor, []).append(join_parts(notes))

    final: list[dict] = []
    for index, block in enumerate(merged):
        final.append(block)
        for note in inserts.get(index, []):
            final.append(
                {
                    "kind": "fn",
                    "text": note,
                    "start_page": block["start_page"],
                    "pages": block["pages"],
                }
            )
    return final


def main() -> None:
    blocks = extract()
    OUT.write_text(json.dumps(blocks, ensure_ascii=False, indent=2), encoding="utf-8")
    from collections import Counter

    print("blocks", len(blocks), Counter(block["kind"] for block in blocks))
    nums = [block["num"] for block in blocks if "num" in block]
    print("para nums", nums[0], nums[-1], "count", len(nums), "missing", [n for n in range(1, 258) if n not in nums])
    for index, block in enumerate(blocks, 1):
        label = block["kind"]
        if "num" in block:
            label += f" {block['num']}"
        preview = block["text"][:120].replace("\n", " ")
        print(f"{index:03d} p{block['start_page']:02d} {label:14} {preview}")


if __name__ == "__main__":
    main()
