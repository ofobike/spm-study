#!/usr/bin/env python
"""Index and extract selected PDFs from F:\\备份项目 into references/backup-pdfs."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


ROOT = Path(__file__).resolve().parents[1]
BACKUP_BASE = Path(r"F:\备份项目")
OUTPUT_DIR = ROOT / "references" / "backup-pdfs"
MANIFEST_FILE = OUTPUT_DIR / "manifest.json"
INDEX_FILE = OUTPUT_DIR / "index.md"


CATEGORY_INFO: dict[str, dict[str, str]] = {
    "past-exam": {"label": "历年真题", "output": "past-exams", "description": "2017-2024 系统规划与管理师真题、答案和解析。"},
    "standards": {"label": "标准规范库", "output": "standards", "description": "IT 服务、信息安全、法律法规和标准规范原文。"},
    "mock": {"label": "模拟题库", "output": "mock-bank", "description": "章节模拟题和二轮模拟题，适合作为候选练习源。"},
    "other": {"label": "其他资料", "output": "other", "description": "尚未归类的备考 PDF。"},
}


def clean_name(text: str) -> str:
    text = re.sub(r"【[^】]+】", "", text)
    text = re.sub(r"（[^）]*?(?:cun|公众号|免费|关注|整理|分享)[^）]*?）", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" _-")
    return text or "material"


def slug(text: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "-", text)
    value = re.sub(r"\s+", "-", value).strip("-")
    return value[:140] or "material"


def category_for(path: Path) -> str:
    try:
        top = path.relative_to(BACKUP_BASE).parts[0]
    except ValueError:
        return "other"
    if re.match(r"20\d{2}年", top):
        return "past-exam"
    if "标准" in top or "规范" in top:
        return "standards"
    if "模拟" in top:
        return "mock"
    return "other"


def detect_exam_year_period(path: Path) -> tuple[int | None, str | None]:
    text = str(path)
    year_match = re.search(r"(20\d{2})", text)
    year = int(year_match.group(1)) if year_match else None
    if "上半年" in text or ".5" in text or "05" in text:
        return year, "上半年"
    if "下半年" in text or ".11" in text or "11" in text:
        return year, "下半年"
    return year, None


def detect_exam_subject(path: Path) -> str | None:
    name = path.name
    if any(word in name for word in ("上午", "选择")):
        return "综合知识"
    if any(word in name for word in ("案例", "下午案例")):
        return "案例分析"
    if "论文" in name:
        return "论文"
    if "真题" in name and "解析" in name:
        return "综合知识+案例"
    return None


def pdf_meta(path: Path) -> tuple[int | None, str, bool]:
    if fitz is None:
        return None, "", True
    text_parts: list[str] = []
    page_count: int | None = None
    try:
        doc = fitz.open(path)
        page_count = doc.page_count
        for page in doc:
            text_parts.append(page.get_text("text"))
        doc.close()
    except Exception:  # noqa: BLE001 - importer should keep going.
        return page_count, "", True
    text = "\n".join(part.strip() for part in text_parts if part.strip())
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return page_count, text, len(text) < 200


def discover_pdfs() -> list[Path]:
    if not BACKUP_BASE.exists():
        return []
    return sorted(path for path in BACKUP_BASE.rglob("*.pdf") if path.is_file())


def build_manifest(write: bool, extract_text: bool) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for path in discover_pdfs():
        category = category_for(path)
        info = CATEGORY_INFO[category]
        title = clean_name(path.stem)
        rel = path.relative_to(BACKUP_BASE)
        page_count, text, needs_ocr = pdf_meta(path) if (extract_text or write) else (None, "", False)
        output_rel = None
        if write and text:
            out_dir = OUTPUT_DIR / info["output"]
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{slug(title)}.md"
            prefix = [
                f"# {title}",
                "",
                f"> 来源：`{path}`",
                f"> 分类：{info['label']}",
            ]
            year, period = detect_exam_year_period(path)
            subject = detect_exam_subject(path)
            if year:
                prefix.append(f"> 年份：{year}")
            if period:
                prefix.append(f"> 考期：{period}")
            if subject:
                prefix.append(f"> 科目：{subject}")
            prefix.extend(["", text])
            out_path.write_text("\n".join(prefix).rstrip() + "\n", encoding="utf-8")
            output_rel = str(out_path.relative_to(ROOT))
        year, period = detect_exam_year_period(path)
        rows.append(
            {
                "title": title,
                "path": str(path),
                "relative_path": str(rel),
                "category": category,
                "category_label": info["label"],
                "size_bytes": path.stat().st_size,
                "page_count": page_count,
                "year": year,
                "period": period,
                "subject": detect_exam_subject(path),
                "needs_ocr": needs_ocr,
                "text_chars": len(text),
                "markdown": output_rel,
            }
        )
    manifest = {
        "base_path": str(BACKUP_BASE),
        "file_count": len(rows),
        "total_size_bytes": sum(int(row["size_bytes"]) for row in rows),
        "category_counts": dict(Counter(row["category"] for row in rows)),
        "extracted_count": sum(1 for row in rows if row.get("markdown")),
        "needs_ocr_count": sum(1 for row in rows if row.get("needs_ocr")),
        "files": rows,
    }
    if write:
        MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        INDEX_FILE.write_text(render_index(manifest), encoding="utf-8")
    return manifest


def render_index(manifest: dict[str, Any]) -> str:
    files = list(manifest.get("files", []))
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in files:
        by_category[row["category"]].append(row)
    lines = [
        "# F盘备份 PDF 资料索引",
        "",
        f"> 来源目录：`{manifest.get('base_path')}`",
        "> 说明：此处只索引并抽取高价值 PDF；扫描或抽取文本过少的文件会标记 needs_ocr。",
        "",
        "## 总览",
        "",
        f"- PDF 数量：{manifest.get('file_count', 0)}",
        f"- 总大小：{float(manifest.get('total_size_bytes', 0)) / 1024 / 1024:.2f} MB",
        f"- 已抽取文本：{manifest.get('extracted_count', 0)}",
        f"- 可能需要 OCR：{manifest.get('needs_ocr_count', 0)}",
        "",
    ]
    for key, info in CATEGORY_INFO.items():
        rows = by_category.get(key, [])
        if not rows:
            continue
        lines.extend([f"## {info['label']}", "", info["description"], ""])
        lines.append("| 文件 | 年份 | 科目 | 页数 | 文本 | 输出 |")
        lines.append("|------|------|------|------|------|------|")
        for row in rows:
            text_status = "需OCR" if row.get("needs_ocr") else f"{row.get('text_chars', 0)}字"
            lines.append(
                "| {title} | {year} {period} | {subject} | {pages} | {text_status} | `{markdown}` |".format(
                    title=row.get("title"),
                    year=row.get("year") or "-",
                    period=row.get("period") or "",
                    subject=row.get("subject") or "-",
                    pages=row.get("page_count") or "-",
                    text_status=text_status,
                    markdown=row.get("markdown") or "-",
                )
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# F盘备份 PDF 导入",
        "",
        f"- 来源目录：`{manifest.get('base_path')}`",
        f"- PDF 数量：{manifest.get('file_count', 0)}",
        f"- 总大小：{float(manifest.get('total_size_bytes', 0)) / 1024 / 1024:.2f} MB",
        f"- 已抽取文本：{manifest.get('extracted_count', 0)}",
        f"- 可能需要 OCR：{manifest.get('needs_ocr_count', 0)}",
        f"- 分类：{manifest.get('category_counts', {})}",
        "",
        f"索引：`{INDEX_FILE.relative_to(ROOT)}`",
        f"清单：`{MANIFEST_FILE.relative_to(ROOT)}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import selected F:\\备份项目 PDFs into references/backup-pdfs.")
    parser.add_argument("--write", action="store_true", help="Write manifest, index, and extracted markdown files.")
    parser.add_argument("--extract-text", action="store_true", help="Extract text during dry-run too.")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()
    manifest = build_manifest(write=args.write, extract_text=args.extract_text)
    if args.format == "json":
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
