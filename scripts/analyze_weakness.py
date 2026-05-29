#!/usr/bin/env python3
"""Analyze weak chapters from progress and wrong-question archive."""

from __future__ import annotations

import argparse
import json

from study_utils import load_archive, load_config, load_progress


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze weak chapters from progress and archive data.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    config = load_config()
    ability_chapters = set(config.get("ability_chapters", []))
    ability_weight = float(config.get("ability_weight", 1.5))
    progress = load_progress()
    archive = load_archive()
    by_chapter_progress = progress.get("stats", {}).get("by_chapter", {})
    by_chapter_archive = archive.get("stats", {}).get("by_chapter", {})

    rows = []
    for chapter_no in range(1, int(config.get("chapter_count", 24)) + 1):
        chapter = f"第{chapter_no}章"
        answered = int(by_chapter_progress.get(chapter, {}).get("answered", 0))
        correct = int(by_chapter_progress.get(chapter, {}).get("correct", 0))
        wrong_attempts = int(by_chapter_archive.get(chapter, {}).get("wrong_attempts", 0))
        weight = ability_weight if chapter_no in ability_chapters else 1.0
        accuracy = round(correct / answered, 4) if answered else None
        if accuracy is None:
            priority = wrong_attempts * weight
        else:
            priority = ((1 - accuracy) * max(answered, 1) + wrong_attempts) * weight
        rows.append(
            {
                "chapter": chapter,
                "answered": answered,
                "correct": correct,
                "accuracy": accuracy,
                "wrong_attempts": wrong_attempts,
                "weight": weight,
                "priority": round(priority, 4),
                "basis": "accuracy+archive" if answered else "archive_only",
            }
        )

    rows.sort(key=lambda item: item["priority"], reverse=True)
    rows = rows[: args.limit]
    payload = {"weak_chapters": rows}

    if args.format == "markdown":
        print("Weakness analysis")
        for row in rows:
            accuracy = "-" if row["accuracy"] is None else f"{row['accuracy'] * 100:.1f}%"
            print(
                f"- {row['chapter']}: priority={row['priority']}, "
                f"answered={row['answered']}, accuracy={accuracy}, wrong_attempts={row['wrong_attempts']}"
            )
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
