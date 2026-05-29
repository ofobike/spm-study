#!/usr/bin/env python
"""OCR and index the 2024 second-half past-exam PDF from F:\\备份项目."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import fitz
import numpy as np
from PIL import Image

try:
    import easyocr
except ImportError as exc:  # pragma: no cover
    raise SystemExit("easyocr is required for OCR. Install or use a text-layer PDF.") from exc


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = Path(r"F:\备份项目\2024年下半年\2024年系统规划与管理师真题解析【持续更新‖免费提供：cunlove.cn】.pdf")
BACKUP_DIR = ROOT / "references" / "backup-pdfs"
PAST_EXAMS_DIR = BACKUP_DIR / "past-exams"
MANIFEST_FILE = BACKUP_DIR / "manifest.json"
INDEX_FILE = BACKUP_DIR / "index.md"
OUTPUT_FILE = PAST_EXAMS_DIR / "2024年系统规划与管理师真题解析.md"


def clean_ocr_line(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    return text


def ocr_pdf(pdf_path: Path, dpi: int) -> list[tuple[int, str]]:
    reader = easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)
    doc = fitz.open(pdf_path)
    pages: list[tuple[int, str]] = []
    for index, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=dpi)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        rows = reader.readtext(np.array(image), detail=1, paragraph=False)
        lines = [clean_ocr_line(str(item[1])) for item in rows if len(item) >= 2 and clean_ocr_line(str(item[1]))]
        pages.append((index, "\n".join(lines)))
        print(f"OCR page {index}/{doc.page_count}: {sum(len(line) for line in lines)} chars", file=sys.stderr)
    doc.close()
    return pages


def render_markdown(pdf_path: Path, pages: list[tuple[int, str]]) -> str:
    header = [
        "# 2024年系统规划与管理师真题解析",
        "",
        f"> 来源：`{pdf_path}`",
        "> 分类：历年真题",
        "> 年份：2024",
        "> 考期：下半年",
        "> 科目：综合知识+案例",
        "> 说明：本文件由 EasyOCR 从扫描 PDF 提取，可能存在识别错误；结构化入库需以可稳定解析的题干、选项、答案为准。",
        "",
        "---",
        "",
    ]
    body: list[str] = []
    for page_no, text in pages:
        body.extend([f"## 第 {page_no} 页", ""])
        body.append(text.strip() or "[OCR 无可用文本]")
        body.extend(["", "---", ""])
    return "\n".join(header + body).rstrip() + "\n"


def text_chars(markdown: str) -> int:
    body = re.sub(r"^# .+?\n(?:\n|> .+?\n)*", "", markdown, flags=re.DOTALL)
    return len(re.sub(r"\s+", "", body))


def load_manifest() -> dict[str, Any]:
    if not MANIFEST_FILE.exists():
        return {
            "base_path": r"F:\备份项目",
            "file_count": 0,
            "total_size_bytes": 0,
            "category_counts": {},
            "extracted_count": 0,
            "needs_ocr_count": 0,
            "files": [],
        }
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def update_manifest(markdown: str) -> dict[str, Any]:
    manifest = load_manifest()
    files = list(manifest.get("files", []))
    path_text = str(PDF_PATH)
    rel_markdown = str(OUTPUT_FILE.relative_to(ROOT))
    row = next((item for item in files if str(item.get("path")) == path_text), None)
    if row is None:
        row = {
            "title": "2024年系统规划与管理师真题解析",
            "path": path_text,
            "relative_path": str(PDF_PATH.relative_to(Path(r"F:\备份项目"))),
            "category": "past-exam",
            "category_label": "历年真题",
            "size_bytes": PDF_PATH.stat().st_size,
        }
        files.append(row)
    doc = fitz.open(PDF_PATH)
    page_count = doc.page_count
    doc.close()
    row.update(
        {
            "title": "2024年系统规划与管理师真题解析",
            "category": "past-exam",
            "category_label": "历年真题",
            "page_count": page_count,
            "year": 2024,
            "period": "下半年",
            "subject": "综合知识+案例",
            "needs_ocr": False,
            "text_chars": text_chars(markdown),
            "markdown": rel_markdown,
        }
    )
    manifest["files"] = files
    manifest["file_count"] = len(files)
    manifest["total_size_bytes"] = sum(int(item.get("size_bytes") or 0) for item in files)
    counts: dict[str, int] = {}
    for item in files:
        key = str(item.get("category") or "other")
        counts[key] = counts.get(key, 0) + 1
    manifest["category_counts"] = counts
    manifest["extracted_count"] = sum(1 for item in files if item.get("markdown"))
    manifest["needs_ocr_count"] = sum(1 for item in files if item.get("needs_ocr"))
    return manifest


def write_index(manifest: dict[str, Any]) -> None:
    from import_backup_pdfs import render_index

    INDEX_FILE.write_text(render_index(manifest), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR and index 2024 second-half past-exam PDF.")
    parser.add_argument("--write", action="store_true", help="Write markdown, manifest, and index.")
    parser.add_argument("--force", action="store_true", help="Run OCR even if markdown already exists.")
    parser.add_argument("--dpi", type=int, default=220)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()

    if not PDF_PATH.exists():
        raise SystemExit(f"PDF not found: {PDF_PATH}")
    if OUTPUT_FILE.exists() and not args.force:
        markdown = OUTPUT_FILE.read_text(encoding="utf-8")
    else:
        pages = ocr_pdf(PDF_PATH, args.dpi)
        markdown = render_markdown(PDF_PATH, pages)

    manifest = update_manifest(markdown)
    if args.write:
        PAST_EXAMS_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(markdown, encoding="utf-8")
        MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_index(manifest)

    payload = {
        "pdf": str(PDF_PATH),
        "markdown": str(OUTPUT_FILE.relative_to(ROOT)),
        "text_chars": text_chars(markdown),
        "pages": next((item.get("page_count") for item in manifest["files"] if str(item.get("path")) == str(PDF_PATH)), None),
        "write": bool(args.write),
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("# 2024下半年真题 OCR 导入")
        print("")
        print(f"- PDF：`{payload['pdf']}`")
        print(f"- Markdown：`{payload['markdown']}`")
        print(f"- 页数：{payload['pages']}")
        print(f"- 文本字符：{payload['text_chars']}")
        print(f"- 写入：{payload['write']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
