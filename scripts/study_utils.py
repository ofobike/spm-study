"""Shared utilities for spm-study automation scripts."""

from __future__ import annotations

import json
import random
import re
import shlex
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_DIR = ROOT / "assets" / "questions"
CHAPTERS_DIR = QUESTIONS_DIR / "chapters"
SESSIONS_DIR = QUESTIONS_DIR / "sessions"
CONFIG_PATH = QUESTIONS_DIR / "config.json"
ARCHIVE_PATH = QUESTIONS_DIR / "archive.json"
PROGRESS_PATH = QUESTIONS_DIR / "progress.json"
CHOICES = {"A", "B", "C", "D"}


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


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


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def today() -> date:
    return date.today()


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def normalize_answer(answer: str | None) -> str:
    if not answer:
        return ""
    return answer.strip().upper()[:1]


def chapter_label(chapter_no: int) -> str:
    return f"第{chapter_no}章"


def chapter_no_from_label(label: str) -> int | None:
    match = re.search(r"第(\d+)章", label or "")
    return int(match.group(1)) if match else None


def parse_chapters(value: str | None, default: list[int] | None = None) -> list[int]:
    if not value:
        return default or list(range(1, 25))
    chapters: list[int] = []
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start, end = [int(x.strip()) for x in item.split("-", 1)]
            chapters.extend(range(start, end + 1))
        else:
            chapters.append(int(item))
    return sorted(dict.fromkeys(chapters))


def load_config() -> dict[str, Any]:
    return load_json(CONFIG_PATH)


def load_archive() -> dict[str, Any]:
    return load_json(
        ARCHIVE_PATH,
        {
            "archive": [],
            "stats": {"total_wrong": 0, "by_chapter": {}},
            "review_schedule": {
                "enabled": True,
                "intervals_days": [1, 3, 7, 14, 30],
                "description": "Review after 1, 3, 7, 14, and 30 days.",
            },
            "review_history": [],
        },
    )


def load_progress() -> dict[str, Any]:
    return load_json(
        PROGRESS_PATH,
        {
            "sessions": [],
            "answers": [],
            "stats": {"total_answered": 0, "total_correct": 0, "by_chapter": {}},
            "last_updated": None,
        },
    )


def load_all_questions() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[int, list[dict[str, Any]]]]:
    questions: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    by_chapter: dict[int, list[dict[str, Any]]] = {chapter: [] for chapter in range(1, 25)}

    for path in sorted(CHAPTERS_DIR.glob("chapter_*.json")):
        data = load_json(path)
        if not isinstance(data, list):
            continue
        for question in data:
            if not isinstance(question, dict):
                continue
            qid = question.get("id")
            chapter_no = chapter_no_from_label(question.get("chapter", ""))
            if not qid or chapter_no is None:
                continue
            questions.append(question)
            by_id[qid] = question
            by_chapter.setdefault(chapter_no, []).append(question)

    return questions, by_id, by_chapter


def public_question(question: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    result = {
        "id": question.get("id"),
        "chapter": question.get("chapter"),
        "question": question.get("question"),
        "options": question.get("options", []),
        "source": question.get("source"),
    }
    for key in ("difficulty", "knowledge_point", "section", "tags", "source_ref"):
        if key in question:
            result[key] = question[key]
    if include_answer:
        result["answer"] = question.get("answer")
        result["explanation"] = question.get("explanation")
    return result


def render_questions_markdown(questions: list[dict[str, Any]], include_answer: bool = False) -> str:
    lines: list[str] = []
    for index, question in enumerate(questions, start=1):
        lines.append(f"{index}. [{question.get('id')}] {question.get('question')}")
        for option in question.get("options", []):
            lines.append(f"   {option}")
        if include_answer:
            lines.append(f"   Answer: {question.get('answer')}")
            lines.append(f"   Explanation: {question.get('explanation')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def choose_questions(
    candidates: list[dict[str, Any]],
    count: int,
    seed: int | None = None,
    exclude_ids: set[str] | None = None,
    difficulty: str | None = None,
) -> list[dict[str, Any]]:
    pool = list(candidates)
    if exclude_ids:
        pool = [question for question in pool if question.get("id") not in exclude_ids]
    if difficulty:
        filtered = [question for question in pool if question.get("difficulty") == difficulty]
        if filtered:
            pool = filtered
    rng = random.Random(seed)
    rng.shuffle(pool)
    return pool[: min(count, len(pool))]


def make_session(kind: str, question_ids: list[str], params: dict[str, Any]) -> dict[str, Any]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:6]
    return {
        "id": f"{kind}_{stamp}_{suffix}",
        "type": kind,
        "created_at": now_iso(),
        "question_ids": question_ids,
        "params": params,
        "answers_template": {qid: "" for qid in question_ids},
    }


def write_session(session: dict[str, Any]) -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SESSIONS_DIR / f"{session['id']}.json"
    save_json(path, session)
    return path


def load_answers(path: Path) -> dict[str, str]:
    data = load_json(path)
    if isinstance(data, dict):
        return {str(key): normalize_answer(str(value)) for key, value in data.items()}
    if isinstance(data, list):
        answers: dict[str, str] = {}
        for item in data:
            if isinstance(item, dict) and "question_id" in item and "answer" in item:
                answers[str(item["question_id"])] = normalize_answer(str(item["answer"]))
        return answers
    raise ValueError("answers must be a JSON object or a list of answer records")


def parse_answer_text(answer_text: str, question_ids: list[str]) -> dict[str, str]:
    text = answer_text.strip()
    if not text:
        return {}
    if text.startswith("{"):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("JSON answers must be an object mapping question id to answer")
        return {str(key): normalize_answer(str(value)) for key, value in data.items()}

    answers: dict[str, str] = {}
    if "=" in text or ":" in text:
        for part in re.split(r"[,;\n]+", text):
            item = part.strip()
            if not item:
                continue
            if "=" in item:
                key, value = item.split("=", 1)
            else:
                key, value = item.split(":", 1)
            answers[key.strip()] = normalize_answer(value)
        return answers

    try:
        parts = shlex.split(text)
    except ValueError:
        parts = [part for part in re.split(r"[\s,;]+", text) if part.strip()]
    values = [normalize_answer(part) for part in parts if part.strip()]
    return {qid: value for qid, value in zip(question_ids, values)}


def recompute_progress_stats(progress: dict[str, Any]) -> None:
    by_chapter: dict[str, dict[str, int]] = {}
    total_answered = 0
    total_correct = 0
    for record in progress.get("answers", []):
        chapter = record.get("chapter", "unknown")
        bucket = by_chapter.setdefault(chapter, {"answered": 0, "correct": 0, "wrong": 0})
        bucket["answered"] += 1
        total_answered += 1
        if record.get("is_correct"):
            bucket["correct"] += 1
            total_correct += 1
        else:
            bucket["wrong"] += 1
    progress["stats"] = {
        "total_answered": total_answered,
        "total_correct": total_correct,
        "by_chapter": by_chapter,
    }
    progress["last_updated"] = now_iso()


def append_progress(session: dict[str, Any], answer_records: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    progress = load_progress()
    sessions = progress.setdefault("sessions", [])
    sessions.append(
        {
            "id": session.get("id"),
            "type": session.get("type"),
            "created_at": session.get("created_at"),
            "graded_at": now_iso(),
            "summary": summary,
        }
    )
    progress.setdefault("answers", []).extend(answer_records)
    recompute_progress_stats(progress)
    save_json(PROGRESS_PATH, progress)


def recompute_archive_stats(archive: dict[str, Any]) -> None:
    by_chapter: dict[str, dict[str, int]] = {}
    total_wrong = 0
    for item in archive.get("archive", []):
        chapter = item.get("chapter", "unknown")
        wrong_count = int(item.get("wrong_count", item.get("error_count", 1)) or 1)
        total_wrong += wrong_count
        bucket = by_chapter.setdefault(chapter, {"wrong_items": 0, "wrong_attempts": 0})
        bucket["wrong_items"] += 1
        bucket["wrong_attempts"] += wrong_count
    archive["stats"] = {"total_wrong": total_wrong, "by_chapter": by_chapter}


def record_wrong_answer(question: dict[str, Any], wrong_answer: str, timestamp: str | None = None) -> dict[str, Any]:
    archive = load_archive()
    timestamp = timestamp or now_iso()
    intervals = archive.get("review_schedule", {}).get("intervals_days") or load_config().get("review_intervals_days", [1, 3, 7, 14, 30])
    first_interval = int(intervals[0])
    qid = question["id"]
    items = archive.setdefault("archive", [])
    item = next((entry for entry in items if entry.get("question_id") == qid), None)
    next_review = (datetime.fromisoformat(timestamp) + timedelta(days=first_interval)).date().isoformat()

    if item is None:
        item = {
            "question_id": qid,
            "chapter": question.get("chapter"),
            "wrong_answer": wrong_answer,
            "correct_answer": question.get("answer"),
            "timestamp": timestamp,
            "wrong_count": 1,
            "review_count": 0,
            "next_review": next_review,
        }
        items.append(item)
    else:
        item["wrong_answer"] = wrong_answer
        item["correct_answer"] = question.get("answer")
        item["timestamp"] = timestamp
        item["wrong_count"] = int(item.get("wrong_count", item.get("error_count", 1)) or 1) + 1
        item["next_review"] = next_review

    recompute_archive_stats(archive)
    save_json(ARCHIVE_PATH, archive)
    return item


def mark_reviewed(question_id: str, reviewed_at: str | None = None) -> dict[str, Any] | None:
    archive = load_archive()
    reviewed_at = reviewed_at or now_iso()
    intervals = archive.get("review_schedule", {}).get("intervals_days") or load_config().get("review_intervals_days", [1, 3, 7, 14, 30])
    item = next((entry for entry in archive.get("archive", []) if entry.get("question_id") == question_id), None)
    if item is None:
        return None

    review_count = int(item.get("review_count", 0)) + 1
    item["review_count"] = review_count
    if review_count < len(intervals):
        item["next_review"] = (datetime.fromisoformat(reviewed_at) + timedelta(days=int(intervals[review_count]))).date().isoformat()
    else:
        item["next_review"] = None
        item["mastered_at"] = reviewed_at

    archive.setdefault("review_history", []).append({"question_id": question_id, "reviewed_at": reviewed_at})
    save_json(ARCHIVE_PATH, archive)
    return item
