from __future__ import annotations

import argparse
import json
import re
from typing import Any

from study_modules.case import public_case as base_public_case, render_case_markdown
from study_modules.common import display_command, session_file_value, session_next_step, should_write_session
from study_modules.settings import PAST_EXAMS_FILE
from study_utils import ROOT, choose_questions, load_json, make_session, public_question, render_questions_markdown


def load_past_exams() -> dict[str, Any]:
    return load_json(
        PAST_EXAMS_FILE,
        {
            "stats": {},
            "choice_questions": [],
            "case_studies": [],
            "paper_topics": [],
        },
    )


def load_past_exam_choices() -> list[dict[str, Any]]:
    data = load_past_exams()
    rows = data.get("choice_questions", [])
    return rows if isinstance(rows, list) else []


def load_past_exam_cases() -> list[dict[str, Any]]:
    data = load_past_exams()
    rows = data.get("case_studies", [])
    return rows if isinstance(rows, list) else []


def load_past_exam_papers() -> list[dict[str, Any]]:
    data = load_past_exams()
    rows = data.get("paper_topics", [])
    return rows if isinstance(rows, list) else []

def filter_year_period(rows: list[dict[str, Any]], year: int | None = None, period: str | None = None) -> list[dict[str, Any]]:
    result = list(rows)
    if year is not None:
        result = [row for row in result if int(row.get("year") or 0) == int(year)]
    if period:
        result = [row for row in result if str(row.get("period") or "") == period]
    return result

def public_past_exam_question(question: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    result = public_question(question, include_answer=include_answer)
    for key in ("year", "period", "subject", "number", "source_pdf"):
        if key in question:
            result[key] = question[key]
    return result


def past_exam_choice_lookup() -> dict[str, dict[str, Any]]:
    return {str(question.get("id")): question for question in load_past_exam_choices() if question.get("id")}


def build_past_exam_choice_payload(args: argparse.Namespace, write: bool | None = None) -> dict[str, Any]:
    choices = filter_year_period(load_past_exam_choices(), getattr(args, "year", None), getattr(args, "period", None))
    available = len(choices)
    selected = choose_questions(choices, int(args.count), seed=getattr(args, "seed", None))
    session = make_session(
        "past_exam",
        [question["id"] for question in selected],
        {
            "year": getattr(args, "year", None),
            "period": getattr(args, "period", None),
            "count": int(args.count),
            "seed": getattr(args, "seed", None),
            "source": str(PAST_EXAMS_FILE.relative_to(ROOT)),
        },
    )
    write = should_write_session(args) if write is None else write
    next_step = f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown"
    return {
        "title": "历年真题选择题",
        "session": session,
        "session_file": session_file_value(session, write),
        "year": getattr(args, "year", None),
        "period": getattr(args, "period", None),
        "available": available,
        "questions": [public_past_exam_question(question) for question in selected],
        "next_step": session_next_step(next_step, write),
    }


def render_past_exam_choice_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 历年真题选择题",
        "",
        f"- Session: {payload['session']['id']}",
        f"- File: {payload['session_file']}",
        f"- 筛选：{payload.get('year') or '全部年份'} {payload.get('period') or ''}".rstrip(),
        f"- 可用题数：{payload['available']}",
        "",
    ]
    questions = payload.get("questions") or []
    if questions:
        lines.append(render_questions_markdown(questions).rstrip())
        lines.append("")
        lines.append(f"Next: {display_command(payload['next_step'])}")
    else:
        lines.append("没有匹配到可训练的历年真题选择题。")
    return "\n".join(lines) + "\n"


def command_past_exam_start(args: argparse.Namespace) -> int:
    payload = build_past_exam_choice_payload(args)
    if args.format == "markdown":
        print(render_past_exam_choice_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def public_past_exam_case(case: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    result = base_public_case(case, include_answer=include_answer)
    for key in ("year", "period", "subject", "number", "source_ref", "source_pdf", "tags", "source"):
        if key in case:
            result[key] = case[key]
    return result


def build_past_exam_case_payload(args: argparse.Namespace, write: bool | None = None) -> dict[str, Any]:
    cases = filter_year_period(load_past_exam_cases(), getattr(args, "year", None), getattr(args, "period", None))
    available = len(cases)
    selected = choose_questions(cases, int(args.count), seed=getattr(args, "seed", None))
    session = make_session(
        "past_exam_case",
        [case["id"] for case in selected],
        {
            "year": getattr(args, "year", None),
            "period": getattr(args, "period", None),
            "count": int(args.count),
            "seed": getattr(args, "seed", None),
            "source": str(PAST_EXAMS_FILE.relative_to(ROOT)),
        },
    )
    session["case_ids"] = session.pop("question_ids")
    session["answers_template"] = {question["id"]: "" for case in selected for question in case.get("questions", [])}
    write = should_write_session(args) if write is None else write
    next_step = f"python scripts/study.py case submit --session {session['id']} --answers \"...\" --format markdown"
    return {
        "title": "历年案例真题",
        "session": session,
        "session_file": session_file_value(session, write),
        "year": getattr(args, "year", None),
        "period": getattr(args, "period", None),
        "available": available,
        "cases": [public_past_exam_case(case, include_answer=getattr(args, "show_answer", False)) for case in selected],
        "next_step": session_next_step(next_step, write),
    }


def render_past_exam_case_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 历年案例真题",
        "",
        f"- Session: {payload['session']['id']}",
        f"- File: {payload['session_file']}",
        f"- 筛选：{payload.get('year') or '全部年份'} {payload.get('period') or ''}".rstrip(),
        f"- 可用案例：{payload['available']}",
    ]
    if not payload.get("cases"):
        lines.append("")
        lines.append("没有匹配到可训练的案例真题。")
        return "\n".join(lines) + "\n"
    for case in payload["cases"]:
        lines.append("")
        lines.append(render_case_markdown(case, include_answer=False).rstrip())
    lines.append("")
    lines.append(f"Next: {payload['next_step']}")
    return "\n".join(lines) + "\n"


def command_past_exam_case(args: argparse.Namespace) -> int:
    payload = build_past_exam_case_payload(args)
    if args.format == "markdown":
        print(render_past_exam_case_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_past_exam_paper_payload(args: argparse.Namespace) -> dict[str, Any]:
    topics = filter_year_period(load_past_exam_papers(), getattr(args, "year", None), getattr(args, "period", None))
    if getattr(args, "topic", None):
        topic_text = str(args.topic)
        topics = [topic for topic in topics if topic_text in str(topic.get("title") or "") or topic_text in str(topic.get("prompt") or "")]
    available = len(topics)
    limit = max(1, int(getattr(args, "count", 5) or 5))
    selected = choose_questions(topics, limit, seed=getattr(args, "seed", None))
    return {
        "title": "历年论文真题",
        "year": getattr(args, "year", None),
        "period": getattr(args, "period", None),
        "available": available,
        "topics": selected,
        "source": str(PAST_EXAMS_FILE.relative_to(ROOT)),
    }


def render_past_exam_paper_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 历年论文真题",
        "",
        f"- 筛选：{payload.get('year') or '全部年份'} {payload.get('period') or ''}".rstrip(),
        f"- 可用题目：{payload['available']}",
        f"- 来源：{payload['source']}",
        "",
    ]
    if not payload.get("topics"):
        lines.append("没有匹配到论文真题。")
        return "\n".join(lines) + "\n"
    for index, topic in enumerate(payload["topics"], start=1):
        lines.append(f"{index}. [{topic.get('id')}] {topic.get('year')}{topic.get('period') or ''} {topic.get('title')}")
        lines.append(f"   Source: {topic.get('source_ref')}")
        prompt = str(topic.get("prompt") or "").strip()
        if prompt:
            lines.append("   " + re.sub(r"\s+", " ", prompt[:260]).strip())
        lines.append(f"   训练命令：python scripts/study.py paper --topic \"{topic.get('title')}\" --format markdown")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_past_exam_paper(args: argparse.Namespace) -> int:
    payload = build_past_exam_paper_payload(args)
    if args.format == "markdown":
        print(render_past_exam_paper_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
