from __future__ import annotations

import argparse
import json
from typing import Any

from study_utils import (
    ROOT,
    SESSIONS_DIR,
    append_progress,
    choose_questions,
    load_all_questions,
    load_archive,
    load_config,
    load_json,
    load_progress,
    make_session,
    mark_reviewed,
    parse_answer_text,
    parse_chapters,
    parse_date,
    public_question,
    record_wrong_answer,
    render_questions_markdown,
    today,
)

from study_modules.case import load_case_studies, public_case, render_case_markdown
from study_modules.common import (
    display_command,
    due_review_items,
    resolve_session,
    session_file_value,
    session_next_step,
    should_write_session,
    simplify_json,
)
from study_modules.materials import case_range_chapters_text
from study_modules.mastery import build_mastery_payload
from study_modules.past_exam import (
    load_past_exam_cases,
    past_exam_choice_lookup,
    public_past_exam_question,
)
from study_modules.search_training import (
    public_sprint_training_question,
    sprint_training_question_lookup,
)
from study_modules.standards import public_standard_question, standards_question_lookup


def session_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not SESSIONS_DIR.exists():
        return records
    for path in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            session = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(session, dict):
            continue
        records.append({"path": path, "session": session, "created_at": session.get("created_at") or ""})
    records.sort(key=lambda item: (str(item["created_at"]), str(item["path"])), reverse=True)
    return records


def completed_session_ids() -> set[str]:
    progress = load_progress()
    return {str(session.get("id")) for session in progress.get("sessions", []) if session.get("id")}


def is_session_completed(session: dict[str, Any], completed_ids: set[str] | None = None) -> bool:
    completed_ids = completed_ids if completed_ids is not None else completed_session_ids()
    session_id = str(session.get("id") or "")
    if session.get("type") in {"case_study", "past_exam_case"}:
        return bool(session.get("case_attempts"))
    return session_id in completed_ids


def latest_session(kind: str | None = None, open_only: bool = False) -> dict[str, Any] | None:
    completed_ids = completed_session_ids()
    for record in session_records():
        session = record["session"]
        if kind and session.get("type") != kind:
            continue
        if open_only and is_session_completed(session, completed_ids):
            continue
        return record
    return None


def filter_questions(questions: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    result = list(questions)
    if getattr(args, "knowledge_point", None):
        result = [question for question in result if args.knowledge_point in str(question.get("knowledge_point", ""))]
    if getattr(args, "section", None):
        result = [question for question in result if args.section in str(question.get("section", ""))]
    if getattr(args, "tag", None):
        result = [question for question in result if any(args.tag in str(tag) for tag in question.get("tags", []))]
    return result


def difficulty_plan(total: int, distribution: dict[str, float]) -> dict[str, int]:
    raw = {difficulty: total * ratio for difficulty, ratio in distribution.items()}
    counts = {difficulty: int(value) for difficulty, value in raw.items()}
    remaining = total - sum(counts.values())
    for difficulty, _ in sorted(raw.items(), key=lambda item: item[1] - int(item[1]), reverse=True):
        if remaining <= 0:
            break
        counts[difficulty] += 1
        remaining -= 1
    return counts


def choose_with_difficulty(pool: list[dict[str, Any]], count: int, distribution: dict[str, float], seed: int | None) -> list[dict[str, Any]]:
    if not distribution or not all("difficulty" in question for question in pool):
        return choose_questions(pool, count, seed=seed)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for offset, (difficulty, target) in enumerate(difficulty_plan(count, distribution).items()):
        picked = choose_questions(pool, target, seed=None if seed is None else seed + offset, exclude_ids=selected_ids, difficulty=difficulty)
        selected.extend(picked)
        selected_ids.update(question["id"] for question in picked)
    if len(selected) < count:
        selected.extend(choose_questions(pool, count - len(selected), seed=seed, exclude_ids=selected_ids))
    return selected[:count]


def build_practice(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _, _, by_chapter = load_all_questions()
    chapters = parse_chapters(args.chapters)
    candidates = [question for chapter in chapters for question in by_chapter.get(chapter, [])]
    candidates = filter_questions(candidates, args)
    selected = choose_questions(candidates, args.count, seed=args.seed, difficulty=args.difficulty)
    session = make_session(
        "practice",
        [question["id"] for question in selected],
        {
            "chapters": chapters,
            "count": args.count,
            "difficulty": args.difficulty,
            "knowledge_point": args.knowledge_point,
            "section": args.section,
            "tag": args.tag,
            "seed": args.seed,
        },
    )
    return session, selected


def build_mock(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = load_config()
    _, _, by_chapter = load_all_questions()
    exam_config = config["mock_exam"]["single_choice"]
    selected: list[dict[str, Any]] = []
    for index, block in enumerate(exam_config["distribution"]):
        for chapter in block["chapters"]:
            selected.extend(
                choose_with_difficulty(
                    by_chapter.get(chapter, []),
                    int(block["questions_each"]),
                    exam_config.get("difficulty_distribution", {}),
                    None if args.seed is None else args.seed + chapter + index,
                )
            )
    session = make_session("mock_exam", [question["id"] for question in selected], {"seed": args.seed, "distribution": exam_config["distribution"]})
    return session, selected


def build_wrong(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    archive = load_archive()
    _, by_id, _ = load_all_questions()
    archived_ids = [item.get("question_id") for item in archive.get("archive", []) if item.get("question_id")]
    archived_questions = [by_id[qid] for qid in archived_ids if qid in by_id]
    archived_questions = filter_questions(archived_questions, args)
    selected = choose_questions(archived_questions, args.count, seed=args.seed, difficulty=args.difficulty)
    session = make_session(
        "wrong_retry",
        [question["id"] for question in selected],
        {
            "count": args.count,
            "difficulty": args.difficulty,
            "knowledge_point": args.knowledge_point,
            "section": args.section,
            "tag": args.tag,
            "seed": args.seed,
        },
    )
    return session, selected


def build_start_payload(args: argparse.Namespace, write: bool | None = None) -> dict[str, Any]:
    if args.mode == "mock":
        session, selected = build_mock(args)
    elif args.mode == "wrong":
        session, selected = build_wrong(args)
    else:
        session, selected = build_practice(args)
    write = should_write_session(args) if write is None else write
    next_step = f"Submit answers with: python scripts/study.py submit --session {session['id']} --answers \"A B C ...\""
    return {
        "session": session,
        "session_file": session_file_value(session, write),
        "questions": [public_question(question, include_answer=False) for question in selected],
        "next_step": session_next_step(next_step, write),
    }


def command_start(args: argparse.Namespace) -> int:
    payload = build_start_payload(args)
    if args.format == "markdown":
        print(f"Session: {payload['session']['id']}")
        print(f"File: {payload['session_file']}\n")
        if payload["questions"]:
            print(render_questions_markdown(payload["questions"]))
            print(payload["next_step"])
        else:
            print("No questions matched this request.")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def grade_session(session: dict[str, Any], answers: dict[str, str], record: bool) -> dict[str, Any]:
    _, by_id, _ = load_all_questions()
    if session.get("type") == "past_exam":
        by_id = {**by_id, **past_exam_choice_lookup()}
    if session.get("type") == "standards_training":
        by_id = {**by_id, **standards_question_lookup()}
    if session.get("type") == "sprint_training":
        by_id = {**by_id, **sprint_training_question_lookup()}
    results: list[dict[str, Any]] = []
    answer_records: list[dict[str, Any]] = []
    correct_count = 0
    wrong_questions: list[dict[str, Any]] = []

    for qid in session.get("question_ids", []):
        question = by_id.get(qid)
        if not question:
            continue
        user_answer = answers.get(qid, "")
        correct_answer = question.get("answer")
        is_correct = user_answer == correct_answer
        correct_count += 1 if is_correct else 0
        result = {
            "question_id": qid,
            "chapter": question.get("chapter"),
            "knowledge_point": question.get("knowledge_point"),
            "section": question.get("section"),
            "source": question.get("source"),
            "year": question.get("year"),
            "period": question.get("period"),
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": question.get("explanation"),
        }
        results.append(result)
        answer_records.append(
            {
                "session_id": session.get("id"),
                "question_id": qid,
                "chapter": question.get("chapter"),
                "knowledge_point": question.get("knowledge_point"),
                "section": question.get("section"),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "answered_at": session.get("created_at"),
            }
        )
        if not is_correct:
            wrong_questions.append(question)
            if record:
                record_wrong_answer(question, user_answer)
        elif record and session.get("type") == "wrong_retry":
            mark_reviewed(qid)

    total = len(results)
    summary = {
        "session_id": session.get("id"),
        "total": total,
        "correct": correct_count,
        "wrong": total - correct_count,
        "score_percent": round((correct_count / total) * 100, 2) if total else 0,
    }
    if record:
        append_progress(session, answer_records, summary)
    return {"summary": summary, "results": results, "recorded": record, "recommendation": recommendation(summary, results)}


def recommendation(summary: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    wrong = [item for item in results if not item["is_correct"]]
    if not wrong:
        return {"message": "本次全对。建议提高难度或进入下一章。", "focus": []}
    focus_counts: dict[str, int] = {}
    for item in wrong:
        key = item.get("knowledge_point") or item.get("section") or item.get("chapter")
        focus_counts[key] = focus_counts.get(key, 0) + 1
    focus = sorted(focus_counts.items(), key=lambda item: item[1], reverse=True)
    return {
        "message": "优先复习本次错题对应知识点，并在到期复习中再次检查。",
        "focus": [{"knowledge_point": key, "wrong": count} for key, count in focus[:5]],
    }


def render_grade_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"Score: {summary['correct']}/{summary['total']} ({summary['score_percent']}%)",
        f"Recorded: {payload['recorded']}",
    ]
    if payload.get("session_id"):
        lines.append(f"Session: {payload['session_id']}")
    for item in payload["results"]:
        mark = "OK" if item["is_correct"] else "WRONG"
        lines.append(f"- {mark} {item['question_id']}: your {item['user_answer'] or '-'}, answer {item['correct_answer']}")
        if not item["is_correct"]:
            lines.append(f"  {item['explanation']}")
    lines.append("")
    lines.append(f"Next: {payload['recommendation']['message']}")
    return "\n".join(lines) + "\n"


def command_submit(args: argparse.Namespace) -> int:
    session_path = resolve_session(args.session)
    session = load_json(session_path)
    answers = parse_answer_text(args.answers, session.get("question_ids", []))
    payload = grade_session(session, answers, record=not args.no_record)
    payload["session_id"] = session.get("id")
    if args.format == "markdown":
        print(render_grade_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def due_items(limit: int, review_date_text: str | None = None) -> list[dict[str, Any]]:
    return due_review_items(limit, review_date_text)


def command_review(args: argparse.Namespace) -> int:
    if args.mark_reviewed:
        updated = [mark_reviewed(qid) for qid in args.mark_reviewed]
        print(json.dumps({"updated": [item for item in updated if item]}, ensure_ascii=False, indent=2))
        return 0
    due = due_items(args.limit, args.date)
    payload = {"date": (parse_date(args.date) or today()).isoformat(), "count": len(due), "due": due}
    if args.format == "markdown":
        print(f"Due review on {payload['date']}: {len(due)} item(s)")
        for item in due:
            archive_item = item["archive"]
            question = item.get("question") or {}
            print(f"- {archive_item.get('question_id')} {archive_item.get('chapter')} wrong_count={archive_item.get('wrong_count')}")
            print(f"  {question.get('question')}")
            print(f"  Answer: {question.get('answer')}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_continue_payload(args: argparse.Namespace) -> dict[str, Any]:
    record = latest_session(kind=getattr(args, "type", None), open_only=not args.any)
    if record is None and not args.any:
        record = latest_session(kind=getattr(args, "type", None), open_only=False)
    if record is None:
        next_step = "python scripts/study.py start --chapters 12 --count 5 --format markdown"
        if getattr(args, "type", None) == "standards_training":
            next_step = "python scripts/study.py standards start --count 5 --format markdown"
        elif getattr(args, "type", None) == "past_exam":
            next_step = "python scripts/study.py past-exam start --count 5 --format markdown"
        elif getattr(args, "type", None) == "past_exam_case":
            next_step = "python scripts/study.py past-exam case --count 1 --format markdown"
        elif getattr(args, "type", None) == "case_study":
            next_step = f"python scripts/study.py case start --chapters {case_range_chapters_text()} --count 1 --format markdown"
        elif getattr(args, "type", None) == "sprint_training":
            next_step = "python scripts/study.py sprint-training start --count 5 --format markdown"
        return {
            "message": "没有找到历史 session，建议先开始一次练习。",
            "next_step": next_step,
        }

    session = record["session"]
    path = record["path"]
    payload = {
        "session": session,
        "session_file": str(path.relative_to(ROOT)),
        "completed": is_session_completed(session),
        "type": session.get("type"),
        "created_at": session.get("created_at"),
    }
    if session.get("type") in {"case_study", "past_exam_case"}:
        source_cases = load_past_exam_cases() if session.get("type") == "past_exam_case" else load_case_studies()
        cases_by_id = {case["id"]: case for case in source_cases}
        cases = [public_case(cases_by_id[case_id]) for case_id in session.get("case_ids", []) if case_id in cases_by_id]
        payload["cases"] = cases
        payload["next_step"] = f"python scripts/study.py case submit --session {session['id']} --answers \"...\" --format markdown"
    else:
        _, by_id, _ = load_all_questions()
        if session.get("type") == "past_exam":
            by_id = {**by_id, **past_exam_choice_lookup()}
        if session.get("type") == "standards_training":
            by_id = {**by_id, **standards_question_lookup()}
        if session.get("type") == "sprint_training":
            by_id = {**by_id, **sprint_training_question_lookup()}
        if session.get("type") == "past_exam":
            questions = [public_past_exam_question(by_id[qid]) for qid in session.get("question_ids", []) if qid in by_id]
        elif session.get("type") == "standards_training":
            questions = [public_standard_question(by_id[qid]) for qid in session.get("question_ids", []) if qid in by_id]
        elif session.get("type") == "sprint_training":
            questions = [public_sprint_training_question(by_id[qid]) for qid in session.get("question_ids", []) if qid in by_id]
        else:
            questions = [public_question(by_id[qid]) for qid in session.get("question_ids", []) if qid in by_id]
        payload["questions"] = questions
        payload["next_step"] = f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown"
    return payload


def render_continue_markdown(payload: dict[str, Any]) -> str:
    if payload.get("message"):
        return f"{payload['message']}\nNext: {display_command(payload['next_step'])}\n"
    lines = [
        "# 继续学习",
        "",
        f"- Session: {payload['session']['id']}",
        f"- File: {payload['session_file']}",
        f"- 类型：{payload['type']}",
        f"- 状态：{'已提交/已完成' if payload['completed'] else '未完成'}",
        "",
    ]
    if payload.get("questions"):
        lines.append(render_questions_markdown(payload["questions"]).rstrip())
    if payload.get("cases"):
        for case in payload["cases"]:
            lines.append(render_case_markdown(case).rstrip())
            lines.append("")
    lines.append(f"Next: {display_command(payload['next_step'])}")
    return "\n".join(lines).rstrip() + "\n"


def command_continue(args: argparse.Namespace) -> int:
    payload = build_continue_payload(args)
    if args.format == "markdown":
        print(render_continue_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_drill_payload(args: argparse.Namespace, write: bool | None = None) -> dict[str, Any]:
    mastery = build_mastery_payload(argparse.Namespace(limit=max(args.count * 3, 10), chapter=args.chapter))
    target_points = [row for row in mastery["weak_points"] if row["level"] in {"初学", "不稳定"}]
    if len(target_points) < args.count:
        target_points.extend(row for row in mastery["weak_points"] if row not in target_points)
    _, _, by_chapter = load_all_questions()
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for row in target_points:
        chapter_numbers = list(row.get("chapters", {}).keys())
        candidates = []
        for chapter_no in chapter_numbers:
            candidates.extend(by_chapter.get(int(chapter_no), []))
        candidates = [question for question in candidates if str(question.get("knowledge_point") or "") == row["knowledge_point"]]
        picked = choose_questions(candidates, 1, seed=args.seed, exclude_ids=selected_ids)
        selected.extend(picked)
        selected_ids.update(question["id"] for question in picked)
        if len(selected) >= args.count:
            break
    if len(selected) < args.count:
        chapters = [int(args.chapter)] if args.chapter else list(range(1, 25))
        fallback = [question for chapter in chapters for question in by_chapter.get(chapter, [])]
        selected.extend(choose_questions(fallback, args.count - len(selected), seed=args.seed, exclude_ids=selected_ids, difficulty=args.difficulty))
    selected = selected[: args.count]
    session = make_session("drill", [question["id"] for question in selected], {"chapter": args.chapter, "count": args.count, "difficulty": args.difficulty, "seed": args.seed})
    write = should_write_session(args) if write is None else write
    next_step = f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown"
    return {
        "session": session,
        "session_file": session_file_value(session, write),
        "target_points": target_points[: args.count],
        "questions": [public_question(question) for question in selected],
        "next_step": session_next_step(next_step, write),
    }


def render_drill_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 专项题单",
        "",
        f"Session: {payload['session']['id']}",
        f"File: {payload['session_file']}",
        "",
        "## 目标知识点",
    ]
    for row in payload["target_points"]:
        lines.append(f"- {row['knowledge_point']}: {row['score']}/100，{row['level']}")
    lines.append("")
    lines.append(render_questions_markdown(payload["questions"]).rstrip() if payload["questions"] else "No questions matched this request.")
    lines.append("")
    lines.append(f"Next: {display_command(payload['next_step'])}")
    return "\n".join(lines) + "\n"


def command_drill(args: argparse.Namespace) -> int:
    payload = build_drill_payload(args)
    if args.format == "markdown":
        print(render_drill_markdown(payload))
    else:
        print(json.dumps(simplify_json(payload), ensure_ascii=False, indent=2))
    return 0
