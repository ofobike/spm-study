#!/usr/bin/env python
"""从 ZFX 全程班扫描 PDF 中提取文本，输出为 markdown。

使用 easyocr 进行中文 OCR，支持增量提取和按页码范围提取。

用法:
    python scripts/extract_zfx.py                          # 提取所有资料
    python scripts/extract_zfx.py --source morning         # 只提取晨读默写本
    python scripts/extract_zfx.py --source homework        # 只提取课后作业
    python scripts/extract_zfx.py --source case            # 只提取案例通
    python scripts/extract_zfx.py --source essay           # 只提取论文集
    python scripts/extract_zfx.py --source yibentong       # 只提取一本通
    python scripts/extract_zfx.py --pages 1-10             # 只提取第1-10页
    python scripts/extract_zfx.py --dpi 300                # 使用更高 DPI
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Error: PyMuPDF not installed. Run: pip install PyMuPDF")
    sys.exit(1)

try:
    import easyocr
except ImportError:
    print("Error: easyocr not installed. Run: pip install easyocr")
    sys.exit(1)

import numpy as np
from PIL import Image

# ZFX 资料路径配置
ZFX_BASE = r"F:\备份项目\1、2025第2版 ZFX全程班"

SOURCES = {
    "yibentong": {
        "name": "一本通",
        "path": os.path.join(
            ZFX_BASE,
            "0 电子资料",
            "__001-【一本通（直播课件合集）】-25年（第2版）",
            "_系规-第2版-一本通（25年课程 郑房新老师）V2.1(完整版-可打印-不包含题目）.pdf",
        ),
        "output": "yibentong",
        "description": "直播课件合集，覆盖24章核心知识点",
    },
    "homework": {
        "name": "课后作业",
        "path": os.path.join(
            ZFX_BASE,
            "0 电子资料",
            "__002-【课后作业（有答案+无答案）】-25年（第2版）",
            "_【有答案版】系规-第2版-课后作业（25年课程 郑房新老师-完整版-可打印）V1.3.pdf",
        ),
        "output": "homework",
        "description": "按章节的练习题（有答案版）",
    },
    "morning": {
        "name": "晨读默写本",
        "path": os.path.join(
            ZFX_BASE,
            "0 电子资料",
            "__004-【晨读默写本（1-24章）】-25年（第2版）",
            "【有答案版】系规晨读-郑房新老师-2025年课程V1.2【花费时间‖免费获取：cunlove.cn】.pdf",
        ),
        "output": "morning",
        "description": "1-24章填空式背诵材料",
    },
    "essay": {
        "name": "论文集",
        "path": os.path.join(
            ZFX_BASE,
            "0 电子资料",
            "__005-【论文集（完整版）】-25年（第2版）",
            "系规第2版【论文集（含基础，题目和范文）】-郑房新老师-2025年课程V2.1（可打印）【不易整理‖请关注：CunWorkNotes】.pdf",
        ),
        "output": "essay",
        "description": "论文基础知识、题目和范文",
    },
    "essay_mock": {
        "name": "论文模拟题",
        "path": os.path.join(
            ZFX_BASE,
            "0 电子资料",
            "__005-【论文集（完整版）】-25年（第2版）",
            "02-系规第2版【论文集】02-论文模拟题-郑房新老师-2025年课程V1.3.pdf",
        ),
        "output": "essay_mock",
        "description": "论文模拟练习题",
    },
    "case": {
        "name": "案例通",
        "path": os.path.join(
            ZFX_BASE,
            "0 电子资料",
            "__006-【案例通（完整版）】-25年（第2版）",
            "_【有答案版】系规-第2版-案例通（25年课程 郑房新老师）V1.2(1).pdf",
        ),
        "output": "case",
        "description": "案例分析专项训练（有答案版）",
    },
}

# 输出目录
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "references" / "zfx"
PROGRESS_FILE = OUTPUT_DIR / ".extraction_progress.json"


def load_progress():
    """加载提取进度。"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    """保存提取进度。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def parse_page_range(page_str, max_pages):
    """解析页码范围，如 '1-10' 或 '5'。"""
    if not page_str:
        return list(range(max_pages))
    if "-" in page_str:
        start, end = page_str.split("-", 1)
        start = max(0, int(start) - 1)
        end = min(max_pages, int(end))
        return list(range(start, end))
    else:
        page = int(page_str) - 1
        if 0 <= page < max_pages:
            return [page]
        else:
            print(f"Warning: page {page_str} out of range (1-{max_pages})")
            return []


def ocr_pdf(pdf_path, page_indices, dpi=200, reader=None):
    """对 PDF 指定页面进行 OCR。

    Args:
        pdf_path: PDF 文件路径
        page_indices: 要提取的页面索引列表
        dpi: 图像分辨率
        reader: easyocr.Reader 实例（可复用）

    Returns:
        list of (page_num, text) 元组
    """
    if reader is None:
        print("Initializing easyocr reader (first time may download models)...")
        reader = easyocr.Reader(["ch_sim", "en"], gpu=False)

    doc = fitz.open(pdf_path)
    results = []

    for i, page_idx in enumerate(page_indices):
        if page_idx >= doc.page_count:
            continue

        page = doc[page_idx]
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_array = np.array(img)

        ocr_results = reader.readtext(img_array)
        text_blocks = [text for (_, text, _) in ocr_results]
        page_text = "\n".join(text_blocks)

        results.append((page_idx + 1, page_text))

        # Progress indicator
        pct = (i + 1) / len(page_indices) * 100
        print(f"\r  OCR page {page_idx + 1}/{doc.page_count} ({pct:.0f}%)", end="", flush=True)

    print()
    doc.close()
    return results


def save_as_markdown(source_key, source_info, page_texts, output_dir):
    """将 OCR 结果保存为 markdown 文件。

    每个 PDF 保存为一个 markdown 文件，包含所有页面的文本。
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{source_info['output']}.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# {source_info['name']}\n\n")
        f.write(f"> 来源：郑房新老师 2025年第2版全程班\n")
        f.write(f"> 说明：{source_info['description']}\n")
        f.write(f"> OCR 提取，可能存在识别错误，请以原 PDF 为准\n\n")
        f.write("---\n\n")

        for page_num, text in page_texts:
            if text.strip():
                f.write(f"## 第 {page_num} 页\n\n")
                f.write(text.strip())
                f.write("\n\n---\n\n")

    return output_file


def extract_source(source_key, source_info, page_range_str=None, dpi=200, reader=None):
    """提取单个资料的文本。"""
    pdf_path = source_info["path"]

    if not os.path.exists(pdf_path):
        print(f"  File not found: {pdf_path}")
        return None

    doc = fitz.open(pdf_path)
    max_pages = doc.page_count
    doc.close()

    page_indices = parse_page_range(page_range_str, max_pages)
    if not page_indices:
        page_indices = list(range(max_pages))

    print(f"  Pages: {max_pages}, extracting {len(page_indices)} pages at DPI {dpi}")

    page_texts = ocr_pdf(pdf_path, page_indices, dpi=dpi, reader=reader)
    output_file = save_as_markdown(source_key, source_info, page_texts, OUTPUT_DIR)

    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="从 ZFX 全程班扫描 PDF 中提取文本"
    )
    parser.add_argument(
        "--source",
        choices=list(SOURCES.keys()),
        help="指定要提取的资料（默认全部）",
    )
    parser.add_argument(
        "--pages",
        help="页码范围，如 '1-10' 或 '5'",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="图像分辨率（默认 200）",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有可用资料",
    )

    args = parser.parse_args()

    if args.list:
        print("Available sources:")
        for key, info in SOURCES.items():
            exists = "✓" if os.path.exists(info["path"]) else "✗"
            print(f"  {exists} {key:15s} - {info['name']} ({info['description']})")
        return

    print(f"ZFX OCR Extractor")
    print(f"Output directory: {OUTPUT_DIR}")
    print()

    # Initialize reader once
    print("Initializing easyocr reader...")
    reader = easyocr.Reader(["ch_sim", "en"], gpu=False)
    print()

    if args.source:
        sources = {args.source: SOURCES[args.source]}
    else:
        sources = SOURCES

    for key, info in sources.items():
        print(f"Extracting: {info['name']}")
        start_time = time.time()

        output_file = extract_source(
            key, info, page_range_str=args.pages, dpi=args.dpi, reader=reader
        )

        elapsed = time.time() - start_time
        if output_file:
            print(f"  Saved to: {output_file} ({elapsed:.1f}s)")
        print()

    print("Done!")


if __name__ == "__main__":
    main()
