#!/usr/bin/env python3
"""Generate a comprehensive knowledge mock exam session."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from study_utils import (
    ROOT,
    choose_questions,
    load_all_questions,
    load_config,
    make_session,
    public_question,
    render_questions_markdown,
    write_session,
)


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


def choose_with_difficulty(pool, count: int, difficulty_distribution: dict[str, float], seed: int | None):
    if not pool or not all("difficulty" in question for question in pool):
        return choose_questions(pool, count, seed=seed)

    selected = []
    selected_ids = set()
    plan = difficulty_plan(count, difficulty_distribution)
    for offset, (difficulty, target) in enumerate(plan.items()):
        picked = choose_questions(pool, target, seed=None if seed is None else seed + offset, exclude_ids=selected_ids, difficulty=difficulty)
        selected.extend(picked)
        selected_ids.update(question["id"] for question in picked)

    if len(selected) < count:
        selected.extend(choose_questions(pool, count - len(selected), seed=seed, exclude_ids=selected_ids))
    return selected[:count]


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a mock exam from configured chapter distribution.")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--answers", action="store_true", help="Include answers and explanations in output.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    parser.add_argument("--save-session", action="store_true", help="Save a session file under assets/questions/sessions.")
    args = parser.parse_args()

    config = load_config()
    _, _, by_chapter = load_all_questions()
    distribution = config["mock_exam"]["single_choice"]["distribution"]
    difficulty_distribution = config["mock_exam"]["single_choice"].get("difficulty_distribution", {})
    selected = []
    for index, block in enumerate(distribution):
        for chapter in block["chapters"]:
            selected.extend(
                choose_with_difficulty(
                    by_chapter.get(chapter, []),
                    int(block["questions_each"]),
                    difficulty_distribution,
                    None if args.seed is None else args.seed + chapter + index,
                )
            )

    session = make_session(
        "mock_exam",
        [question["id"] for question in selected],
        {"seed": args.seed, "distribution": distribution},
    )
    session_path: Path | None = write_session(session) if args.save_session else None
    payload = {
        "session": session,
        "session_file": str(session_path.relative_to(ROOT)) if session_path else None,
        "exam": config["mock_exam"]["single_choice"],
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
