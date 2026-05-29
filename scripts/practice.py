#!/usr/bin/env python3
"""Generate a chapter practice session."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from study_utils import (
    ROOT,
    choose_questions,
    load_all_questions,
    make_session,
    parse_chapters,
    public_question,
    render_questions_markdown,
    write_session,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate chapter practice questions.")
    parser.add_argument("--chapters", default=None, help="Chapter list such as 1,2,5-7. Defaults to all chapters.")
    parser.add_argument("--count", type=int, default=5, help="Number of questions to generate.")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"], default=None)
    parser.add_argument("--knowledge-point", default=None, help="Filter by knowledge_point substring.")
    parser.add_argument("--section", default=None, help="Filter by section substring.")
    parser.add_argument("--tag", default=None, help="Filter by tag substring.")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--answers", action="store_true", help="Include answers and explanations in output.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--save-session", action="store_true", help="Save a session file under assets/questions/sessions.")
    args = parser.parse_args()

    _, _, by_chapter = load_all_questions()
    chapters = parse_chapters(args.chapters)
    candidates = [question for chapter in chapters for question in by_chapter.get(chapter, [])]
    if args.knowledge_point:
        candidates = [question for question in candidates if args.knowledge_point in str(question.get("knowledge_point", ""))]
    if args.section:
        candidates = [question for question in candidates if args.section in str(question.get("section", ""))]
    if args.tag:
        candidates = [question for question in candidates if any(args.tag in str(tag) for tag in question.get("tags", []))]
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

    session_path: Path | None = write_session(session) if args.save_session else None
    payload = {
        "session": session,
        "session_file": str(session_path.relative_to(ROOT)) if session_path else None,
        "questions": [public_question(question, include_answer=args.answers) for question in selected],
    }

    if args.format == "markdown":
        if session_path:
            print(f"Session: {session_path.relative_to(ROOT)}\n")
        print(render_questions_markdown(selected, include_answer=args.answers))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
