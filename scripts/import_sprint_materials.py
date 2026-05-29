#!/usr/bin/env python
"""Index and extract selected sprint materials into references/internal/sprint-materials."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE_BASE = Path(r"F:\备份项目")
OUTPUT_DIR = ROOT / "references" / "internal" / "sprint-materials"
MANIFEST_FILE = OUTPUT_DIR / "manifest.json"
INDEX_FILE = OUTPUT_DIR / "index.md"

OCR_TARGETS = {"mnemonic", "gold-points", "mock-exam", "csf-risk", "activities", "sprint-guide"}
OCR_GROUPS = {
    "small": {"mnemonic", "csf-risk", "activities"},
    "all": OCR_TARGETS,
    "none": set(),
}


MATERIALS: list[dict[str, str]] = [
    {
        "filename": "系规精简记忆口诀83个.pdf",
        "kind": "mnemonic",
        "kind_label": "记忆口诀",
        "description": "83 个精简记忆口诀，适合临考前快速回忆高频概念和清单。",
        "strategy": "ocr_later",
    },
    {
        "filename": "系规临考突击押题65页金色考点【必看】【耗时整理‖免费分享：CuNlOve.cn】.pdf",
        "kind": "gold-points",
        "kind_label": "金色考点",
        "description": "临考突击押题和高频考点资料，适合冲刺阶段查漏补缺；不等同正式真题。",
        "strategy": "ocr_later",
    },
    {
        "filename": "24年11月系规综合模考题-第1套.pdf",
        "kind": "mock-exam",
        "kind_label": "综合模考题",
        "description": "2024 年 11 月综合模拟题候选资料，只作为模拟练习源，不标记为历年真题。",
        "strategy": "ocr_later",
    },
    {
        "filename": "28个关键成功因素、8大风险控制-冲刺2【精挑细选‖免费提供：cunlove.cn】.pdf",
        "kind": "csf-risk",
        "kind_label": "关键成功因素与风险控制",
        "description": "关键成功因素和风险控制冲刺资料，适合案例分析和论文素材补充。",
        "strategy": "ocr_later",
    },
    {
        "filename": "130个活动-冲刺1.pdf",
        "kind": "activities",
        "kind_label": "130个活动",
        "description": "130 个活动冲刺清单，适合流程、活动、管理动作类知识点背诵。",
        "strategy": "ocr_later",
    },
    {
        "filename": "规划冲刺资料-马军.pdf",
        "kind": "sprint-guide",
        "kind_label": "规划冲刺资料",
        "description": "系统规划与管理师冲刺资料，当前可抽取文本，适合冲刺复习和主观题素材补充。",
        "strategy": "extract_selected",
    },
]


def clean_title(text: str) -> str:
    value = re.sub(r"【[^】]+】", "", text)
    value = re.sub(r"（[^）]*?(?:cun|免费|关注|整理|分享|获取)[^）]*?）", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" _-")
    return value or text


def slug(text: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|]+", "-", text)
    value = re.sub(r"\s+", "-", value).strip("-")
    return value[:120] or "material"


def output_markdown_path(row: dict[str, Any]) -> Path:
    out_dir = OUTPUT_DIR / str(row["kind"])
    return out_dir / f"{slug(str(row['title']))}.md"


def markdown_char_count(path: Path) -> int:
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8", errors="ignore")
    return len(re.sub(r"\s+", "", text))


def file_sha1_prefix(path: Path, length: int = 16) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:length]


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
    for spec in MATERIALS:
        path = SOURCE_BASE / spec["filename"]
        exists = path.exists()
        page_count, text_chars, needs_ocr = pdf_stats(path) if exists else (None, 0, True)
        title = clean_title(path.stem)
        row = {
            "title": title,
            "path": str(path),
            "relative_path": str(path.relative_to(SOURCE_BASE)),
            "exists": exists,
            "kind": spec["kind"],
            "kind_label": spec["kind_label"],
            "description": spec["description"],
            "strategy": spec["strategy"],
            "suffix": path.suffix.lower(),
            "size_bytes": path.stat().st_size if exists else 0,
            "sha1_prefix": file_sha1_prefix(path),
            "page_count": page_count,
            "text_chars": text_chars,
            "needs_ocr": needs_ocr,
            "markdown": None,
        }
        rows.append(row)
    return rows


def attach_existing_markdown(row: dict[str, Any]) -> None:
    out_file = output_markdown_path(row)
    if not out_file.exists():
        return
    chars = markdown_char_count(out_file)
    row["markdown"] = str(out_file.relative_to(ROOT)).replace("\\", "/")
    if chars > int(row.get("text_chars") or 0):
        row["text_chars"] = chars
    if chars >= 200:
        row["needs_ocr"] = False
        if row.get("strategy") == "ocr_later":
            row["strategy"] = "ocr_completed"


def extract_pdf_markdown(row: dict[str, Any]) -> Path | None:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")
    path = Path(row["path"])
    if not path.exists():
        return None
    out_file = output_markdown_path(row)
    out_file.parent.mkdir(parents=True, exist_ok=True)

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
        "> 说明：由冲刺资料导入脚本抽取；如排版有误，以原 PDF 为准。",
        "",
    ]
    out_file.write_text("\n".join(header) + "\n\n---\n\n".join(parts).strip() + "\n", encoding="utf-8")
    return out_file


def clean_ocr_line(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    return text


def parse_page_range(page_range: str | None, max_pages: int) -> list[int]:
    if not page_range:
        return list(range(max_pages))
    pages: set[int] = set()
    for part in page_range.split(","):
        value = part.strip()
        if not value:
            continue
        if "-" in value:
            start_text, end_text = value.split("-", 1)
            start = max(1, int(start_text.strip()))
            end = min(max_pages, int(end_text.strip()))
            pages.update(range(start - 1, end))
        else:
            page = int(value) - 1
            if 0 <= page < max_pages:
                pages.add(page)
    return sorted(pages)


def load_ocr_reader() -> Any:
    try:
        import easyocr
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("easyocr is required for OCR. Install easyocr or skip --ocr.") from exc
    return easyocr.Reader(["ch_sim", "en"], gpu=False, verbose=False)


def ocr_pdf_markdown(row: dict[str, Any], reader: Any, dpi: int, pages: str | None, force: bool) -> Path | None:
    if fitz is None:
        raise RuntimeError("PyMuPDF is required for OCR.")
    path = Path(row["path"])
    if not path.exists():
        return None
    out_file = output_markdown_path(row)
    if out_file.exists() and not force:
        return out_file

    try:
        import numpy as np
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("numpy and Pillow are required for OCR.") from exc

    out_file.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(path)
    page_indices = parse_page_range(pages, doc.page_count)
    parts: list[str] = []
    total_chars = 0
    for sequence, page_index in enumerate(page_indices, start=1):
        page = doc[page_index]
        pix = page.get_pixmap(dpi=dpi)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        rows = reader.readtext(np.array(image), detail=1, paragraph=False)
        lines = [clean_ocr_line(str(item[1])) for item in rows if len(item) >= 2 and clean_ocr_line(str(item[1]))]
        page_text = "\n".join(lines).strip() or "[OCR 无可用文本]"
        total_chars += len(re.sub(r"\s+", "", page_text))
        parts.append(f"## 第 {page_index + 1} 页\n\n{page_text}")
        print(
            f"OCR {row['kind']} page {sequence}/{len(page_indices)} "
            f"(pdf page {page_index + 1}/{doc.page_count}): {len(page_text)} chars",
            file=sys.stderr,
        )
    page_count = doc.page_count
    doc.close()

    header = [
        f"# {row['title']}",
        "",
        f"> 来源：`{row['path']}`",
        f"> 分类：{row['kind_label']}",
        f"> 页数：{page_count}，OCR 页：{len(page_indices)}，DPI：{dpi}",
        "> 说明：由 EasyOCR 从扫描 PDF 提取，可能存在识别错误；如排版或文字有疑问，以原 PDF 为准。",
        "",
    ]
    out_file.write_text("\n".join(header) + "\n\n---\n\n".join(parts).strip() + "\n", encoding="utf-8")
    row["markdown"] = str(out_file.relative_to(ROOT)).replace("\\", "/")
    row["text_chars"] = max(int(row.get("text_chars") or 0), total_chars)
    row["needs_ocr"] = total_chars < 200
    row["strategy"] = "ocr_completed" if not row["needs_ocr"] else "ocr_partial"
    return out_file


def should_extract(row: dict[str, Any], mode: str) -> bool:
    if mode == "none" or not row.get("exists") or row.get("needs_ocr"):
        return False
    if mode == "all":
        return True
    return row.get("strategy") == "extract_selected"


def normalize_ocr_targets(values: list[str] | None) -> set[str]:
    targets: set[str] = set()
    for raw in values or []:
        for part in str(raw).split(","):
            value = part.strip()
            if not value:
                continue
            if value in OCR_GROUPS:
                targets.update(OCR_GROUPS[value])
            elif value in OCR_TARGETS:
                targets.add(value)
            else:
                choices = ", ".join(sorted(OCR_TARGETS | set(OCR_GROUPS)))
                raise ValueError(f"Unknown OCR target '{value}'. Use one of: {choices}")
    return targets


def render_index(manifest: dict[str, Any]) -> str:
    rows = list(manifest.get("files", []))
    kind_counts = Counter(row["kind"] for row in rows if row.get("exists"))
    lines = [
        "# 冲刺资料索引",
        "",
        f"> 来源目录：`{manifest.get('base_path')}`",
        "> 说明：冲刺资料作为补充资料源接入。押题、模拟题和冲刺清单不自动并入正式题库；扫描 PDF 可用 --ocr 分批识别。",
        "",
        "## 总览",
        "",
        f"- 文件数：{manifest.get('file_count', 0)}",
        f"- 存在文件：{manifest.get('existing_count', 0)}",
        f"- 总大小：{float(manifest.get('total_size_bytes', 0)) / 1024 / 1024:.2f} MB",
        f"- 已抽取：{manifest.get('extracted_count', 0)}",
        f"- 需 OCR：{manifest.get('needs_ocr_count', 0)}",
        f"- 类型分布：{dict(kind_counts)}",
        "",
        "## 文件清单",
        "",
        "| 类型 | 文件 | 页数 | 大小 | 文本 | 需OCR | 接入策略 | 输出 | SHA1 |",
        "|---|---|---:|---:|---:|---|---|---|---|",
    ]
    for row in rows:
        size_mb = int(row["size_bytes"]) / 1024 / 1024
        markdown = f"`{row['markdown']}`" if row.get("markdown") else "-"
        page_count = row.get("page_count") or "-"
        needs_ocr = "是" if row.get("needs_ocr") else "否"
        exists_note = "" if row.get("exists") else "（缺失）"
        lines.append(
            f"| {row['kind_label']} | `{row['relative_path']}`{exists_note} | {page_count} | "
            f"{size_mb:.2f} MB | {row.get('text_chars', 0)} | {needs_ocr} | "
            f"{row.get('strategy')} | {markdown} | {row.get('sha1_prefix') or '-'} |"
        )
    lines.extend(
        [
            "",
            "## 使用建议",
            "",
            "- `sprint-guide`：当前已抽取文本，可用于冲刺复习、案例分析和论文素材补充。",
            "- `mock-exam`：先作为模拟题候选资料；只有 OCR 和解析质量通过后，才可拆成模拟训练题。",
            "- `mnemonic`、`gold-points`、`csf-risk`、`activities`：OCR 完成后可继续整理为背诵卡片、案例采分点或论文素材库。",
            "- 这些资料不是历年真题；调用和回答时统一称为冲刺资料、押题资料、模拟题或候选题源。",
            "",
        ]
    )
    return "\n".join(lines)


def build_manifest(
    write: bool,
    extract: str,
    ocr_targets: set[str] | None = None,
    force_ocr: bool = False,
    dpi: int = 220,
    pages: str | None = None,
) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = discover_files()
    for row in rows:
        attach_existing_markdown(row)
    ocr_targets = ocr_targets or set()
    if ocr_targets and not write:
        raise ValueError("OCR requires write=True because OCR creates markdown files and refreshes the manifest.")
    reader = None
    if ocr_targets:
        reader = load_ocr_reader()
    for row in rows:
        if row.get("kind") in ocr_targets:
            out_file = ocr_pdf_markdown(row, reader, dpi=dpi, pages=pages, force=force_ocr)
            if out_file is not None:
                attach_existing_markdown(row)
            continue
        if not should_extract(row, extract):
            continue
        out_file = extract_pdf_markdown(row)
        if out_file is not None:
            row["markdown"] = str(out_file.relative_to(ROOT)).replace("\\", "/")
            attach_existing_markdown(row)
    manifest = {
        "base_path": str(SOURCE_BASE),
        "file_count": len(rows),
        "existing_count": sum(1 for row in rows if row.get("exists")),
        "total_size_bytes": sum(int(row["size_bytes"]) for row in rows),
        "extracted_count": sum(1 for row in rows if row.get("markdown")),
        "needs_ocr_count": sum(1 for row in rows if row.get("needs_ocr")),
        "files": rows,
    }
    if write:
        MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        INDEX_FILE.write_text(render_index(manifest), encoding="utf-8")
    return manifest


def render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# 冲刺资料导入",
        "",
        f"- 来源目录：`{manifest.get('base_path')}`",
        f"- 文件数：{manifest.get('file_count', 0)}",
        f"- 存在文件：{manifest.get('existing_count', 0)}",
        f"- 总大小：{float(manifest.get('total_size_bytes', 0)) / 1024 / 1024:.2f} MB",
        f"- 已抽取：{manifest.get('extracted_count', 0)}",
        f"- 需 OCR：{manifest.get('needs_ocr_count', 0)}",
        f"- 索引：`{INDEX_FILE.relative_to(ROOT)}`",
        f"- 清单：`{MANIFEST_FILE.relative_to(ROOT)}`",
        "",
        "## 文件",
    ]
    for row in manifest.get("files", []):
        status = "缺失" if not row.get("exists") else ("需OCR" if row.get("needs_ocr") else "可读文本")
        lines.append(f"- {row['kind_label']}：{row['relative_path']} -> {row.get('markdown') or '仅索引'}（{status}）")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import sprint materials into references/internal/sprint-materials.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--extract", choices=["none", "selected", "all"], default="selected")
    parser.add_argument(
        "--ocr",
        action="append",
        default=[],
        help="OCR target kind or group. Use one or more of: small, all, mnemonic, gold-points, mock-exam, csf-risk, activities, sprint-guide.",
    )
    parser.add_argument("--force-ocr", action="store_true", help="Re-run OCR even when a markdown output already exists.")
    parser.add_argument("--dpi", type=int, default=220, help="OCR render DPI. Higher is slower but may improve recognition.")
    parser.add_argument("--pages", default=None, help="Optional OCR page range, e.g. 1-3 or 1,3,5-8.")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()

    try:
        ocr_targets = normalize_ocr_targets(args.ocr)
    except ValueError as exc:
        parser.error(str(exc))
    if ocr_targets and not args.write:
        parser.error("--ocr requires --write because OCR creates markdown files and refreshes the manifest.")
    manifest = build_manifest(
        write=args.write,
        extract=args.extract,
        ocr_targets=ocr_targets,
        force_ocr=bool(args.force_ocr),
        dpi=int(args.dpi),
        pages=args.pages,
    )
    if args.format == "json":
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(manifest))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
