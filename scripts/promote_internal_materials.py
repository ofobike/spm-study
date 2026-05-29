#!/usr/bin/env python3
"""Promote vetted internal practice and recitation materials into formal assets."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_DIR = ROOT / "assets" / "questions"
CHAPTERS_DIR = QUESTIONS_DIR / "chapters"
CASE_STUDIES_FILE = QUESTIONS_DIR / "case_studies.json"
INDEX_FILE = QUESTIONS_DIR / "index.json"
CONFIG_FILE = QUESTIONS_DIR / "config.json"
INTERNAL_CHAPTER_FILE = ROOT / "references" / "internal" / "chapter-practice" / "structured" / "candidate_questions.json"
INTERNAL_RECITATION_DIR = ROOT / "references" / "internal" / "case-special" / "structured"
PROMOTION_REPORT_FILE = ROOT / "references" / "internal" / "formal-promotion-report.json"

QUESTION_SOURCE = "2025新版系规千题闯关-正式入库"
CASE_SOURCE = "2025新版系规案例背诵-正式入库"
CHOICES = ("A", "B", "C", "D")
SUSPICIOUS_DISTRACTOR_REPLACEMENTS = {
    "军事建设": "科技建设",
    "军事安全": "信息安全",
    "军事训练": "人员培训",
    "军事基地": "基础设施",
    "军事政策": "政策规范",
    "军事服务": "公共服务",
    "军事生产": "生产管理",
    "军事技术": "信息技术",
    "军事": "科技",
}


def load_json(path: Path, default: Any | None = None) -> Any:
    if default is not None and not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def option_body(option: Any) -> str:
    return re.sub(r"^[A-Da-d][\.\、:：\)]\s*", "", str(option or "")).strip()


def clean_tags(values: list[str]) -> list[str]:
    tags: list[str] = []
    for value in values:
        tag = str(value or "").strip()
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:5]


def replace_suspicious_terms(text: str) -> str:
    fixed = str(text or "")
    for bad, replacement in SUSPICIOUS_DISTRACTOR_REPLACEMENTS.items():
        fixed = fixed.replace(bad, replacement)
    return fixed


def candidate_quality_score(question: dict[str, Any]) -> tuple[int, int, str]:
    text = f"{question.get('question', '')} {question.get('explanation', '')}"
    hard_markers = sum(1 for term in ("不正确", "不包括", "不属于", "最恰当", "核心", "规划", "治理", "场景") if term in text)
    return (hard_markers, len(normalize_text(text)), str(question.get("id") or ""))


def infer_difficulty(question: dict[str, Any]) -> str:
    markers, text_len, _ = candidate_quality_score(question)
    if markers >= 3 or text_len >= 220:
        return "hard"
    if markers >= 1 or text_len >= 120:
        return "medium"
    return "easy"


def is_valid_candidate(question: dict[str, Any], duplicate_texts: set[str]) -> tuple[bool, str | None]:
    text = normalize_text(str(question.get("question") or ""))
    if not text or text in duplicate_texts:
        return False, "duplicate_or_empty_question"
    if len(text) < 8:
        return False, "short_question"
    options = question.get("options")
    if not isinstance(options, list) or len(options) != 4:
        return False, "option_count"
    bodies = [option_body(option) for option in options]
    if len(set(bodies)) != 4 or any(not body for body in bodies):
        return False, "duplicate_options"
    if question.get("answer") not in CHOICES:
        return False, "invalid_answer"
    if len(normalize_text(str(question.get("explanation") or ""))) < 30:
        return False, "short_explanation"
    return True, None


def formal_question(candidate: dict[str, Any], new_id: str) -> dict[str, Any]:
    chapter_title = str(candidate.get("chapter_title") or candidate.get("chapter") or "章节知识点").strip()
    difficulty = infer_difficulty(candidate)
    return {
        "id": new_id,
        "question": replace_suspicious_terms(candidate["question"]),
        "options": [replace_suspicious_terms(option) for option in candidate["options"]],
        "answer": candidate["answer"],
        "explanation": replace_suspicious_terms(candidate["explanation"]),
        "chapter": candidate["chapter"],
        "source": QUESTION_SOURCE,
        "question_type": "single_choice",
        "difficulty": difficulty,
        "section": chapter_title,
        "knowledge_point": chapter_title,
        "source_ref": candidate.get("source_ref") or "references/internal/chapter-practice/2025新版系规千题闯关-解析版.md#正式入库",
        "tags": clean_tags([chapter_title, "内部章节习题", "正式入库", difficulty]),
        "candidate_source_id": candidate.get("id"),
    }


def promote_chapter_questions(per_chapter: int, write: bool) -> dict[str, Any]:
    candidates = load_json(INTERNAL_CHAPTER_FILE, [])
    candidates_by_chapter: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        candidates_by_chapter[int(candidate.get("chapter_no") or 0)].append(candidate)

    chapter_files = [CHAPTERS_DIR / f"chapter_{chapter_no:02d}.json" for chapter_no in range(1, 25)]
    existing_by_chapter = {path: load_json(path, []) for path in chapter_files}
    all_existing = [question for rows in existing_by_chapter.values() for question in rows]
    answer_counts = Counter(str(question.get("answer") or "") for question in all_existing)
    planned_total = len(all_existing) + per_chapter * 24
    target_each = planned_total // 4
    answer_deficits = {letter: max(0, target_each - answer_counts.get(letter, 0)) for letter in CHOICES}
    existing_texts = {normalize_text(str(question.get("question") or "")) for question in all_existing}
    promoted_source_ids = {
        str(question.get("candidate_source_id"))
        for question in all_existing
        if question.get("source") == QUESTION_SOURCE and question.get("candidate_source_id")
    }

    report = {
        "source": str(INTERNAL_CHAPTER_FILE.relative_to(ROOT)),
        "mode": "write" if write else "dry_run",
        "target_new_per_chapter": per_chapter,
        "added_total": 0,
        "added_by_chapter": {},
        "answer_distribution_before": dict(answer_counts),
        "answer_deficits_target": answer_deficits,
        "skipped": Counter(),
        "sample_added_ids": [],
    }

    for chapter_no in range(1, 25):
        path = CHAPTERS_DIR / f"chapter_{chapter_no:02d}.json"
        existing_rows = list(existing_by_chapter[path])
        existing_promoted = sum(1 for question in existing_rows if question.get("source") == QUESTION_SOURCE)
        needed = max(0, per_chapter - existing_promoted)
        if needed == 0:
            report["added_by_chapter"][str(chapter_no)] = 0
            continue

        pools: dict[str, list[dict[str, Any]]] = {letter: [] for letter in CHOICES}
        local_seen = set(existing_texts)
        for candidate in candidates_by_chapter.get(chapter_no, []):
            source_id = str(candidate.get("id") or "")
            if source_id in promoted_source_ids:
                report["skipped"]["already_promoted"] += 1
                continue
            valid, reason = is_valid_candidate(candidate, local_seen)
            if not valid:
                report["skipped"][reason or "invalid"] += 1
                continue
            pools[str(candidate["answer"])].append(candidate)
            local_seen.add(normalize_text(str(candidate.get("question") or "")))

        for rows in pools.values():
            rows.sort(key=candidate_quality_score, reverse=True)

        added: list[dict[str, Any]] = []
        next_index = len(existing_rows) + 1
        while len(added) < needed:
            available = [letter for letter in CHOICES if pools[letter]]
            if not available:
                break
            letter = max(available, key=lambda item: (answer_deficits.get(item, 0), len(pools[item])))
            candidate = pools[letter].pop(0)
            new_id = f"ch{chapter_no:02d}_q{next_index:03d}"
            next_index += 1
            question = formal_question(candidate, new_id)
            added.append(question)
            existing_texts.add(normalize_text(str(question["question"])))
            promoted_source_ids.add(str(candidate.get("id")))
            answer_counts[letter] += 1
            answer_deficits[letter] = max(0, answer_deficits.get(letter, 0) - 1)
            if len(report["sample_added_ids"]) < 20:
                report["sample_added_ids"].append(new_id)

        if write and added:
            save_json(path, existing_rows + added)
        report["added_by_chapter"][str(chapter_no)] = len(added)
        report["added_total"] += len(added)

    report["answer_distribution_after"] = dict(answer_counts)
    report["skipped"] = dict(report["skipped"])
    return report


def is_valid_recitation_item(item: dict[str, Any], seen_texts: set[str]) -> bool:
    question = normalize_text(str(item.get("question") or ""))
    answer = normalize_text(str(item.get("answer") or ""))
    if len(question) < 6 or len(answer) < 4:
        return False
    if question in seen_texts:
        return False
    return True


def formal_recitation_case(chapter_no: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    chapter_title = str(rows[0].get("chapter_title") or f"第{chapter_no}章").strip()
    questions = []
    for index, item in enumerate(rows, start=1):
        questions.append(
            {
                "id": f"cs_recite_ch{chapter_no:02d}_q{index}",
                "question": item["question"],
                "answer": item["answer"],
                "explanation": "参考答案来自2025新版系规案例背诵有答案版，用于主观题采分点训练。",
                "question_type": "short_answer",
                "score": 5,
                "source_ref": item.get("source_ref"),
                "candidate_source_id": item.get("id"),
            }
        )
    return {
        "id": f"cs_recite_ch{chapter_no:02d}",
        "chapter": chapter_no,
        "chapters": [chapter_no],
        "difficulty": "medium",
        "total_score": sum(int(question.get("score", 0) or 0) for question in questions),
        "title": f"第{chapter_no}章{chapter_title}案例背诵采分点训练",
        "scenario": f"本案例来自2025新版系规案例专题有答案版，围绕{chapter_title}常见案例采分点进行主观题默写训练。请按考试案例题方式分点作答，尽量写出关键词、措施和闭环。",
        "questions": questions,
        "source": CASE_SOURCE,
    }


def promote_recitation_cases(items_per_chapter: int, write: bool) -> dict[str, Any]:
    case_data = load_json(CASE_STUDIES_FILE, {"case_studies": []})
    cases = list(case_data.get("case_studies") or [])
    existing_case_ids = {str(case.get("id") or "") for case in cases}
    report = {
        "source": str(INTERNAL_RECITATION_DIR.relative_to(ROOT)),
        "mode": "write" if write else "dry_run",
        "target_items_per_chapter": items_per_chapter,
        "added_cases": 0,
        "added_sub_questions": 0,
        "skipped_existing_cases": 0,
        "skipped_invalid_items": 0,
        "sample_added_case_ids": [],
    }

    new_cases: list[dict[str, Any]] = []
    for chapter_no in range(1, 25):
        case_id = f"cs_recite_ch{chapter_no:02d}"
        if case_id in existing_case_ids:
            report["skipped_existing_cases"] += 1
            continue
        path = INTERNAL_RECITATION_DIR / f"chapter_{chapter_no:02d}.json"
        items = load_json(path, [])
        seen_texts: set[str] = set()
        valid_items = []
        for item in items:
            if is_valid_recitation_item(item, seen_texts):
                valid_items.append(item)
                seen_texts.add(normalize_text(str(item.get("question") or "")))
            else:
                report["skipped_invalid_items"] += 1
        valid_items.sort(key=lambda item: (len(normalize_text(str(item.get("answer") or ""))), str(item.get("id") or "")), reverse=True)
        selected = valid_items[:items_per_chapter]
        if not selected:
            continue
        case = formal_recitation_case(chapter_no, selected)
        new_cases.append(case)
        report["added_cases"] += 1
        report["added_sub_questions"] += len(case["questions"])
        if len(report["sample_added_case_ids"]) < 10:
            report["sample_added_case_ids"].append(case_id)

    if write and new_cases:
        case_data["case_studies"] = cases + new_cases
        case_data["total_case_studies"] = len(case_data["case_studies"])
        case_data["total_sub_questions"] = sum(len(case.get("questions") or []) for case in case_data["case_studies"])
        case_data["last_updated"] = date.today().isoformat()
        save_json(CASE_STUDIES_FILE, case_data)
    return report


def refresh_index_and_config(write: bool) -> dict[str, Any]:
    by_chapter = {}
    total_questions = 0
    for chapter_no in range(1, 25):
        rows = load_json(CHAPTERS_DIR / f"chapter_{chapter_no:02d}.json", [])
        by_chapter[f"chapter_{chapter_no:02d}"] = len(rows)
        total_questions += len(rows)

    case_data = load_json(CASE_STUDIES_FILE, {"case_studies": []})
    total_cases = len(case_data.get("case_studies") or [])
    total_sub_questions = sum(len(case.get("questions") or []) for case in case_data.get("case_studies") or [])
    today_text = date.today().isoformat()

    index_data = load_json(INDEX_FILE, {})
    index_data.update(
        {
            "total_questions": total_questions,
            "total_cases": total_cases,
            "total_sub_questions": total_sub_questions,
            "by_chapter": by_chapter,
            "case_studies_file": "case_studies.json",
            "last_updated": today_text,
        }
    )

    config_data = load_json(CONFIG_FILE, {})
    config_data["questions_per_chapter"] = min(by_chapter.values()) if by_chapter else 0
    config_data["last_updated"] = today_text

    if write:
        save_json(INDEX_FILE, index_data)
        save_json(CONFIG_FILE, config_data)

    return {
        "total_questions": total_questions,
        "total_cases": total_cases,
        "total_sub_questions": total_sub_questions,
        "by_chapter": by_chapter,
        "questions_per_chapter": config_data["questions_per_chapter"],
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    question_report = promote_chapter_questions(args.questions_per_chapter, args.write)
    recitation_report = promote_recitation_cases(args.case_items_per_chapter, args.write)
    index_report = refresh_index_and_config(args.write)
    report = {
        "updated_at": date.today().isoformat(),
        "mode": "write" if args.write else "dry_run",
        "chapter_questions": question_report,
        "case_recitation": recitation_report,
        "index": index_report,
        "next_checks": [
            "python scripts/validate_questions.py",
            "python scripts/study.py audit --format markdown",
            "python scripts/study.py regression --format markdown",
        ],
    }
    if args.write:
        save_json(PROMOTION_REPORT_FILE, report)
    return report


def render_markdown(report: dict[str, Any]) -> str:
    question_report = report["chapter_questions"]
    recitation_report = report["case_recitation"]
    index_report = report["index"]
    lines = [
        "# 内部资料正式入库",
        "",
        f"- 模式：{report['mode']}",
        f"- 新增章节选择题：{question_report['added_total']}",
        f"- 新增案例背诵正式案例：{recitation_report['added_cases']}",
        f"- 新增案例子问题：{recitation_report['added_sub_questions']}",
        f"- 正式章节题总数：{index_report['total_questions']}",
        f"- 正式案例总数：{index_report['total_cases']}",
        f"- 正式案例子问题：{index_report['total_sub_questions']}",
        f"- 每章最低题量：{index_report['questions_per_chapter']}",
        "",
        "## 答案分布",
        f"- 入库前：{question_report['answer_distribution_before']}",
        f"- 入库后：{question_report['answer_distribution_after']}",
        "",
        "## 跳过项",
        f"- 章节题：{question_report['skipped'] or '无'}",
        f"- 已存在案例：{recitation_report['skipped_existing_cases']}",
        f"- 无效案例背诵项：{recitation_report['skipped_invalid_items']}",
        "",
        "## 下一步校验",
    ]
    lines.extend(f"- {command}" for command in report["next_checks"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote vetted internal materials into formal question assets.")
    parser.add_argument("--write", action="store_true", help="Write promoted assets. Without this flag, run a dry-run preview.")
    parser.add_argument("--questions-per-chapter", type=int, default=20, help="Target promoted internal chapter-practice questions per chapter.")
    parser.add_argument("--case-items-per-chapter", type=int, default=5, help="Number of recitation prompts to promote as formal case sub-questions per chapter.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    report = build_report(args)
    if args.format == "markdown":
        print(render_markdown(report))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
