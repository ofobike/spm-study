#!/usr/bin/env python3
"""Update generated asset statistics in SKILL.md."""

from __future__ import annotations

import json
import re
import argparse
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILL_FILE = ROOT / "SKILL.md"
QUESTIONS_DIR = ROOT / "assets" / "questions"
CHAPTERS_DIR = QUESTIONS_DIR / "chapters"
PAST_EXAMS_FILE = QUESTIONS_DIR / "past_exams.json"
STANDARDS_TRAINING_FILE = QUESTIONS_DIR / "standards_training.json"
SPRINT_TRAINING_FILE = QUESTIONS_DIR / "sprint_training.json"
SEARCH_INDEX_FILE = ROOT / "assets" / "search" / "index.json"
PROFILE_FILE = ROOT / "assets" / "profile" / "learner_profile.json"
VIP_MANIFEST_FILE = ROOT / "references" / "internal" / "vip-materials" / "manifest.json"
SPRINT_MANIFEST_FILE = ROOT / "references" / "internal" / "sprint-materials" / "manifest.json"
CHAPTER_PRACTICE_INDEX_FILE = ROOT / "references" / "internal" / "chapter-practice" / "structured" / "index.md"
CASE_RECITATION_DIR = ROOT / "references" / "internal" / "case-special" / "structured"

SUMMARY_START = "<!-- ASSET_SUMMARY_START -->"
SUMMARY_END = "<!-- ASSET_SUMMARY_END -->"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def count_chapter_questions() -> tuple[int, dict[str, int]]:
    counts: dict[str, int] = {}
    total = 0
    for path in sorted(CHAPTERS_DIR.glob("chapter_*.json")):
        rows = load_json(path, [])
        count = len(rows) if isinstance(rows, list) else 0
        counts[path.stem] = count
        total += count
    return total, counts


def count_case_studies() -> tuple[int, int]:
    data = load_json(QUESTIONS_DIR / "case_studies.json", {})
    rows = data.get("case_studies") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return 0, 0
    sub_questions = sum(len(row.get("questions", [])) for row in rows if isinstance(row, dict))
    return len(rows), sub_questions


def count_promoted_chapter_questions() -> int | None:
    total = 0
    found = False
    for path in sorted(CHAPTERS_DIR.glob("chapter_*.json")):
        rows = load_json(path, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            tags = [str(tag) for tag in row.get("tags", [])]
            source = str(row.get("source") or "")
            if "正式入库" in tags or "正式入库" in source:
                total += 1
                found = True
    return total if found else None


def count_promoted_recitation_cases() -> int:
    data = load_json(QUESTIONS_DIR / "case_studies.json", {})
    rows = data.get("case_studies") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        return 0
    return sum(1 for row in rows if isinstance(row, dict) and str(row.get("source") or "") == "2025新版系规案例背诵-正式入库")


def count_candidate_questions_from_index() -> int | None:
    if not CHAPTER_PRACTICE_INDEX_FILE.exists():
        return None
    text = CHAPTER_PRACTICE_INDEX_FILE.read_text(encoding="utf-8")
    match = re.search(r"候选题数[:：]\s*(\d+)", text)
    return int(match.group(1)) if match else None


def count_case_recitation_items() -> int | None:
    path = CASE_RECITATION_DIR / "recitation_items.json"
    rows = load_json(path, None)
    if isinstance(rows, list):
        return len(rows)
    return None


def manifest_counts(path: Path) -> tuple[int, int]:
    data = load_json(path, {})
    rows = data.get("items") or data.get("materials") or data.get("files") or []
    if not isinstance(rows, list):
        return 0, 0
    indexed = len(rows)
    extracted = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        output = row.get("output") or row.get("output_path") or row.get("markdown") or row.get("markdown_path") or row.get("extracted_path")
        if output:
            extracted += 1
        elif row.get("extracted") is True:
            extracted += 1
    return indexed, extracted


def past_exam_2024_summary(past_exam: dict[str, Any]) -> str | None:
    choices = past_exam.get("choice_questions", [])
    cases = past_exam.get("case_studies", [])
    papers = past_exam.get("paper_topics", [])
    if not isinstance(choices, list):
        choices = []
    if not isinstance(cases, list):
        cases = []
    if not isinstance(papers, list):
        papers = []
    choice_count = sum(1 for row in choices if isinstance(row, dict) and row.get("year") == 2024)
    case_count = sum(1 for row in cases if isinstance(row, dict) and row.get("year") == 2024)
    paper_count = sum(1 for row in papers if isinstance(row, dict) and row.get("year") == 2024)
    warnings = past_exam.get("stats", {}).get("warnings", {})
    warning_text = ""
    if isinstance(warnings, dict):
        broken = []
        for items in warnings.values():
            if isinstance(items, list):
                broken.extend(str(item).split(":", 1)[0] for item in items)
        focused = [item for item in ("choice_33", "choice_34", "choice_42") if item in broken]
        if focused:
            warning_text = f"，OCR 破损严重的题保留解析警告（{', '.join(focused)} 未入库）"
    if choice_count or case_count or paper_count:
        return f"其中 2024 下半年 OCR 抽取版保守入库 {choice_count} 道上午题、{case_count} 个案例、{paper_count} 个论文题目{warning_text}"
    return None


def covered_years_text(years: Any) -> str:
    if not isinstance(years, list) or not years:
        return "-"
    nums = sorted(int(year) for year in years)
    if len(nums) >= 2 and nums == list(range(nums[0], nums[-1] + 1)):
        return f"{nums[0]}-{nums[-1]}"
    return "、".join(str(year) for year in nums)


def source_type_summary(search_index: dict[str, Any]) -> str:
    source_counts = search_index.get("source_counts") or {}
    if not isinstance(source_counts, dict):
        return "覆盖教材章节、正式题库、案例、真题、标准规范、内部资料、VIP、冲刺资料和训练化资产"
    found = []
    for keys, label in (
        (("chapter_reference",), "教材章节"),
        (("chapter_question",), "正式题库"),
        (("case_study",), "案例"),
        (("past_exam", "past_exam_pdf", "past_exam_pdf_enhanced"), "真题"),
        (("standards_training", "standards_pdf", "standards_pdf_enhanced"), "标准规范"),
        (("exam_guide", "mindmap", "paper_special", "syllabus", "three_color_notes", "chapter_practice", "case_special"), "内部资料"),
        (("mock_bank", "mock_bank_enhanced"), "模拟题库"),
        (("vip_material",), "VIP"),
        (("sprint_material",), "冲刺资料"),
        (("sprint_training",), "训练化资产"),
    ):
        if any(int(source_counts.get(key, 0) or 0) > 0 for key in keys):
            found.append(label)
    return "覆盖" + "、".join(found) if found else "覆盖多类本地资料"


def profile_summary() -> str:
    profile = load_json(PROFILE_FILE, {})
    if not isinstance(profile, dict):
        return "记录考试目标、每日可学时间、薄弱科目/章节、目标分数和学习偏好"
    parts = ["记录考试目标、每日可学时间、薄弱科目/章节、目标分数和学习偏好"]
    updated = profile.get("updated_at")
    if updated:
        parts.append(f"最近更新 {updated}")
    return "；".join(parts)


def build_asset_summary() -> str:
    chapter_total, chapter_counts = count_chapter_questions()
    per_chapter_counts = sorted(Counter(chapter_counts.values()).items())
    if len(per_chapter_counts) == 1:
        per_chapter_text = f"每章 {per_chapter_counts[0][0]} 道"
    else:
        per_chapter_text = "各章题量不完全一致"

    case_count, sub_question_count = count_case_studies()
    past_exam = load_json(PAST_EXAMS_FILE, {})
    past_stats = past_exam.get("stats", {}) if isinstance(past_exam, dict) else {}
    standards = load_json(STANDARDS_TRAINING_FILE, {})
    standards_stats = standards.get("stats", {}) if isinstance(standards, dict) else {}
    sprint_training = load_json(SPRINT_TRAINING_FILE, {})
    sprint_stats = sprint_training.get("stats", {}) if isinstance(sprint_training, dict) else {}
    search_index = load_json(SEARCH_INDEX_FILE, {})

    promoted_chapter_questions = count_promoted_chapter_questions()
    candidate_questions = count_candidate_questions_from_index()
    recitation_candidates = count_case_recitation_items()
    promoted_cases = count_promoted_recitation_cases()
    vip_indexed, vip_extracted = manifest_counts(VIP_MANIFEST_FILE)
    sprint_indexed, sprint_extracted = manifest_counts(SPRINT_MANIFEST_FILE)

    years = covered_years_text(past_stats.get("years"))
    past_2024 = past_exam_2024_summary(past_exam)
    past_detail = f"覆盖 {years}"
    if past_2024:
        past_detail += f"；{past_2024}"

    skipped_standards = int(standards_stats.get("skipped_documents", 0) or 0)
    source_standards = int(standards_stats.get("source_documents", 0) or 0)
    standards_detail = f"其余 {skipped_standards} 个标准规范 PDF 因需 OCR 或文本过少暂不生成训练题" if skipped_standards else "所有索引文档均已结构化"

    lines = [
        SUMMARY_START,
        "",
        "正式题库：",
        f"- 章节选择题：{chapter_total} 道，{per_chapter_text}。",
        f"- 案例题：{case_count} 个案例，{sub_question_count} 个子问题。",
        (
            "- 历年真题训练库：`assets/questions/past_exams.json`，当前结构化 "
            f"{int(past_stats.get('choice_questions', 0) or 0)} 道上午选择题、"
            f"{int(past_stats.get('case_studies', 0) or 0)} 个下午案例、"
            f"{int(past_stats.get('paper_topics', 0) or 0)} 个论文题目；{past_detail}。"
        ),
        (
            "- 标准规范专项训练库：`assets/questions/standards_training.json`，当前结构化 "
            f"{int(standards_stats.get('structured_documents', 0) or 0)}/{source_standards} 个标准/法规文档、"
            f"{int(standards_stats.get('clauses', 0) or 0)} 条条款、"
            f"{int(standards_stats.get('questions', 0) or 0)} 道专项训练题；{standards_detail}。"
        ),
    ]

    if promoted_chapter_questions is not None:
        candidate_text = f"，剩余候选题约 {candidate_questions} 道" if candidate_questions is not None else ""
        lines.append(f"- 05 章节习题已筛选 {promoted_chapter_questions} 道正式入库{candidate_text}，候选题保留在 `references/internal/chapter-practice/structured/`。")
    else:
        lines.append("- 05 章节习题正式入库题与候选题保留在 `assets/questions/chapters/` 和 `references/internal/chapter-practice/structured/`。")

    recitation_text = f"，剩余采分点候选材料约 {recitation_candidates} 条" if recitation_candidates is not None else ""
    lines.append(f"- 06 案例专题已筛选 {promoted_cases} 个正式案例背诵题入库{recitation_text}，候选材料保留在 `references/internal/case-special/structured/`。")

    lines.extend(
        [
            f"- VIP 补充资料：`references/internal/vip-materials/`，当前索引 {vip_indexed} 个 PDF，精选抽取 {vip_extracted} 个 markdown；一本通、无答案练习题和三色笔记汇总版默认仅索引，避免重复和体量膨胀。",
            f"- 冲刺补充资料：`references/internal/sprint-materials/`，当前索引 {sprint_indexed} 个 PDF，抽取 {sprint_extracted} 个 markdown；扫描件由 EasyOCR 识别，仍作为补充资料源，不自动并入正式题库。",
            (
                "- 全资料检索索引：`assets/search/index.json`，当前 "
                f"{int(search_index.get('chunk_count', 0) or 0)} 个本地资料片段，{source_type_summary(search_index)}。"
            ),
            (
                "- 冲刺训练库：`assets/questions/sprint_training.json`，当前 "
                f"{int(sprint_stats.get('cards', 0) or 0)} 张背诵卡、"
                f"{int(sprint_stats.get('choice_questions', 0) or 0)} 道自编综合模考候选选择题、"
                f"{int(sprint_stats.get('case_prompts', 0) or 0)} 个案例采分点训练；来自冲刺资料 OCR/抽取文本，不等同正式题库或历年真题。"
            ),
            f"- 个人备考画像：`assets/profile/learner_profile.json`，{profile_summary()}；`plan`、`dashboard`、`sprint` 会读取画像自动调整题量和任务优先级；自然语言“保存到画像：我每天能学1小时，论文最弱，优先保过”会走 `profile-update`。",
            "",
            SUMMARY_END,
        ]
    )
    return "\n".join(lines)


def update_skill_summary(skill_text: str, summary: str) -> str:
    if SUMMARY_START in skill_text and SUMMARY_END in skill_text:
        pattern = re.compile(rf"{re.escape(SUMMARY_START)}.*?{re.escape(SUMMARY_END)}", re.S)
        return pattern.sub(summary, skill_text, count=1)

    heading = "## 当前资产"
    start = skill_text.index(heading) + len(heading)
    keep_heading = "\n已接入的 7 类 2025 新版资料:"
    next_heading = "\n## 入口选择"
    end = skill_text.index(keep_heading) if keep_heading in skill_text else skill_text.index(next_heading)
    return skill_text[:start] + "\n\n" + summary + "\n" + skill_text[end:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Update generated asset statistics in SKILL.md.")
    parser.add_argument("--check", action="store_true", help="Only check whether SKILL.md asset statistics are current.")
    args = parser.parse_args()

    skill_text = SKILL_FILE.read_text(encoding="utf-8")
    summary = build_asset_summary()
    updated = update_skill_summary(skill_text, summary)
    if args.check:
        if updated == skill_text:
            print("SKILL.md asset summary is current.")
            return 0
        print("SKILL.md asset summary is stale. Run: python scripts/update_skill_summary.py")
        return 1
    SKILL_FILE.write_text(updated, encoding="utf-8")
    print("Updated SKILL.md asset summary.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
