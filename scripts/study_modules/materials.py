from __future__ import annotations

import argparse
import json
from typing import Any

from study_modules.common import load_internal_json
from study_modules.settings import (
    BACKUP_PDFS_DIR,
    BACKUP_PDFS_MANIFEST,
    CASE_RECITATION_STRUCTURED_DIR,
    CHAPTER_PRACTICE_STRUCTURED_DIR,
    DEFAULT_CASE_CHAPTERS,
    DEFAULT_FOCUS_CHAPTERS,
    EXAM_GUIDE_FILE,
    INTERNAL_DIR,
    PAPER_SPECIAL_INDEX,
    SPRINT_MATERIALS_DIR,
    SPRINT_MATERIALS_MANIFEST,
    SYLLABUS_ANALYSIS_FILE,
    VIP_MATERIALS_DIR,
    VIP_MATERIALS_MANIFEST,
)
from study_utils import ROOT

def load_exam_guide() -> dict[str, Any]:
    return load_internal_json(EXAM_GUIDE_FILE, {})


def load_syllabus_analysis() -> dict[str, Any]:
    return load_internal_json(SYLLABUS_ANALYSIS_FILE, {})


def load_paper_special_index() -> dict[str, Any]:
    return load_internal_json(PAPER_SPECIAL_INDEX, {"documents": [], "rubric": {}, "framework": {}, "samples": []})



def exam_focus_chapters() -> list[int]:
    syllabus = load_syllabus_analysis()
    focus = syllabus.get("strategic_focus", {}).get("highest_priority_chapters")
    if isinstance(focus, list) and focus:
        return [int(item) for item in focus]
    return DEFAULT_FOCUS_CHAPTERS[:7]


def paper_range_chapters() -> list[int]:
    syllabus = load_syllabus_analysis()
    chapters = syllabus.get("strategic_focus", {}).get("paper_range_chapters")
    if isinstance(chapters, list) and chapters:
        return [int(item) for item in chapters]
    return list(range(4, 18))


def case_range_chapters_text() -> str:
    syllabus = load_syllabus_analysis()
    chapters = syllabus.get("strategic_focus", {}).get("case_range_chapters")
    if isinstance(chapters, list) and chapters:
        values = [int(item) for item in chapters]
        if values == list(range(min(values), max(values) + 1)):
            return f"{min(values)}-{max(values)}"
        return ",".join(str(item) for item in values)
    return DEFAULT_CASE_CHAPTERS


def guide_chapter_rows() -> list[dict[str, Any]]:
    guide = load_exam_guide()
    rows = guide.get("chapter_priorities", [])
    return rows if isinstance(rows, list) else []


def chapter_guide_row(chapter_no: int) -> dict[str, Any] | None:
    for row in guide_chapter_rows():
        if int(row.get("chapter", 0) or 0) == chapter_no:
            return row
    return None


def top_exam_priority_chapters(limit: int = 5) -> list[dict[str, Any]]:
    rows = [row for row in guide_chapter_rows() if int(row.get("importance", 0) or 0) >= 3]
    if not rows:
        return [{"chapter": chapter, "title": f"第{chapter}章", "importance": 3, "advice": "新版大纲重点章节。"} for chapter in DEFAULT_FOCUS_CHAPTERS[:limit]]
    return sorted(rows, key=lambda row: (-int(row.get("importance", 0) or 0), int(row.get("chapter", 0) or 0)))[:limit]


def build_exam_guide_payload(args: argparse.Namespace | None = None) -> dict[str, Any]:
    limit = int(getattr(args, "limit", 8) if args is not None else 8)
    guide = load_exam_guide()
    syllabus = load_syllabus_analysis()
    subjects = guide.get("exam_schedule", {}).get("subjects", [])
    return {
        "guide_source": guide.get("source"),
        "syllabus_source": syllabus.get("source"),
        "note": guide.get("note") or syllabus.get("note"),
        "exam_schedule": guide.get("exam_schedule", {}),
        "subject_ranges": syllabus.get("subject_ranges", {}),
        "strategic_focus": syllabus.get("strategic_focus", {}),
        "top_chapters": top_exam_priority_chapters(limit),
        "subjects": subjects,
        "paths": {
            "guide": str(EXAM_GUIDE_FILE.relative_to(ROOT)),
            "syllabus": str(SYLLABUS_ANALYSIS_FILE.relative_to(ROOT)),
        },
    }


def load_candidate_questions(chapter: int | None = None) -> list[dict[str, Any]]:
    if chapter:
        path = CHAPTER_PRACTICE_STRUCTURED_DIR / f"chapter_{int(chapter):02d}.json"
    else:
        path = CHAPTER_PRACTICE_STRUCTURED_DIR / "candidate_questions.json"
    return load_internal_json(path, [])


def build_candidate_practice_payload(args: argparse.Namespace) -> dict[str, Any]:
    questions = load_candidate_questions(args.chapter)
    limit = max(1, int(args.count))
    selected = questions[:limit]
    report = load_internal_json(CHAPTER_PRACTICE_STRUCTURED_DIR / "quality_report.json", {})
    return {
        "source": "2025新版系规千题闯关-解析版",
        "status": "candidate_only",
        "note": "候选题源仅用于预览和人工筛选，不写入正式题库、不记录学习进度。",
        "chapter": args.chapter,
        "total_available": len(questions),
        "quality_report": {
            "total": report.get("total"),
            "answer_distribution": report.get("answer_distribution"),
            "issue_counts": report.get("issue_counts"),
        },
        "questions": selected,
        "index_file": str((CHAPTER_PRACTICE_STRUCTURED_DIR / "index.md").relative_to(ROOT)),
    }


def load_vip_manifest() -> dict[str, Any]:
    return load_internal_json(VIP_MATERIALS_MANIFEST, {"files": []})


def load_sprint_materials_manifest() -> dict[str, Any]:
    return load_internal_json(SPRINT_MATERIALS_MANIFEST, {"files": []})


def build_vip_material_payload(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_vip_manifest()
    files = list(manifest.get("files", []))
    kind = getattr(args, "kind", "all") or "all"
    if kind != "all":
        files = [item for item in files if item.get("kind") == kind]
    keyword = str(getattr(args, "keyword", "") or "").strip()
    if keyword:
        files = [
            item
            for item in files
            if keyword in str(item.get("title") or "")
            or keyword in str(item.get("relative_path") or "")
            or keyword in str(item.get("kind_label") or "")
            or keyword in str(item.get("description") or "")
        ]
    limit = max(1, int(getattr(args, "limit", 10) or 10))
    rows = []
    for item in files[:limit]:
        preview: list[str] = []
        markdown = item.get("markdown")
        if markdown:
            md_path = ROOT / markdown
            if md_path.exists():
                text_lines = [
                    line.strip()
                    for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.startswith(">") and not line.startswith("#") and line != "---"
                ]
                preview = text_lines[: max(0, int(getattr(args, "preview_lines", 8) or 8))]
        rows.append({**item, "preview": preview})
    return {
        "source": str(VIP_MATERIALS_MANIFEST.relative_to(ROOT)),
        "index_file": str((VIP_MATERIALS_DIR / "index.md").relative_to(ROOT)),
        "base_path": manifest.get("base_path"),
        "kind": kind,
        "keyword": keyword,
        "total_files": manifest.get("file_count", len(manifest.get("files", []))),
        "total_size_mb": round(float(manifest.get("total_size_bytes", 0)) / 1024 / 1024, 2),
        "extracted_count": manifest.get("extracted_count", 0),
        "matched_count": len(files),
        "files": rows,
    }


def build_sprint_material_payload(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_sprint_materials_manifest()
    files = list(manifest.get("files", []))
    kind = getattr(args, "kind", "all") or "all"
    if kind != "all":
        files = [item for item in files if item.get("kind") == kind]
    keyword = str(getattr(args, "keyword", "") or "").strip()
    if keyword:
        files = [
            item
            for item in files
            if keyword in str(item.get("title") or "")
            or keyword in str(item.get("relative_path") or "")
            or keyword in str(item.get("kind_label") or "")
            or keyword in str(item.get("description") or "")
        ]
    limit = max(1, int(getattr(args, "limit", 10) or 10))
    rows = []
    for item in files[:limit]:
        preview: list[str] = []
        markdown = item.get("markdown")
        if markdown:
            md_path = ROOT / markdown
            if md_path.exists():
                text_lines = [
                    line.strip()
                    for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.startswith(">") and not line.startswith("#") and line != "---"
                ]
                preview = text_lines[: max(0, int(getattr(args, "preview_lines", 8) or 8))]
        rows.append({**item, "preview": preview})
    return {
        "source": str(SPRINT_MATERIALS_MANIFEST.relative_to(ROOT)),
        "index_file": str((SPRINT_MATERIALS_DIR / "index.md").relative_to(ROOT)),
        "base_path": manifest.get("base_path"),
        "kind": kind,
        "keyword": keyword,
        "total_files": manifest.get("file_count", len(manifest.get("files", []))),
        "existing_count": manifest.get("existing_count", 0),
        "total_size_mb": round(float(manifest.get("total_size_bytes", 0)) / 1024 / 1024, 2),
        "extracted_count": manifest.get("extracted_count", 0),
        "needs_ocr_count": manifest.get("needs_ocr_count", 0),
        "matched_count": len(files),
        "files": rows,
    }


def load_recitation_items(chapter: int | None = None) -> list[dict[str, Any]]:
    if chapter:
        path = CASE_RECITATION_STRUCTURED_DIR / f"chapter_{int(chapter):02d}.json"
    else:
        path = CASE_RECITATION_STRUCTURED_DIR / "recitation_items.json"
    return load_internal_json(path, [])


def build_recitation_payload(args: argparse.Namespace) -> dict[str, Any]:
    items = load_recitation_items(args.chapter)
    limit = max(1, int(args.count))
    selected = items[:limit]
    report = load_internal_json(CASE_RECITATION_STRUCTURED_DIR / "quality_report.json", {})
    return {
        "source": "有答案版/无答案版-系规案例背诵",
        "status": "candidate_only",
        "note": "用于案例默写和采分点候选预览；其中部分内容已正式入库，继续提升前需先做质量门禁和回归测试。",
        "chapter": args.chapter,
        "total_available": len(items),
        "quality_report": {
            "total": report.get("total"),
            "issue_counts": report.get("issue_counts"),
        },
        "items": selected,
        "show_answer": bool(args.show_answer),
        "index_file": str((CASE_RECITATION_STRUCTURED_DIR / "index.md").relative_to(ROOT)),
    }


BACKUP_CATEGORY_LABELS = {
    "past-exam": "历年真题",
    "standards": "标准规范库",
    "mock": "模拟题库",
    "all": "全部",
}


def load_backup_pdf_manifest() -> dict[str, Any]:
    return load_internal_json(BACKUP_PDFS_MANIFEST, {"files": []})



def build_backup_pdf_payload(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_backup_pdf_manifest()
    files = list(manifest.get("files", []))
    category = getattr(args, "category", "all") or "all"
    if category != "all":
        files = [item for item in files if item.get("category") == category]
    if getattr(args, "year", None):
        files = [item for item in files if int(item.get("year") or 0) == int(args.year)]
    if getattr(args, "subject", None):
        files = [item for item in files if str(args.subject) in str(item.get("subject") or "")]
    rows = sorted(files, key=lambda item: (str(item.get("category") or ""), int(item.get("year") or 0), str(item.get("title") or "")))
    limit = max(1, int(getattr(args, "limit", 20) or 20))
    return {
        "source": str(BACKUP_PDFS_MANIFEST.relative_to(ROOT)),
        "index_file": str((BACKUP_PDFS_DIR / "index.md").relative_to(ROOT)),
        "base_path": manifest.get("base_path"),
        "category": category,
        "category_label": BACKUP_CATEGORY_LABELS.get(category, category),
        "total_files": manifest.get("file_count", len(manifest.get("files", []))),
        "total_size_mb": round(float(manifest.get("total_size_bytes", 0)) / 1024 / 1024, 2),
        "extracted_count": manifest.get("extracted_count", 0),
        "needs_ocr_count": manifest.get("needs_ocr_count", 0),
        "matched_count": len(rows),
        "files": rows[:limit],
    }

def render_exam_guide_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 考试导航与大纲分析",
        "",
    ]
    if payload.get("note"):
        lines.append(f"> {payload['note']}")
        lines.append("")
    schedule = payload.get("exam_schedule", {})
    if schedule:
        lines.extend(
            [
                "## 考试安排",
                f"- 资格：{schedule.get('qualification', '系统规划与管理师')}（{schedule.get('level', '高级')}）",
                f"- 预测考试时间：{schedule.get('predicted_2025_h2_dates', '-')}",
                f"- 合格线参考：{schedule.get('full_score', 75)} 分满分，{schedule.get('pass_score', 45)} 分及格",
            ]
        )
        for subject in payload.get("subjects", []):
            lines.append(f"- {subject['name']}：{subject['content']}，{subject['duration_minutes']} 分钟，{subject['time_window']}")
        lines.append("")
    ranges = payload.get("subject_ranges", {})
    if ranges:
        lines.extend(
            [
                "## 大纲范围",
                f"- 综合知识：第{ranges.get('comprehensive', {}).get('chapters', '1-24')}章",
                f"- 案例分析：第{ranges.get('case_analysis', {}).get('chapters', '4-24')}章",
                f"- 论文：第{ranges.get('paper', {}).get('chapters', '4-17')}章",
                "",
            ]
        )
    lines.append("## 高优先级章节")
    for row in payload.get("top_chapters", []):
        lines.append(f"- 第{row['chapter']}章 {row['title']}：重要度 {row['importance']}，{row.get('advice', '')}")
    lines.extend(
        [
            "",
            "## 资料位置",
            f"- 学习指南：{payload['paths']['guide']}",
            f"- 大纲分析：{payload['paths']['syllabus']}",
        ]
    )
    return "\n".join(lines) + "\n"


def command_exam_guide(args: argparse.Namespace) -> int:
    payload = build_exam_guide_payload(args)
    if args.format == "markdown":
        print(render_exam_guide_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


INTERNAL_KIND_CONFIG = {
    "notes": {
        "label": "三色笔记",
        "index": INTERNAL_DIR / "three-color-notes" / "index.json",
        "description": "高频知识点补充和背诵清单",
    },
    "mindmap": {
        "label": "思维导图",
        "index": INTERNAL_DIR / "mindmaps" / "index.json",
        "description": "章节速览和知识结构导航",
    },
}


def build_internal_material_payload(args: argparse.Namespace) -> dict[str, Any]:
    kind = args.kind
    config = INTERNAL_KIND_CONFIG[kind]
    index = load_internal_json(config["index"], {"items": []})
    items = index.get("items", []) if isinstance(index, dict) else []
    if args.chapter:
        items = [item for item in items if int(item.get("chapter", 0) or 0) == int(args.chapter)]
    rows = []
    for item in items:
        md_path = ROOT / item["markdown"] if item.get("markdown") else None
        preview: list[str] = []
        if md_path and md_path.exists():
            text_lines = [
                line.strip()
                for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                if line.strip() and not line.startswith(">") and not line.startswith("#")
            ]
            preview = text_lines[: args.preview_lines]
        rows.append({**item, "preview": preview})
    return {
        "kind": kind,
        "label": config["label"],
        "description": config["description"],
        "index_file": str(config["index"].relative_to(ROOT)),
        "count": len(rows),
        "items": rows,
    }


def render_internal_material_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload['label']}",
        "",
        f"- 用途：{payload['description']}",
        f"- 索引：{payload['index_file']}",
        f"- 命中：{payload['count']}",
        "",
    ]
    for item in payload["items"]:
        lines.append(f"## 第{item['chapter']}章 {item['chapter_title']}")
        lines.append(f"- 抽取文本：{item.get('markdown') or '-'}")
        if item.get("asset"):
            lines.append(f"- 原始资源：{item['asset']}")
        lines.append(f"- 原始资料：{item.get('source')}")
        preview = item.get("preview") or []
        if preview:
            lines.append("- 预览：")
            lines.extend(f"  - {line}" for line in preview)
        lines.append("")
    return "\n".join(lines)


def command_internal_material(args: argparse.Namespace) -> int:
    payload = build_internal_material_payload(args)
    if args.format == "markdown":
        print(render_internal_material_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def render_vip_material_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# VIP材料",
        "",
        f"- 来源目录：{payload.get('base_path')}",
        f"- 索引：{payload['index_file']}",
        f"- 筛选：{payload.get('kind') or 'all'} {payload.get('keyword') or ''}".rstrip(),
        f"- 总文件：{payload['total_files']}，已抽取：{payload['extracted_count']}，命中：{payload['matched_count']}",
        f"- 总大小：{payload['total_size_mb']} MB",
        "",
    ]
    if not payload.get("files"):
        lines.append("没有匹配到 VIP 材料。")
        return "\n".join(lines) + "\n"
    for item in payload["files"]:
        lines.append(f"## {item.get('kind_label')}：{item.get('title')}")
        lines.append(f"- 原始文件：{item.get('relative_path')}")
        lines.append(f"- 页数：{item.get('page_count') or '-'}；文本量：{item.get('text_chars', 0)}；策略：{item.get('strategy')}")
        lines.append(f"- 抽取文本：{item.get('markdown') or '仅索引'}")
        if item.get("description"):
            lines.append(f"- 用途：{item['description']}")
        preview = item.get("preview") or []
        if preview:
            lines.append("- 预览：")
            lines.extend(f"  - {line}" for line in preview)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_vip_material(args: argparse.Namespace) -> int:
    payload = build_vip_material_payload(args)
    if args.format == "markdown":
        print(render_vip_material_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def render_sprint_material_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 冲刺资料",
        "",
        f"- 来源目录：{payload.get('base_path')}",
        f"- 索引：{payload['index_file']}",
        f"- 筛选：{payload.get('kind') or 'all'} {payload.get('keyword') or ''}".rstrip(),
        f"- 总文件：{payload['total_files']}，存在：{payload.get('existing_count', 0)}，已抽取：{payload['extracted_count']}，需OCR：{payload.get('needs_ocr_count', 0)}，命中：{payload['matched_count']}",
        f"- 总大小：{payload['total_size_mb']} MB",
        "> 说明：冲刺资料、押题资料和模拟题是补充资料源，不等同历年真题；扫描件需 OCR 后才适合进一步结构化。",
        "",
    ]
    if not payload.get("files"):
        lines.append("没有匹配到冲刺资料。")
        return "\n".join(lines) + "\n"
    for item in payload["files"]:
        lines.append(f"## {item.get('kind_label')}：{item.get('title')}")
        lines.append(f"- 原始文件：{item.get('relative_path')}")
        lines.append(
            f"- 页数：{item.get('page_count') or '-'}；文本量：{item.get('text_chars', 0)}；"
            f"需OCR：{'是' if item.get('needs_ocr') else '否'}；策略：{item.get('strategy')}"
        )
        lines.append(f"- 抽取文本：{item.get('markdown') or '仅索引'}")
        if item.get("sha1_prefix"):
            lines.append(f"- SHA1：{item.get('sha1_prefix')}")
        if item.get("description"):
            lines.append(f"- 用途：{item['description']}")
        preview = item.get("preview") or []
        if preview:
            lines.append("- 预览：")
            lines.extend(f"  - {line}" for line in preview)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_sprint_material(args: argparse.Namespace) -> int:
    payload = build_sprint_material_payload(args)
    if args.format == "markdown":
        print(render_sprint_material_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0

def render_candidate_practice_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 章节习题候选题源",
        "",
        f"> {payload['note']}",
        "",
        f"- 来源：{payload['source']}",
        f"- 章节：{payload['chapter'] if payload['chapter'] else '全部'}",
        f"- 可用候选题：{payload['total_available']}",
        f"- 索引：{payload['index_file']}",
    ]
    report = payload.get("quality_report") or {}
    if report:
        lines.append(f"- 总候选题：{report.get('total')}")
        lines.append(f"- 答案分布：{report.get('answer_distribution')}")
        lines.append(f"- 质量问题：{report.get('issue_counts') or '暂无'}")
    lines.append("")
    for index, question in enumerate(payload["questions"], start=1):
        lines.append(f"{index}. [{question['id']}] {question['question']}")
        for option in question.get("options", []):
            lines.append(f"   {option}")
        lines.append(f"   Answer: {question.get('answer')}")
        lines.append(f"   Explanation: {question.get('explanation')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_candidate_practice(args: argparse.Namespace) -> int:
    payload = build_candidate_practice_payload(args)
    if args.format == "markdown":
        print(render_candidate_practice_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def render_recitation_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 案例背诵训练",
        "",
        f"> {payload['note']}",
        "",
        f"- 来源：{payload['source']}",
        f"- 章节：{payload['chapter'] if payload['chapter'] else '全部'}",
        f"- 可用候选题：{payload['total_available']}",
        f"- 索引：{payload['index_file']}",
    ]
    report = payload.get("quality_report") or {}
    if report:
        lines.append(f"- 总候选题：{report.get('total')}")
        lines.append(f"- 质量问题：{report.get('issue_counts') or '暂无'}")
    lines.append("")
    for index, item in enumerate(payload["items"], start=1):
        lines.append(f"{index}. [{item['id']}] {item['question']}")
        if payload.get("show_answer"):
            lines.append("   参考答案/采分点：")
            for line in str(item.get("answer", "")).splitlines():
                lines.append(f"   - {line}")
        else:
            lines.append("   参考答案：隐藏；加 `--show-answer` 查看采分点。")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_recitation(args: argparse.Namespace) -> int:
    payload = build_recitation_payload(args)
    if args.format == "markdown":
        print(render_recitation_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def render_backup_pdf_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# F盘备份PDF：{payload['category_label']}",
        "",
        f"- 来源目录：`{payload.get('base_path')}`",
        f"- 索引：`{payload['index_file']}`",
        f"- 总 PDF：{payload['total_files']}，已抽取：{payload['extracted_count']}，需 OCR：{payload['needs_ocr_count']}，总大小：{payload['total_size_mb']} MB",
        f"- 当前匹配：{payload['matched_count']}",
        "",
        "## 文件",
    ]
    if not payload["files"]:
        lines.append("- 暂无匹配文件。")
    for item in payload["files"]:
        year = item.get("year") or "-"
        period = item.get("period") or ""
        subject = item.get("subject") or "-"
        status = "需OCR" if item.get("needs_ocr") else f"{item.get('text_chars', 0)}字"
        markdown = item.get("markdown") or "-"
        lines.append(f"- {item.get('title')} | {year}{period} | {subject} | {status}")
        lines.append(f"  `{markdown}`")
    return "\n".join(lines) + "\n"


def command_backup_pdfs(args: argparse.Namespace) -> int:
    payload = build_backup_pdf_payload(args)
    if args.format == "markdown":
        print(render_backup_pdf_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
