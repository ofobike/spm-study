#!/usr/bin/env python
"""Index and extract selected VIP materials into references/internal/vip-materials."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BASE = Path(r"F:\备份项目\vip材料")
OUTPUT_DIR = ROOT / "references" / "internal" / "vip-materials"
MANIFEST_FILE = OUTPUT_DIR / "manifest.json"
INDEX_FILE = OUTPUT_DIR / "index.md"


KIND_INFO: dict[str, dict[str, str]] = {
    "comprehensive": {
        "label": "一本通",
        "output": "comprehensive",
        "description": "2025 系规综合一本通，适合按需核对章节讲义和综合知识。",
        "strategy": "index_only",
    },
    "chapter-practice-answer": {
        "label": "分章节练习题有答案版",
        "output": "chapter-practice",
        "description": "VIP 分章节练习题有答案版，适合做候选题源和解析核对。",
        "strategy": "extract_selected",
    },
    "chapter-practice-blank": {
        "label": "分章节练习题无答案版",
        "output": "chapter-practice",
        "description": "VIP 分章节练习题无答案版，适合人工打印/自测；结构化优先使用有答案版。",
        "strategy": "index_only",
    },
    "theory-core": {
        "label": "案例论文理论必背",
        "output": "theory-core",
        "description": "案例和论文共用的理论必背知识点，适合补充主观题答题素材。",
        "strategy": "extract_selected",
    },
    "notes-summary": {
        "label": "三色笔记汇总版",
        "output": "notes-summary",
        "description": "三色笔记汇总 PDF；当前已有 1-24 章三色笔记，汇总版默认仅索引避免重复。",
        "strategy": "index_only",
    },
    "other": {
        "label": "其他VIP资料",
        "output": "other",
        "description": "尚未归类的 VIP 资料。",
        "strategy": "index_only",
    },
}


def clean_title(text: str) -> str:
    value = re.sub(r"【[^】]+】", "", text)
    value = re.sub(r"（[^）]*?(?:cun|免费|关注|整理|分享|获取)[^）]*?）", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" _-")
    return value or text


def slug(text: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "-", text)
    value = re.sub(r"\s+", "-", value).strip("-")
    return value[:120] or "material"


def detect_kind(path: Path) -> str:
    name = path.name
    if "一本通" in name:
        return "comprehensive"
    if "分章节练习题有答案" in name:
        return "chapter-practice-answer"
    if "分章节练习题无答案" in name:
        return "chapter-practice-blank"
    if "理论必背" in name:
        return "theory-core"
    if "三色笔记" in name and "汇总" in name:
        return "notes-summary"
    return "other"


def pdf_stats(path: Path) -> tuple[int | None, int, bool]:
    if fitz is None or path.suffix.lower() != ".pdf":
        return None, 0, True
    text_chars = 0
    try:
        doc = fitz.open(path)
        page_count = doc.page_count
        for page in doc:
            text_chars += len(page.get_text("text").strip())
        doc.close()
    except Exception:  # noqa: BLE001 - keep indexing robust.
        return None, 0, True
    return page_count, text_chars, text_chars < 200


def discover_files() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not SOURCE_BASE.exists():
        return rows
    for path in sorted(SOURCE_BASE.glob("*.pdf")):
        kind = detect_kind(path)
        page_count, text_chars, needs_ocr = pdf_stats(path)
        info = KIND_INFO[kind]
        rows.append(
            {
                "title": clean_title(path.stem),
                "path": str(path),
                "relative_path": str(path.relative_to(SOURCE_BASE)),
                "kind": kind,
                "kind_label": info["label"],
                "description": info["description"],
                "strategy": info["strategy"],
                "suffix": path.suffix.lower(),
                "size_bytes": path.stat().st_size,
                "page_count": page_count,
                "text_chars": text_chars,
                "needs_ocr": needs_ocr,
                "markdown": None,
            }
        )
    return rows


def extract_pdf_markdown(row: dict[str, Any]) -> Path | None:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")
    path = Path(row["path"])
    kind = str(row["kind"])
    info = KIND_INFO.get(kind, KIND_INFO["other"])
    out_dir = OUTPUT_DIR / info["output"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{slug(str(row['title']))}.md"

    doc = fitz.open(path)
    parts: list[str] = []
    extracted_pages = 0
    for index, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        if not text:
            continue
        extracted_pages += 1
        parts.append(f"## 第 {index} 页\n\n{text}")
    page_count = doc.page_count
    doc.close()
    if not parts:
        return None

    header = [
        f"# {row['title']}",
        "",
        f"> 来源：`{row['path']}`",
        f"> 分类：{row['kind_label']}",
        f"> 页数：{page_count}，提取到文本页：{extracted_pages}",
        "> 说明：由 VIP 材料导入脚本抽取；如排版有误，以原 PDF 为准。",
        "",
    ]
    out_file.write_text("\n".join(header) + "\n\n---\n\n".join(parts).strip() + "\n", encoding="utf-8")
    return out_file


def should_extract(row: dict[str, Any], mode: str) -> bool:
    if mode == "none":
        return False
    if mode == "all":
        return True
    return row.get("strategy") == "extract_selected"


def render_index(manifest: dict[str, Any]) -> str:
    rows = list(manifest.get("files", []))
    kind_counts = Counter(row["kind"] for row in rows)
    lines = [
        "# VIP材料索引",
        "",
        f"> 来源目录：`{manifest.get('base_path')}`",
        "> 说明：VIP 资料作为补充资料源接入。大体量或重复资料先索引，精选资料抽取为 markdown。",
        "",
        "## 总览",
        "",
        f"- 文件数：{manifest.get('file_count', 0)}",
        f"- 总大小：{float(manifest.get('total_size_bytes', 0)) / 1024 / 1024:.2f} MB",
        f"- 已抽取：{manifest.get('extracted_count', 0)}",
        f"- 类型分布：{dict(kind_counts)}",
        "",
        "## 文件清单",
        "",
        "| 类型 | 文件 | 页数 | 大小 | 文本 | 接入策略 | 输出 |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in rows:
        size_mb = int(row["size_bytes"]) / 1024 / 1024
        markdown = f"`{row['markdown']}`" if row.get("markdown") else "-"
        lines.append(
            f"| {row['kind_label']} | `{row['relative_path']}` | {row.get('page_count') or '-'} | "
            f"{size_mb:.2f} MB | {row.get('text_chars', 0)} | {row.get('strategy')} | {markdown} |"
        )
    lines.extend(
        [
            "",
            "## 使用建议",
            "",
            "- `chapter-practice-answer`：可作为候选题源，正式入库前仍需去重、元数据补齐、质量审计和回归。",
            "- `theory-core`：优先用于案例/论文主观题素材补充和答题采分点整理。",
            "- `notes-summary` 与现有 1-24 章三色笔记高度重叠，默认不重复抽取。",
            "- `comprehensive` 一本通体量较大，当前作为章节讲义补充索引，按需再抽取。",
            "",
        ]
    )
    return "\n".join(lines)


def build_manifest(write: bool, extract: str) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = discover_files()
    for row in rows:
        if not should_extract(row, extract):
            continue
        out_file = extract_pdf_markdown(row)
        if out_file is not None:
            row["markdown"] = str(out_file.relative_to(ROOT)).replace("\\", "/")
    manifest = {
        "base_path": str(SOURCE_BASE),
        "file_count": len(rows),
        "total_size_bytes": sum(int(row["size_bytes"]) for row in rows),
        "extracted_count": sum(1 for row in rows if row.get("markdown")),
        "files": rows,
    }
    if write:
        MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        INDEX_FILE.write_text(render_index(manifest), encoding="utf-8")
    return manifest


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# VIP材料导入",
        "",
        f"- 来源目录：`{manifest.get('base_path')}`",
        f"- 文件数：{manifest.get('file_count', 0)}",
        f"- 总大小：{float(manifest.get('total_size_bytes', 0)) / 1024 / 1024:.2f} MB",
        f"- 已抽取：{manifest.get('extracted_count', 0)}",
        f"- 索引：`{INDEX_FILE.relative_to(ROOT)}`",
        f"- 清单：`{MANIFEST_FILE.relative_to(ROOT)}`",
        "",
        "## 文件",
    ]
    for row in manifest.get("files", []):
        lines.append(f"- {row['kind_label']}：{row['relative_path']} -> {row.get('markdown') or '仅索引'}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import VIP materials into references/internal/vip-materials.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--extract", choices=["none", "selected", "all"], default="selected")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()

    manifest = build_manifest(write=args.write, extract=args.extract)
    if args.format == "json":
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
