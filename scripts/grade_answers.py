#!/usr/bin/env python3
"""Grade a saved practice or mock-exam session."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from study_utils import (
    ROOT,
    append_progress,
    load_all_questions,
    load_answers,
    load_json,
    normalize_answer,
    record_wrong_answer,
)


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Grade answers for a saved session.")
    parser.add_argument("--session", required=True, help="Session JSON file created by practice.py or mock_exam.py.")
    parser.add_argument("--answers", required=True, help="JSON object mapping question id to selected option.")
    parser.add_argument("--record", action="store_true", help="Record progress and archive wrong answers.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    session_path = resolve_path(args.session)
    answers_path = resolve_path(args.answers)
    session = load_json(session_path)
    answers = load_answers(answers_path)
    _, by_id, _ = load_all_questions()

    results = []
    correct_count = 0
    answer_records = []
    for qid in session.get("question_ids", []):
        question = by_id.get(qid)
        if not question:
            continue
        user_answer = normalize_answer(answers.get(qid))
        correct_answer = question.get("answer")
        is_correct = user_answer == correct_answer
        correct_count += 1 if is_correct else 0
        result = {
            "question_id": qid,
            "chapter": question.get("chapter"),
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
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "answered_at": session.get("created_at"),
            }
        )
        if args.record and not is_correct:
            record_wrong_answer(question, user_answer or "")

    total = len(results)
    summary = {
        "session_id": session.get("id"),
        "total": total,
        "correct": correct_count,
        "wrong": total - correct_count,
        "score_percent": round((correct_count / total) * 100, 2) if total else 0,
    }
    if args.record:
        append_progress(session, answer_records, summary)

    payload = {"summary": summary, "results": results, "recorded": args.record}

    if args.format == "markdown":
        print(f"Score: {summary['correct']}/{summary['total']} ({summary['score_percent']}%)")
        for item in results:
            mark = "OK" if item["is_correct"] else "WRONG"
            print(f"- {mark} {item['question_id']}: your {item['user_answer'] or '-'}, answer {item['correct_answer']}")
            if not item["is_correct"]:
                print(f"  {item['explanation']}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
