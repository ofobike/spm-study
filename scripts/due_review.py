#!/usr/bin/env python3
"""List due review questions and optionally mark items as reviewed."""

from __future__ import annotations

import argparse
import json

from study_utils import load_all_questions, load_archive, mark_reviewed, parse_date, public_question, today


def main() -> int:
    parser = argparse.ArgumentParser(description="Show due wrong-question reviews.")
    parser.add_argument("--date", default=None, help="Review date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--mark-reviewed", nargs="*", default=None, help="Question ids to mark as reviewed.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    if args.mark_reviewed is not None:
        updated = [mark_reviewed(qid) for qid in args.mark_reviewed]
        print(json.dumps({"updated": [item for item in updated if item]}, ensure_ascii=False, indent=2))
        return 0

    review_date = parse_date(args.date) or today()
    archive = load_archive()
    _, by_id, _ = load_all_questions()
    due = []
    for item in archive.get("archive", []):
        next_review = parse_date(item.get("next_review"))
        if next_review and next_review <= review_date:
            question = by_id.get(item.get("question_id"))
            due.append({"archive": item, "question": public_question(question, include_answer=True) if question else None})
    due = due[: args.limit]
    payload = {"date": review_date.isoformat(), "count": len(due), "due": due}

    if args.format == "markdown":
        print(f"Due review on {review_date.isoformat()}: {len(due)} item(s)")
        for item in due:
            question = item.get("question") or {}
            archive_item = item.get("archive") or {}
            print(f"- {archive_item.get('question_id')} {archive_item.get('chapter')} next={archive_item.get('next_review')}")
            print(f"  {question.get('question')}")
            print(f"  Answer: {question.get('answer')}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
