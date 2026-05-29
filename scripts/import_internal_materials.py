#!/usr/bin/env python
"""Import the 2025 internal SPM study materials into references/internal.

The importer is intentionally conservative: it always creates a source index,
and only extracts text for selected smaller materials unless asked otherwise.
Large scanned PDFs should be indexed first and OCRed in smaller batches.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - surfaced as a CLI error.
    fitz = None

try:
    import docx
except ImportError:  # pragma: no cover - surfaced as a CLI error.
    docx = None


ROOT = Path(__file__).resolve().parents[1]
INTERNAL_BASE = Path(r"F:\备份项目\00-25年新版内部资料（持续更新中）\2025高级系规备考资料")
OUTPUT_DIR = ROOT / "references" / "internal"
MANIFEST_FILE = OUTPUT_DIR / "manifest.json"
PRESERVED_TITLE_MARKERS = ("有答案版", "无答案版", "解析版", "题目版", "答案版")
CHAPTER_TITLES = {
    1: "信息系统与信息技术发展",
    2: "数字中国与数智化发展",
    3: "系统科学与哲学方法论",
    4: "信息系统规划",
    5: "应用系统规划",
    6: "云资源规划",
    7: "网络环境规划",
    8: "数据资源规划",
    9: "信息安全规划",
    10: "云原生系统规划",
    11: "信息系统治理",
    12: "信息系统服务管理",
    13: "人员管理",
    14: "规范与过程管理",
    15: "技术与研发管理",
    16: "资源与工具管理",
    17: "信息系统项目管理",
    18: "智慧城市发展规划",
    19: "智慧园区发展规划",
    20: "数字乡村发展规划",
    21: "企业数字化转型发展规划",
    22: "智能制造发展规划",
    23: "新型消费系统规划",
    24: "法律法规和标准规范",
}


CATEGORIES: dict[str, dict[str, str]] = {
    "guide": {
        "prefix": "01.2025系规学习指南",
        "name": "学习指南",
        "output": "guide",
        "description": "考试时间、科目、章节学习建议和分值预测，适合做备考导航。",
    },
    "syllabus": {
        "prefix": "02.2025系规教材+大纲",
        "name": "教材与大纲",
        "output": "syllabus",
        "description": "第2版教程、考试大纲、大纲分析和新老教材对比。",
    },
    "notes": {
        "prefix": "03.2025系规三色笔记",
        "name": "三色笔记",
        "output": "three-color-notes",
        "description": "1-24章三色笔记，适合提炼高频考点和背诵清单。",
    },
    "mindmap": {
        "prefix": "04.2025系规思维导图",
        "name": "思维导图",
        "output": "mindmaps",
        "description": "1-24章思维导图，适合章节速览和知识结构导航。",
    },
    "questions": {
        "prefix": "05.2025系规章节习题",
        "name": "章节习题",
        "output": "chapter-practice",
        "description": "千题闯关、全练、解析版，适合扩充和校验章节题库。",
    },
    "case": {
        "prefix": "06.2025系规案例专题",
        "name": "案例专题",
        "output": "case-special",
        "description": "案例背诵有答案/无答案版，适合增强案例分析主观题训练。",
    },
    "paper": {
        "prefix": "07.2025系规论文专题",
        "name": "论文专题",
        "output": "paper-special",
        "description": "论文学习建议、框架格式和行业范文，适合增强论文训练闭环。",
    },
}


def normalize_slug(text: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "-", text)
    value = re.sub(r"\s+", "-", value).strip("-")
    return value[:120] or "material"


def category_for(path: Path) -> str:
    rel = path.relative_to(INTERNAL_BASE)
    top = rel.parts[0] if rel.parts else ""
    for key, info in CATEGORIES.items():
        if top.startswith(info["prefix"]):
            return key
    return "other"


def discover_files() -> list[dict[str, Any]]:
    files = []
    for path in sorted(INTERNAL_BASE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(INTERNAL_BASE)
        category = category_for(path)
        files.append(
            {
                "path": str(path),
                "relative_path": str(rel),
                "category": category,
                "suffix": path.suffix.lower() or "<none>",
                "size_bytes": path.stat().st_size,
            }
        )
    return files


def pdf_page_count(path: Path) -> int | None:
    if fitz is None or path.suffix.lower() != ".pdf":
        return None
    try:
        doc = fitz.open(path)
        count = doc.page_count
        doc.close()
        return count
    except Exception:  # noqa: BLE001 - index generation should keep going.
        return None


def preserved_markers(text: str) -> list[str]:
    markers = []
    for match in re.findall(r"【([^】]+)】", text):
        clean = match.strip()
        if any(token in clean for token in PRESERVED_TITLE_MARKERS):
            markers.append(clean)
    return markers


def file_title(path: Path) -> str:
    title = path.stem
    markers = preserved_markers(title)
    title = re.sub(r"【[^】]+】", "", title)
    title = re.sub(r"（[^）]*?cun[^）]*?）", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+", " ", title).strip(" _-")
    if markers:
        title = "-".join([*markers, title])
    return title or path.stem


def chapter_no_from_title(text: str) -> int | None:
    patterns = [
        r"第\s*(\d{1,2})\s*章",
        r"^(\d{1,2})(?=[^\d])",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 24:
                return value
    return None


def extracted_output_path(out_dir: Path, item: dict[str, Any]) -> Path:
    """Return a stable markdown path without allowing same-title sources to collide."""
    path = Path(item["path"])
    stem = normalize_slug(file_title(path))
    candidate = out_dir / f"{stem}.md"
    if not candidate.exists():
        return candidate

    source_line = f"> 来源：`{item['relative_path']}`"
    try:
        if source_line in candidate.read_text(encoding="utf-8", errors="ignore"):
            return candidate
    except OSError:
        pass

    rel_stem = normalize_slug(str(Path(item["relative_path"]).with_suffix("")))
    candidate = out_dir / f"{stem}-{rel_stem[-48:]}.md"
    counter = 2
    while candidate.exists():
        candidate = out_dir / f"{stem}-{rel_stem[-44:]}-{counter}.md"
        counter += 1
    return candidate


def load_manifest() -> dict[str, Any]:
    if MANIFEST_FILE.exists():
        return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    return {"base_path": str(INTERNAL_BASE), "files": []}


def save_manifest(files: list[dict[str, Any]]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    enriched = []
    for item in files:
        path = Path(item["path"])
        row = dict(item)
        row["title"] = file_title(path)
        row["page_count"] = pdf_page_count(path)
        enriched.append(row)
    MANIFEST_FILE.write_text(
        json.dumps({"base_path": str(INTERNAL_BASE), "files": enriched}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def render_index(files: list[dict[str, Any]]) -> str:
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in files:
        by_category[item["category"]].append(item)

    ext_counts = Counter(item["suffix"] for item in files)
    lines = [
        "# 2025高级系规内部备考资料索引",
        "",
        f"> 来源目录：`{INTERNAL_BASE}`",
        "> 说明：本索引用于定位和分批导入本地备考资料；大体量 PDF 不直接全文写入 SKILL.md。",
        "",
        "## 总览",
        "",
        f"- 文件数：{len(files)}",
        f"- 类型分布：{dict(sorted(ext_counts.items()))}",
        "",
        "## 分类",
        "",
    ]

    for key in CATEGORIES:
        info = CATEGORIES[key]
        rows = by_category.get(key, [])
        size_mb = sum(int(item["size_bytes"]) for item in rows) / 1024 / 1024
        lines.extend(
            [
                f"### {info['name']}",
                "",
                f"- 说明：{info['description']}",
                f"- 文件数：{len(rows)}",
                f"- 总大小：{size_mb:.2f} MB",
                "",
                "| 文件 | 类型 | 页数 | 大小 | 用途 |",
                "|---|---:|---:|---:|---|",
            ]
        )
        for item in rows:
            path = Path(item["path"])
            pages = item.get("page_count")
            pages_text = str(pages) if pages else "-"
            size_text = f"{int(item['size_bytes']) / 1024 / 1024:.2f} MB"
            lines.append(
                f"| `{item['relative_path']}` | {item['suffix']} | {pages_text} | {size_text} | {info['description']} |"
            )
        lines.append("")

    lines.extend(
        [
            "## 导入策略",
            "",
            "1. 论文专题：体量小，优先抽取为 `references/internal/paper-special/`，用于论文框架和评分闭环。",
            "2. 案例专题：优先建立索引，再分批 OCR/结构化到 `assets/questions/case_studies.json`。",
            "3. 章节习题：先抽取解析版，经过题目质量审计后再合并进章节题库。",
            "4. 三色笔记和思维导图：先做章节索引，按用户需要再抽取对应章节，避免上下文膨胀。",
            "5. 教材与大纲：当前 `references/` 已有章节 markdown，内部资料作为补充校验来源。",
            "",
        ]
    )
    return "\n".join(lines)


def extract_pdf_text(path: Path) -> tuple[str, int, int]:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")
    doc = fitz.open(path)
    page_count = doc.page_count
    extracted_pages = 0
    parts = []
    for index, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if text:
            extracted_pages += 1
            parts.append(f"## 第 {index} 页\n\n{text}")
    doc.close()
    return "\n\n---\n\n".join(parts), page_count, extracted_pages


def extract_docx_text(path: Path) -> str:
    if docx is None:
        raise RuntimeError("python-docx is not installed")
    document = docx.Document(path)
    return "\n\n".join(paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip())


def write_extracted_markdown(item: dict[str, Any]) -> Path | None:
    path = Path(item["path"])
    category = item["category"]
    if category not in CATEGORIES:
        return None
    out_dir = OUTPUT_DIR / CATEGORIES[category]["output"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = extracted_output_path(out_dir, item)

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text, page_count, extracted_pages = extract_pdf_text(path)
        if not text.strip():
            text = "未提取到可复制文本；该文件可能需要 OCR。"
    elif suffix == ".docx":
        text = extract_docx_text(path)
        page_count = None
        extracted_pages = None
    elif suffix == ".svg" and category == "mindmap":
        copied = out_dir / f"{normalize_slug(file_title(path))}.svg"
        shutil.copy2(path, copied)
        text = f"SVG 思维导图已复制到 `{copied.relative_to(ROOT)}`。"
        page_count = None
        extracted_pages = None
    else:
        return None

    header = [
        f"# {file_title(path)}",
        "",
        f"> 来源：`{item['relative_path']}`",
        f"> 分类：{CATEGORIES[category]['name']}",
        "> 说明：由内部备考资料导入脚本提取；如存在排版或识别问题，以原文件为准。",
    ]
    if suffix == ".pdf":
        header.append(f"> 页数：{page_count}，提取到文本页：{extracted_pages}")
    if suffix == ".svg":
        header.append(f"> 本地资源：`{copied.relative_to(ROOT)}`")
    header.append("")
    out_file.write_text("\n".join(header) + "\n" + text.strip() + "\n", encoding="utf-8")
    return out_file


def category_output_file(item: dict[str, Any]) -> Path | None:
    category = item["category"]
    if category not in CATEGORIES:
        return None
    path = Path(item["path"])
    suffix = path.suffix.lower()
    if suffix not in {".pdf", ".docx", ".svg"}:
        return None
    out_dir = OUTPUT_DIR / CATEGORIES[category]["output"]
    return out_dir / f"{normalize_slug(file_title(path))}.md"


def write_chapter_navigation(category: str, files: list[dict[str, Any]]) -> list[Path]:
    if category not in {"notes", "mindmap"}:
        return []
    info = CATEGORIES[category]
    out_dir = OUTPUT_DIR / info["output"]
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for item in files:
        if item["category"] != category:
            continue
        chapter_no = chapter_no_from_title(item.get("title") or item["relative_path"])
        if chapter_no is None:
            chapter_no = chapter_no_from_title(item["relative_path"])
        if chapter_no is None:
            continue
        output_file = category_output_file(item)
        asset_file = None
        if Path(item["path"]).suffix.lower() == ".svg":
            asset_file = out_dir / f"{normalize_slug(file_title(Path(item['path'])))}.svg"
        records.append(
            {
                "chapter": chapter_no,
                "chapter_title": CHAPTER_TITLES.get(chapter_no, ""),
                "title": item.get("title") or file_title(Path(item["path"])),
                "source": item["relative_path"],
                "source_type": item["suffix"],
                "page_count": item.get("page_count"),
                "size_bytes": item.get("size_bytes"),
                "markdown": str(output_file.relative_to(ROOT)) if output_file else None,
                "asset": str(asset_file.relative_to(ROOT)) if asset_file else None,
            }
        )
    records.sort(key=lambda row: row["chapter"])

    json_file = out_dir / "index.json"
    json_file.write_text(json.dumps({"category": category, "name": info["name"], "items": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# {info['name']}章节导航",
        "",
        f"> 来源：`{INTERNAL_BASE}`",
        f"> 说明：{info['description']}",
        "",
        "| 章 | 章节 | 抽取文本 | 页数 | 原始资料 |",
        "|---:|---|---|---:|---|",
    ]
    for row in records:
        pages = row["page_count"] if row["page_count"] is not None else "-"
        markdown = f"`{row['markdown']}`" if row["markdown"] else "-"
        source = f"`{row['source']}`"
        lines.append(f"| {row['chapter']} | {row['chapter_title']} | {markdown} | {pages} | {source} |")
    lines.append("")
    md_file = out_dir / "index.md"
    md_file.write_text("\n".join(lines), encoding="utf-8")
    return [md_file, json_file]


def import_source(source: str, extract_text: bool) -> list[Path]:
    files = discover_files()
    save_manifest(files)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "index.md").write_text(render_index(load_manifest()["files"]), encoding="utf-8")
    if source == "index" or not extract_text:
        return [OUTPUT_DIR / "index.md", MANIFEST_FILE]

    selected = [item for item in load_manifest()["files"] if source == "all" or item["category"] == source]
    written = [OUTPUT_DIR / "index.md", MANIFEST_FILE]
    for item in selected:
        result = write_extracted_markdown(item)
        if result is not None:
            written.append(result)
    manifest_files = load_manifest()["files"]
    if source in {"notes", "all"}:
        written.extend(write_chapter_navigation("notes", manifest_files))
    if source in {"mindmap", "all"}:
        written.extend(write_chapter_navigation("mindmap", manifest_files))
    return written


def main() -> int:
    global INTERNAL_BASE

    parser = argparse.ArgumentParser(description="Import the 2025 internal SPM study materials.")
    parser.add_argument("--base", default=str(INTERNAL_BASE), help="Source directory for internal materials.")
    parser.add_argument("--source", choices=["index", "all", *CATEGORIES.keys()], default="index")
    parser.add_argument("--extract-text", action="store_true", help="Extract text from PDFs/DOCX for the selected source.")
    parser.add_argument("--list", action="store_true", help="List discovered materials without writing extraction files.")
    args = parser.parse_args()

    INTERNAL_BASE = Path(args.base)
    if not INTERNAL_BASE.exists():
        print(f"Source directory not found: {INTERNAL_BASE}", file=sys.stderr)
        return 1

    files = discover_files()
    if args.list:
        for item in files:
            print(f"{item['category']:9s} {item['suffix']:7s} {item['relative_path']}")
        return 0

    written = import_source(args.source, extract_text=args.extract_text)
    print("Written:")
    for path in written:
        print(f"- {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
