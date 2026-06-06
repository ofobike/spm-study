from __future__ import annotations

from collections import Counter
import json
import re
from pathlib import Path
from typing import Any

from study_utils import ROOT, SESSIONS_DIR, load_all_questions, load_archive, parse_date, public_question, today, write_session

def resolve_session(session_value: str) -> Path:
    path = Path(session_value)
    if path.is_absolute():
        return path
    if path.exists():
        return ROOT / path
    if session_value.endswith(".json"):
        return ROOT / session_value
    return SESSIONS_DIR / f"{session_value}.json"


def should_write_session(args: argparse.Namespace) -> bool:
    return not bool(getattr(args, "dry_run", False))


def session_file_value(session: dict[str, Any], write: bool) -> str:
    if not write:
        return "<dry-run>"
    session_path = write_session(session)
    return str(session_path.relative_to(ROOT))


def session_next_step(command: str, write: bool) -> str:
    if write:
        return command
    return "Dry run only: session was not written; rerun without --dry-run to submit answers."


def display_command(command: str) -> str:
    return re.sub(r"(python scripts/study\.py\b[^\n`]*?)\s+--format markdown\b", r"\1", str(command))


def compact_text(text: str | None) -> str:
    return re.sub(r"\s+", "", text or "")


def normalize_lookup_text(value: str | None) -> str:
    text = str(value or "").lower()
    return re.sub(r"[\s_\-—:：/\\（）()《》“”\"'，,。.;；]+", "", text)


def due_review_items(limit: int, review_date_text: str | None = None) -> list[dict[str, Any]]:
    review_date = parse_date(review_date_text) or today()
    archive = load_archive()
    _, by_id, _ = load_all_questions()
    due: list[dict[str, Any]] = []
    for item in archive.get("archive", []):
        next_review = parse_date(item.get("next_review"))
        if next_review and next_review <= review_date:
            question = by_id.get(item.get("question_id"))
            due.append({"archive": item, "question": public_question(question, include_answer=True) if question else None})
    return due[:limit]


def simplify_json(value: Any) -> Any:
    if isinstance(value, Counter):
        return dict(value)
    if isinstance(value, dict):
        return {key: simplify_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [simplify_json(item) for item in value]
    return value


def load_internal_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
