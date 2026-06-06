from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from pathlib import Path
from typing import Any

from study_modules.common import compact_text
from study_modules.settings import (
    PAPER_TOPICS,
    STOP_KNOWLEDGE_POINTS,
    STRONG_KNOWLEDGE_POINT_OVERRIDES,
    SUSPICIOUS_DISTRACTOR_REPLACEMENTS,
    WEAK_KNOWLEDGE_POINT_PATTERNS,
)
from study_utils import CHAPTERS_DIR, ROOT, chapter_no_from_label, load_all_questions, load_json, save_json


def normalize_text(text: str) -> str:
    return compact_text(text)


def is_weak_knowledge_point(point: str) -> bool:
    text = str(point or "").strip()
    if len(text) < 3:
        return True
    return any(pattern.match(text) for pattern in WEAK_KNOWLEDGE_POINT_PATTERNS)


def option_body(option: Any) -> str:
    text = str(option or "").strip()
    return re.sub(r"^[A-Da-d][\.\、:：\)]\s*", "", text).strip()


def add_audit_issue(issues: list[dict[str, Any]], severity: str, code: str, message: str, question: dict[str, Any] | None = None, detail: Any | None = None) -> None:
    issue = {"severity": severity, "code": code, "message": message}
    if question:
        issue["question_id"] = question.get("id")
        issue["chapter"] = question.get("chapter")
    if detail is not None:
        issue["detail"] = detail
    issues.append(issue)


def audit_questions_payload(questions: list[dict[str, Any]], limit: int, min_explanation_length: int) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    required = ["id", "chapter", "question", "options", "answer", "explanation", "difficulty", "section", "knowledge_point", "source_ref", "tags"]
    answer_distribution = Counter(str(question.get("answer") or "") for question in questions)
    difficulty_distribution = Counter(str(question.get("difficulty") or "") for question in questions)
    knowledge_distribution = Counter(str(question.get("knowledge_point") or "").strip() for question in questions if str(question.get("knowledge_point") or "").strip())
    question_texts = Counter(str(question.get("question") or "").strip() for question in questions)
    suspicious_terms = ["军事", "军事化", "军队", "作战", "军事基地", "军事训练", "军事政策", "军事服务", "军事生产", "军事安全", "军事技术"]

    total = len(questions)
    if total:
        answer, count = answer_distribution.most_common(1)[0]
        ratio = count / total
        if ratio >= 0.45:
            add_audit_issue(issues, "high", "answer_skew", f"答案 {answer} 占比 {round(ratio * 100, 2)}%，分布明显偏斜。", detail=dict(answer_distribution))
        hard_ratio = difficulty_distribution.get("hard", 0) / total
        easy_ratio = difficulty_distribution.get("easy", 0) / total
        if hard_ratio < 0.05:
            add_audit_issue(issues, "medium", "difficulty_imbalance", f"hard 难度占比仅 {round(hard_ratio * 100, 2)}%，高难题偏少。", detail=dict(difficulty_distribution))
        if easy_ratio > 0.45:
            add_audit_issue(issues, "medium", "difficulty_imbalance", f"easy 难度占比 {round(easy_ratio * 100, 2)}%，题库可能偏基础。", detail=dict(difficulty_distribution))

    for question in questions:
        missing = [field for field in required if field not in question or question.get(field) in (None, "", [])]
        if missing:
            add_audit_issue(issues, "high", "missing_field", "题目缺少必要字段。", question, missing)
        answer = str(question.get("answer") or "").strip()
        if answer not in {"A", "B", "C", "D"}:
            add_audit_issue(issues, "high", "invalid_answer", "答案不在 A/B/C/D 范围。", question, answer)
        options = question.get("options") or []
        option_bodies = [option_body(option) for option in options]
        if len(options) != 4:
            add_audit_issue(issues, "high", "option_count", "选择题选项数量不是4个。", question, len(options))
        duplicates = [body for body, count in Counter(option_bodies).items() if body and count > 1]
        if duplicates:
            add_audit_issue(issues, "medium", "duplicate_options", "存在重复或近似重复选项。", question, duplicates)
        explanation = str(question.get("explanation") or "").strip()
        if len(explanation) < min_explanation_length:
            add_audit_issue(issues, "medium", "short_explanation", "解析过短，难以支撑学习闭环。", question, f"{len(explanation)} chars")
        point = str(question.get("knowledge_point") or "").strip()
        if is_weak_knowledge_point(point):
            add_audit_issue(issues, "medium", "weak_knowledge_point", "knowledge_point 过短、过泛或像截断短语。", question, point)
        source_ref = str(question.get("source_ref") or "").strip()
        if source_ref and not source_ref.startswith("references/"):
            add_audit_issue(issues, "low", "weak_source_ref", "source_ref 不是 references/ 路径。", question, source_ref)
        text_bundle = " ".join([str(question.get("question") or ""), explanation, " ".join(str(option) for option in options)])
        matched_terms = sorted({term for term in suspicious_terms if term in text_bundle})
        if matched_terms:
            add_audit_issue(issues, "medium", "artificial_distractor", "出现明显模板化或与考试场景弱相关的干扰项词汇。", question, matched_terms)

    for text, count in question_texts.items():
        if text and count > 1:
            add_audit_issue(issues, "medium", "duplicate_question_text", f"存在完全相同题干，重复 {count} 次。", detail=text[:80])

    if total:
        for point, count in knowledge_distribution.most_common(10):
            if count / total >= 0.08:
                add_audit_issue(issues, "low", "overused_knowledge_point", f"知识点“{point}”出现 {count} 次，可能过泛。", detail={"knowledge_point": point, "count": count})

    severity_order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda item: (severity_order.get(item["severity"], 9), item["code"], item.get("question_id", "")))
    counts_by_code = Counter(issue["code"] for issue in issues)
    counts_by_severity = Counter(issue["severity"] for issue in issues)
    return {
        "total_questions": total,
        "answer_distribution": dict(answer_distribution),
        "difficulty_distribution": dict(difficulty_distribution),
        "issue_count": len(issues),
        "counts_by_severity": dict(counts_by_severity),
        "counts_by_code": dict(counts_by_code),
        "issues": issues[: limit],
        "truncated": len(issues) > limit,
    }


def build_audit_payload(args: argparse.Namespace) -> dict[str, Any]:
    questions, _, _ = load_all_questions()
    return audit_questions_payload(questions, args.limit, args.min_explanation_length)


def render_audit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 题库质量审计",
        "",
        f"- 题目总数：{payload['total_questions']}",
        f"- 问题数量：{payload['issue_count']}",
        f"- 答案分布：{payload['answer_distribution']}",
        f"- 难度分布：{payload['difficulty_distribution']}",
        "",
        "## 问题汇总",
    ]
    if payload["counts_by_code"]:
        for code, count in sorted(payload["counts_by_code"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {code}: {count}")
    else:
        lines.append("- 暂未发现问题。")
    lines.append("")
    lines.append("## 示例")
    if payload["issues"]:
        for issue in payload["issues"]:
            location = f" {issue.get('question_id')}" if issue.get("question_id") else ""
            detail = f" detail={issue['detail']}" if "detail" in issue else ""
            lines.append(f"- [{issue['severity']}] {issue['code']}{location}: {issue['message']}{detail}")
        if payload.get("truncated"):
            lines.append("- 输出已截断；可增加 --limit 查看更多示例。")
    else:
        lines.append("- 暂无示例。")
    return "\n".join(lines) + "\n"


def command_audit(args: argparse.Namespace) -> int:
    payload = build_audit_payload(args)
    if args.format == "markdown":
        print(render_audit_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def chapter_path_from_question(question: dict[str, Any]) -> Path | None:
    chapter_no = chapter_no_from_label(str(question.get("chapter") or ""))
    if chapter_no is None:
        return None
    return CHAPTERS_DIR / f"chapter_{chapter_no:02d}.json"


def inferred_knowledge_point(question: dict[str, Any]) -> str:
    qid = str(question.get("id") or "")
    if qid in STRONG_KNOWLEDGE_POINT_OVERRIDES:
        return STRONG_KNOWLEDGE_POINT_OVERRIDES[qid]
    section = str(question.get("section") or "").strip()
    tags = [str(tag).strip() for tag in question.get("tags", []) if str(tag).strip()]
    for tag in tags:
        if not is_weak_knowledge_point(tag) and tag != section:
            return tag
    if section and not is_weak_knowledge_point(section):
        return section
    chapter_no = chapter_no_from_label(str(question.get("chapter") or ""))
    if chapter_no:
        for data in PAPER_TOPICS.values():
            if data["chapter"] == chapter_no:
                return data["chapter_title"]
    return section or str(question.get("chapter") or "通用知识点")


def replace_suspicious_terms(text: str) -> str:
    fixed = str(text)
    for bad, replacement in SUSPICIOUS_DISTRACTOR_REPLACEMENTS.items():
        fixed = fixed.replace(bad, replacement)
    return fixed


def apply_quality_fix(question: dict[str, Any], min_explanation_length: int, fix_options: bool = False) -> list[dict[str, Any]]:
    changes = []
    if fix_options:
        for field in ("question", "explanation"):
            original = str(question.get(field) or "")
            fixed = replace_suspicious_terms(original)
            if fixed != original:
                question[field] = fixed
                changes.append({"field": field, "reason": "replace_template_distractor"})
        original_options = list(question.get("options") or [])
        fixed_options = [replace_suspicious_terms(str(option)) for option in original_options]
        if fixed_options != original_options:
            question["options"] = fixed_options
            changes.append({"field": "options", "reason": "replace_template_distractor"})

    point = str(question.get("knowledge_point") or "").strip()
    if is_weak_knowledge_point(point) or point in STOP_KNOWLEDGE_POINTS:
        new_point = inferred_knowledge_point(question)
        if new_point and new_point != point:
            question["knowledge_point"] = new_point
            tags = list(question.get("tags") or [])
            if new_point not in tags:
                tags.insert(0, new_point)
                question["tags"] = tags[:5]
            changes.append({"field": "knowledge_point", "reason": "replace_weak_metadata", "from": point, "to": new_point})

    explanation = str(question.get("explanation") or "").strip()
    if len(explanation) < min_explanation_length:
        answer = str(question.get("answer") or "").strip()
        section = str(question.get("section") or question.get("knowledge_point") or "").strip()
        supplement = f"本题考查{section}。正确答案为{answer}，可结合教材对应小节理解概念边界和适用场景。"
        if explanation:
            question["explanation"] = f"{explanation} {supplement}"
        else:
            question["explanation"] = supplement
        changes.append({"field": "explanation", "reason": "expand_short_explanation"})

    return changes


def option_letter(index: int) -> str:
    return "ABCD"[index]


def option_text_without_letter(option: Any) -> str:
    return re.sub(r"^[A-Da-d][\.\、:：\)]\s*", "", str(option or "")).strip()


def format_option(letter: str, body: str) -> str:
    return f"{letter}. {body}"


def rebalance_answer_distribution(questions: list[dict[str, Any]], target_max_ratio: float = 0.44) -> list[dict[str, Any]]:
    changes = []
    total = len(questions)
    if not total:
        return changes
    distribution = Counter(str(question.get("answer") or "") for question in questions)
    target_max = int(total * target_max_ratio)
    target_letters = ("A", "B", "C", "D")
    for source_letter, source_count in distribution.most_common():
        while source_count > target_max:
            target_letter = min(target_letters, key=lambda letter: distribution.get(letter, 0))
            if distribution[target_letter] >= target_max or target_letter == source_letter:
                break
            question = next(
                (
                    item for item in questions
                    if str(item.get("answer") or "") == source_letter
                    and len(item.get("options") or []) == 4
                    and item.get("question_type", "single_choice") in {"single_choice", "choice"}
                ),
                None,
            )
            if not question:
                break
            options = list(question.get("options") or [])
            source_index = target_letters.index(source_letter)
            target_index = target_letters.index(target_letter)
            bodies = [option_text_without_letter(option) for option in options]
            bodies[source_index], bodies[target_index] = bodies[target_index], bodies[source_index]
            question["options"] = [format_option(letter, body) for letter, body in zip(target_letters, bodies)]
            question["answer"] = target_letter
            changes.append({"question_id": question.get("id"), "field": "answer/options", "reason": "rebalance_answer_distribution", "from": source_letter, "to": target_letter})
            distribution[source_letter] -= 1
            distribution[target_letter] += 1
            source_count = distribution[source_letter]
    return changes


def hard_question_score(question: dict[str, Any]) -> int:
    text = f"{question.get('question', '')} {question.get('explanation', '')}"
    score = 0
    score += 2 if any(term in text for term in ("不正确", "不包括", "不属于", "最恰当", "主要原因", "核心要求")) else 0
    score += 2 if any(term in text for term in ("案例", "场景", "分析", "规划", "治理", "架构", "成熟度", "连续性")) else 0
    score += 1 if len(normalize_text(text)) >= 120 else 0
    return score


def rebalance_difficulty(questions: list[dict[str, Any]], min_hard_ratio: float = 0.06) -> list[dict[str, Any]]:
    total = len(questions)
    target_hard = max(1, int(total * min_hard_ratio))
    current_hard = sum(1 for question in questions if question.get("difficulty") == "hard")
    needed = max(0, target_hard - current_hard)
    if needed == 0:
        return []
    candidates = [
        question for question in questions
        if question.get("difficulty") == "medium" and hard_question_score(question) >= 3
    ]
    candidates.sort(key=lambda question: (-hard_question_score(question), str(question.get("id") or "")))
    changes = []
    for question in candidates[:needed]:
        question["difficulty"] = "hard"
        tags = list(question.get("tags") or [])
        if "hard" not in tags:
            tags.append("hard")
            question["tags"] = tags[:5]
        changes.append({"question_id": question.get("id"), "field": "difficulty", "reason": "promote_high_cognitive_load", "to": "hard"})
    return changes


def build_quality_fix_payload(args: argparse.Namespace) -> dict[str, Any]:
    files = sorted(CHAPTERS_DIR.glob("chapter_*.json"))
    changed_files: dict[str, list[dict[str, Any]]] = {}
    loaded_files: dict[Path, list[dict[str, Any]]] = {}
    all_questions_after_fix: list[dict[str, Any]] = []
    total_changes = 0
    touched_questions = 0
    for path in files:
        data = load_json(path)
        if not isinstance(data, list):
            continue
        loaded_files[path] = data
        file_changes = []
        for question in data:
            if not isinstance(question, dict):
                continue
            changes = apply_quality_fix(question, args.min_explanation_length, fix_options=args.fix_options)
            all_questions_after_fix.append(question)
            if changes:
                touched_questions += 1
                total_changes += len(changes)
                file_changes.append({"question_id": question.get("id"), "changes": changes})
        if file_changes:
            rel = str(path.relative_to(ROOT))
            changed_files[rel] = file_changes
            if args.write:
                save_json(path, data)
    all_questions_after_fix = [question for data in loaded_files.values() for question in data if isinstance(question, dict)]
    if args.rebalance_answers:
        answer_changes = rebalance_answer_distribution(all_questions_after_fix, target_max_ratio=args.answer_max_ratio)
        if answer_changes:
            by_id = {str(question.get("id")): question for question in all_questions_after_fix}
            for change in answer_changes:
                question = by_id.get(str(change.get("question_id")))
                if not question:
                    continue
                path = chapter_path_from_question(question)
                if not path:
                    continue
                rel = str(path.relative_to(ROOT))
                changed_files.setdefault(rel, []).append({"question_id": question.get("id"), "changes": [change]})
            touched_questions += len(answer_changes)
            total_changes += len(answer_changes)
    if args.rebalance_difficulty:
        difficulty_changes = rebalance_difficulty(all_questions_after_fix, min_hard_ratio=args.min_hard_ratio)
        if difficulty_changes:
            by_id = {str(question.get("id")): question for question in all_questions_after_fix}
            for change in difficulty_changes:
                question = by_id.get(str(change.get("question_id")))
                if not question:
                    continue
                path = chapter_path_from_question(question)
                if not path:
                    continue
                rel = str(path.relative_to(ROOT))
                changed_files.setdefault(rel, []).append({"question_id": question.get("id"), "changes": [change]})
            touched_questions += len(difficulty_changes)
            total_changes += len(difficulty_changes)
    if args.write:
        for path, data in loaded_files.items():
            save_json(path, data)
    remaining = audit_questions_payload(all_questions_after_fix, args.audit_limit, args.min_explanation_length)
    payload = {
        "mode": "write" if args.write else "dry_run",
        "changed_files": changed_files,
        "changed_file_count": len(changed_files),
        "touched_questions": touched_questions,
        "total_changes": total_changes,
        "remaining_issue_count": remaining["issue_count"],
        "remaining_counts_by_code": remaining["counts_by_code"],
        "remaining_issues": remaining["issues"],
        "note": "默认自动修复弱 knowledge_point 和过短解析；--fix-options 替换题干/选项/解析中的明显模板化干扰词；--rebalance-answers 只重排选项不改变知识含义；--rebalance-difficulty 按题干复杂度提升部分 hard。",
    }
    return payload


def render_quality_fix_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 题库质量修复",
        "",
        f"- 模式：{payload['mode']}",
        f"- 涉及文件：{payload['changed_file_count']}",
        f"- 涉及题目：{payload['touched_questions']}",
        f"- 修复项：{payload['total_changes']}",
        f"- 剩余问题：{payload['remaining_issue_count']}",
        f"- 说明：{payload['note']}",
        "",
        "## 剩余问题分布",
    ]
    if payload["remaining_counts_by_code"]:
        for code, count in sorted(payload["remaining_counts_by_code"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {code}: {count}")
    else:
        lines.append("- 暂无剩余问题。")
    if payload.get("remaining_issues"):
        lines.append("")
        lines.append("## 剩余问题示例")
        for issue in payload["remaining_issues"][:10]:
            location = f" {issue.get('question_id')}" if issue.get("question_id") else ""
            detail = f" detail={issue['detail']}" if "detail" in issue else ""
            lines.append(f"- [{issue['severity']}] {issue['code']}{location}: {issue['message']}{detail}")
    lines.append("")
    lines.append("## 修复示例")
    examples = []
    for rel, items in payload["changed_files"].items():
        for item in items:
            examples.append((rel, item))
            if len(examples) >= 10:
                break
        if len(examples) >= 10:
            break
    if examples:
        for rel, item in examples:
            reasons = ", ".join(change["reason"] for change in item["changes"])
            lines.append(f"- {rel} {item['question_id']}: {reasons}")
    else:
        lines.append("- 没有可自动修复项。")
    if payload["mode"] == "dry_run":
        lines.append("")
        lines.append("Next: 确认后执行 python scripts/study.py fix-quality --write")
    return "\n".join(lines) + "\n"


def command_fix_quality(args: argparse.Namespace) -> int:
    payload = build_quality_fix_payload(args)
    if args.format == "markdown":
        print(render_quality_fix_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
