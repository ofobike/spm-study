from __future__ import annotations

import argparse
import json
import re
from typing import Any

from study_modules.common import compact_text, resolve_session, session_file_value, session_next_step, should_write_session
from study_modules.settings import GENERIC_CASE_TERMS
from study_utils import (
    ROOT,
    choose_questions,
    load_json,
    load_progress,
    make_session,
    now_iso,
    parse_answer_text,
    parse_chapters,
    save_json,
    write_session,
)


def load_case_studies() -> list[dict[str, Any]]:
    data = load_json(ROOT / "assets" / "questions" / "case_studies.json")
    return data.get("case_studies", [])


def filter_cases_by_source(cases: list[dict[str, Any]], source: str | None) -> list[dict[str, Any]]:
    if not source or source == "all":
        return cases
    if source == "recitation":
        return [case for case in cases if str(case.get("source") or "") == "2025新版系规案例背诵-正式入库"]
    if source == "scenario":
        return [case for case in cases if str(case.get("source") or "") != "2025新版系规案例背诵-正式入库"]
    return cases


def public_case(case: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    questions = []
    for question in case.get("questions", []):
        item = {
            "id": question.get("id"),
            "question": question.get("question"),
            "question_type": question.get("question_type", "choice" if question.get("options") else "subjective"),
            "score": question.get("score"),
        }
        if question.get("options"):
            item["options"] = question.get("options")
        if include_answer:
            item["answer"] = question.get("answer")
            item["explanation"] = question.get("explanation")
        questions.append(item)
    return {
        "id": case.get("id"),
        "chapter": case.get("chapter"),
        "chapters": case.get("chapters", [case.get("chapter")]),
        "title": case.get("title"),
        "difficulty": case.get("difficulty"),
        "total_score": case.get("total_score"),
        "scenario": case.get("scenario"),
        "questions": questions,
    }


def render_case_markdown(case: dict[str, Any], include_answer: bool = False) -> str:
    lines = [f"# {case.get('title')} [{case.get('id')}]", "", str(case.get("scenario", "")), ""]
    for index, question in enumerate(case.get("questions", []), start=1):
        lines.append(f"{index}. [{question.get('id')}] {question.get('question')}")
        for option in question.get("options", []):
            lines.append(f"   {option}")
        if include_answer:
            lines.append(f"   Answer: {question.get('answer')}")
            if question.get("explanation"):
                lines.append(f"   Explanation: {question.get('explanation')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_case_answer_text(answer_text: str, question_ids: list[str]) -> dict[str, str]:
    text = answer_text.strip()
    if not text:
        return {}
    if text.startswith("{"):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("JSON answers must be an object mapping question id to answer")
        return {str(key): str(value).strip() for key, value in data.items()}
    if "=" in text or ":" in text or "：" in text:
        keyed = list(re.finditer(r"(?<!\w)([A-Za-z][A-Za-z0-9_]*_q\d+)\s*[=：:]", text))
        if keyed:
            answers = {}
            for idx, match in enumerate(keyed):
                start = match.end()
                end = keyed[idx + 1].start() if idx + 1 < len(keyed) else len(text)
                answers[match.group(1).strip()] = text[start:end].strip(" \t\r\n,，;；")
            return answers
        answers: dict[str, str] = {}
        for part in re.split(r"[,;\n]+", text):
            item = part.strip()
            if not item:
                continue
            if "=" in item:
                key, value = item.split("=", 1)
            elif "：" in item:
                key, value = item.split("：", 1)
            else:
                key, value = item.split(":", 1)
            answers[key.strip()] = value.strip()
        return answers
    return parse_answer_text(text, question_ids)


def normalize_text(text: str) -> str:
    return compact_text(text)


def case_keywords(reference: str, limit: int = 16) -> list[str]:
    chunks = re.split(r"[；;。.!！?？\n]|(?:\(\d+\))|(?:（\d+）)", reference or "")
    phrases = []
    for chunk in chunks:
        cleaned = re.sub(r"^[\s:：,，、\-—]+|[\s:：,，、\-—]+$", "", chunk)
        if 4 <= len(cleaned) <= 28 and not any(term in cleaned for term in ("可能原因分析", "提升策略", "计算方法")):
            phrases.append(cleaned)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+/.-]{1,}|[\u4e00-\u9fff]{2,}", reference or "")
    keywords = []
    for phrase in phrases:
        if phrase not in keywords:
            keywords.append(phrase)
    for token in tokens:
        item = token.strip("：:，,。；;（）()、-—")
        if len(item) < 2 or item in GENERIC_CASE_TERMS:
            continue
        if item not in keywords:
            keywords.append(item)
    return keywords[:limit]


def char_ngrams(text: str, size: int = 2) -> set[str]:
    normalized = normalize_text(text)
    if len(normalized) < size:
        return {normalized} if normalized else set()
    return {normalized[index:index + size] for index in range(len(normalized) - size + 1)}


def point_matched(point: str, normalized_answer: str) -> bool:
    normalized_point = normalize_text(point)
    if not normalized_point:
        return False
    if normalized_point in normalized_answer:
        return True
    point_grams = char_ngrams(normalized_point)
    answer_grams = char_ngrams(normalized_answer)
    if point_grams and len(point_grams & answer_grams) / len(point_grams) >= 0.45:
        return True
    if len(normalized_point) >= 6:
        parts = re.findall(r"[A-Za-z][A-Za-z0-9+/.-]{1,}|[\u4e00-\u9fff]{2,}", point)
        meaningful = [part for part in parts if part not in GENERIC_CASE_TERMS and len(part) >= 2]
        if meaningful:
            hits = sum(1 for part in meaningful if normalize_text(part) in normalized_answer)
            return hits / len(meaningful) >= 0.5
    return False


def grade_subjective_answer(user_answer: str, reference_answer: str, max_score: int) -> dict[str, Any]:
    keywords = case_keywords(reference_answer)
    normalized = normalize_text(user_answer)
    matched = [keyword for keyword in keywords if point_matched(keyword, normalized)]
    missing = [keyword for keyword in keywords if not point_matched(keyword, normalized)]
    coverage = len(matched) / len(keywords) if keywords else 0
    answer_terms = [
        term for term in re.findall(r"[A-Za-z][A-Za-z0-9+/.-]{1,}|[\u4e00-\u9fff]{2,}", user_answer or "")
        if term not in GENERIC_CASE_TERMS
    ]
    reference_terms = [
        term for term in re.findall(r"[A-Za-z][A-Za-z0-9+/.-]{1,}|[\u4e00-\u9fff]{2,}", reference_answer or "")
        if term not in GENERIC_CASE_TERMS
    ]
    reference_terms = list(dict.fromkeys(reference_terms))
    term_matched = [term for term in reference_terms if point_matched(term, normalized)]
    term_missing = [term for term in reference_terms if not point_matched(term, normalized)]
    term_hits = len(term_matched)
    term_coverage = term_hits / len(reference_terms) if reference_terms else 0
    length_ratio = min(1.0, len(normalized) / max(80, min(240, len(normalize_text(reference_answer)))))
    scenario_terms = ["案例", "场景", "问题", "原因", "策略", "措施", "目标", "指标", "风险", "用户", "业务", "平台", "数据", "流程", "组织"]
    scenario_hits = sum(1 for term in scenario_terms if term in user_answer)
    scenario_ratio = min(1.0, scenario_hits / 4)
    problem_terms = ["原因", "问题", "痛点", "不足", "现状", "影响", "瓶颈", "需求", "风险"]
    action_terms = ["优化", "建立", "完善", "制定", "提升", "改进", "监控", "培训", "治理", "协同", "保障", "评估", "闭环", "机制", "流程"]
    metric_terms = ["指标", "KPI", "SLA", "满意度", "正确率", "及时率", "覆盖率", "成本", "效率", "周期", "质量", "%", "％"]
    problem_hits = [term for term in problem_terms if term in user_answer]
    action_hits = [term for term in action_terms if term in user_answer]
    metric_hits = [term for term in metric_terms if term in user_answer]
    if re.search(r"\d+|一|二|三|四|五|六|七|八|九|十", user_answer or ""):
        metric_hits.append("量化表达")
    problem_ratio = min(1.0, len(problem_hits) / 2)
    action_ratio = min(1.0, len(action_hits) / 3)
    metric_ratio = min(1.0, len(metric_hits) / 2)
    structure_markers = re.findall(r"(?:^|[；;。.\n])\s*(?:[一二三四五六七八九十]、|[0-9]+[.、]|首先|其次|再次|最后|第一|第二|第三)", user_answer)
    structure_ratio = min(1.0, len(structure_markers) / 3)
    rubric = [
        ("key_points", "采分点覆盖", 0.36, coverage, matched[:8], missing[:8]),
        ("terms", "关键术语", 0.14, term_coverage, term_matched[:8], term_missing[:8]),
        ("scenario", "场景化表达", 0.1, scenario_ratio, [term for term in scenario_terms if term in user_answer][:8], []),
        ("problem", "问题定位", 0.1, problem_ratio, problem_hits[:8], []),
        ("action", "措施可执行性", 0.12, action_ratio, action_hits[:8], []),
        ("metrics", "量化指标", 0.08, metric_ratio, metric_hits[:8], []),
        ("structure", "结构完整性", 0.06, structure_ratio, structure_markers[:5], []),
        ("length", "答题充分度", 0.04, length_ratio, [], []),
    ]
    score = round(max_score * sum(weight * ratio for _, _, weight, ratio, _, _ in rubric)) if max_score else 0
    if not normalized:
        score = 0
    rubric_rows = [
        {
            "key": key,
            "label": label,
            "weight": weight,
            "ratio": round(ratio, 4),
            "score": round(max_score * weight * ratio, 2) if max_score else 0,
            "max_score": round(max_score * weight, 2) if max_score else 0,
            "matched": hits,
            "missing": misses,
        }
        for key, label, weight, ratio, hits, misses in rubric
    ]
    feedback_parts = []
    if coverage < 0.65:
        feedback_parts.append("优先补齐参考答案中的核心采分点")
    if problem_ratio < 0.5:
        feedback_parts.append("先写清原因、问题或风险定位")
    if action_ratio < 0.67:
        feedback_parts.append("措施要写成可执行动作和闭环机制")
    if metric_ratio < 0.5:
        feedback_parts.append("补充可量化指标或验收标准")
    if scenario_ratio < 0.5:
        feedback_parts.append("结合题干场景写原因、措施和指标")
    if structure_ratio < 0.5:
        feedback_parts.append("用分点结构作答，避免整段堆叙")
    if length_ratio < 0.7:
        feedback_parts.append("答案篇幅偏短，需要展开关键措施")
    return {
        "is_correct": None,
        "auto_score": min(max_score, score),
        "max_score": max_score,
        "keyword_coverage": round(coverage, 4),
        "term_coverage": round(term_coverage, 4),
        "scenario_coverage": round(scenario_ratio, 4),
        "structure_coverage": round(structure_ratio, 4),
        "length_coverage": round(length_ratio, 4),
        "rubric": rubric_rows,
        "matched_points": matched[:10],
        "missing_points": missing[:10],
        "feedback": "；".join(feedback_parts) if feedback_parts else "要点覆盖较好，继续补充场景化表达和量化指标。",
    }


def build_case_start_payload(args: argparse.Namespace, write: bool | None = None) -> dict[str, Any]:
    cases = load_case_studies()
    cases = filter_cases_by_source(cases, getattr(args, "source", None))
    if getattr(args, "chapters", None):
        chapters = set(parse_chapters(args.chapters))
        cases = [case for case in cases if chapters.intersection(set(case.get("chapters") or [case.get("chapter")]))]
    if getattr(args, "difficulty", None):
        filtered = [case for case in cases if case.get("difficulty") == args.difficulty]
        if filtered:
            cases = filtered
    selected = choose_questions(cases, int(args.count), seed=getattr(args, "seed", None))
    session = make_session(
        "case_study",
        [case["id"] for case in selected],
        {
            "chapters": getattr(args, "chapters", None),
            "count": int(args.count),
            "difficulty": getattr(args, "difficulty", None),
            "seed": getattr(args, "seed", None),
            "source": getattr(args, "source", None),
        },
    )
    session["case_ids"] = session.pop("question_ids")
    session["answers_template"] = {question["id"]: "" for case in selected for question in case.get("questions", [])}
    write = should_write_session(args) if write is None else write
    next_step = f"Submit answers with: python scripts/study.py case submit --session {session['id']} --answers \"cs_x_q1=A,...\""
    return {
        "session": session,
        "session_file": session_file_value(session, write),
        "cases": [public_case(case) for case in selected],
        "next_step": session_next_step(next_step, write),
    }


def render_case_start_markdown(payload: dict[str, Any]) -> str:
    lines = [f"Session: {payload['session']['id']}", f"File: {payload['session_file']}", ""]
    for case in payload.get("cases", []):
        lines.append(render_case_markdown(case).rstrip())
        lines.append("")
    lines.append(payload["next_step"])
    return "\n".join(lines).rstrip() + "\n"


def command_case_start(args: argparse.Namespace) -> int:
    payload = build_case_start_payload(args)
    if args.format == "markdown":
        print(render_case_start_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_case_submit_payload(args: argparse.Namespace) -> dict[str, Any]:
    session_path = resolve_session(args.session)
    session = load_json(session_path)
    answers = parse_case_answer_text(args.answers, list(session.get("answers_template", {}).keys()))
    if session.get("type") == "past_exam_case":
        from study_modules.past_exam import load_past_exam_cases

        cases_by_id = {case["id"]: case for case in load_past_exam_cases()}
    else:
        cases_by_id = {case["id"]: case for case in load_case_studies()}
    results = []
    auto_score = 0
    max_score = 0
    subjective = []

    for case_id in session.get("case_ids", []):
        case = cases_by_id.get(case_id)
        if not case:
            continue
        case_result = {"case_id": case_id, "title": case.get("title"), "questions": []}
        for question in case.get("questions", []):
            qid = question.get("id")
            answer = answers.get(qid, "")
            expected = str(question.get("answer", ""))
            has_options = bool(question.get("options"))
            score = int(question.get("score", 0) or 0)
            max_score += score
            item = {
                "question_id": qid,
                "user_answer": answer,
                "reference_answer": expected,
                "score": score,
                "explanation": question.get("explanation"),
            }
            if has_options and expected in {"A", "B", "C", "D"}:
                item["is_correct"] = answer == expected
                if item["is_correct"]:
                    auto_score += score
            else:
                grading = grade_subjective_answer(answer, expected, score)
                item.update(grading)
                auto_score += int(item["auto_score"])
                subjective.append(item)
            case_result["questions"].append(item)
        results.append(case_result)

    payload = {
        "session_id": session.get("id"),
        "auto_score": auto_score,
        "max_score": max_score,
        "score_percent": round((auto_score / max_score) * 100, 2) if max_score else 0,
        "subjective_count": len(subjective),
        "results": results,
        "recommendation": "选择题已自动批改；主观题已按参考答案关键词、篇幅和要点覆盖自动估分，建议按 missing_points 二次补答。",
    }
    record = not getattr(args, "no_record", False)
    attempts = list(session.get("case_attempts", []))
    previous = attempts[-1] if attempts else None
    submitted_at = now_iso()
    attempt = {
        "attempt_no": len(attempts) + 1,
        "submitted_at": submitted_at,
        "auto_score": auto_score,
        "max_score": max_score,
        "score_percent": payload["score_percent"],
        "answers": answers,
    }
    if previous:
        attempt["delta_score"] = auto_score - int(previous.get("auto_score", 0))
        attempt["delta_percent"] = round(payload["score_percent"] - float(previous.get("score_percent", 0)), 2)
        payload["improvement"] = {
            "previous_score": previous.get("auto_score"),
            "current_score": auto_score,
            "delta_score": attempt["delta_score"],
            "delta_percent": attempt["delta_percent"],
        }
    if record:
        session.setdefault("case_attempts", []).append(attempt)
        write_session(session)

        progress = load_progress()
        progress.setdefault("case_attempts", []).append(
            {
                "session_id": session.get("id"),
                "submitted_at": submitted_at,
                "attempt_no": attempt["attempt_no"],
                "auto_score": auto_score,
                "max_score": max_score,
                "score_percent": payload["score_percent"],
            }
        )
        progress["last_updated"] = submitted_at
        save_json(ROOT / "assets" / "questions" / "progress.json", progress)
    payload["recorded"] = record
    payload["attempt_no"] = attempt["attempt_no"]
    payload["session_file"] = str(session_path.relative_to(ROOT))
    return payload


def render_case_submit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"Auto score: {payload['auto_score']}/{payload['max_score']}",
        f"Recorded: {payload.get('recorded', True)}",
        f"Attempt: {payload['attempt_no']}",
    ]
    if payload.get("improvement"):
        improvement = payload["improvement"]
        lines.append(f"Improvement: {improvement['delta_score']} 分，{improvement['delta_percent']} 个百分点")
    for case in payload["results"]:
        lines.append(f"\n## {case['title']} [{case['case_id']}]")
        for item in case["questions"]:
            mark = "SUBJECTIVE" if item["is_correct"] is None else ("OK" if item["is_correct"] else "WRONG")
            score_text = f" score={item.get('auto_score', item.get('score', 0) if item.get('is_correct') else 0)}/{item.get('max_score', item.get('score'))}" if item["is_correct"] is None else ""
            lines.append(f"- {mark} {item['question_id']}{score_text}: your {item['user_answer'] or '-'}, reference {item['reference_answer']}")
            if item["is_correct"] is None:
                if item.get("matched_points"):
                    lines.append(f"  Matched: {'、'.join(item['matched_points'])}")
                if item.get("missing_points"):
                    lines.append(f"  Missing: {'、'.join(item['missing_points'])}")
                if item.get("rubric"):
                    lines.append("  Rubric:")
                    for row in item["rubric"]:
                        lines.append(f"    - {row['label']}: {row['score']}/{row['max_score']} ({round(row['ratio'] * 100, 1)}%)")
                lines.append(f"  Feedback: {item.get('feedback')}")
            if item.get("explanation"):
                lines.append(f"  {item['explanation']}")
    lines.append("")
    lines.append(f"Next: {payload['recommendation']}")
    return "\n".join(lines) + "\n"


def command_case_submit(args: argparse.Namespace) -> int:
    payload = build_case_submit_payload(args)
    if args.format == "markdown":
        print(render_case_submit_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
