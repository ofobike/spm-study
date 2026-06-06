from __future__ import annotations

import argparse
from collections import Counter
import json
from typing import Any

from study_modules.common import display_command, simplify_json
from study_utils import chapter_no_from_label, load_all_questions, load_archive, load_progress


def knowledge_point_index() -> dict[str, dict[str, Any]]:
    questions, _, _ = load_all_questions()
    index: dict[str, dict[str, Any]] = {}
    for question in questions:
        point = str(question.get("knowledge_point") or "").strip()
        if not point:
            continue
        row = index.setdefault(point, {"knowledge_point": point, "question_count": 0, "chapters": Counter(), "sections": Counter()})
        row["question_count"] += 1
        chapter_no = chapter_no_from_label(str(question.get("chapter") or ""))
        if chapter_no is not None:
            row["chapters"][chapter_no] += 1
        section = str(question.get("section") or "").strip()
        if section:
            row["sections"][section] += 1
    return index


def practiced_knowledge_stats() -> dict[str, dict[str, Any]]:
    progress = load_progress()
    stats: dict[str, dict[str, Any]] = {}
    for answer in progress.get("answers", []):
        point = str(answer.get("knowledge_point") or "").strip()
        if not point:
            continue
        row = stats.setdefault(point, {"knowledge_point": point, "answered": 0, "correct": 0, "chapters": Counter()})
        row["answered"] += 1
        if answer.get("is_correct"):
            row["correct"] += 1
        chapter_no = chapter_no_from_label(str(answer.get("chapter") or ""))
        if chapter_no is not None:
            row["chapters"][chapter_no] += 1
    for row in stats.values():
        answered = int(row["answered"])
        row["accuracy"] = round(row["correct"] / answered, 4) if answered else None
    return stats


def chapter_command_for_point(point: str, chapters: Counter[int] | dict[int, int] | None, count: int = 5) -> str:
    chapter_part = ""
    if chapters:
        chapter_no = max(chapters.items(), key=lambda item: item[1])[0]
        chapter_part = f" --chapters {chapter_no}"
    return f"python scripts/study.py start{chapter_part} --knowledge-point {point} --count {count} --format markdown"


def mastery_level(score: float) -> str:
    if score < 20:
        return "未接触"
    if score < 45:
        return "初学"
    if score < 65:
        return "不稳定"
    if score < 85:
        return "已掌握"
    return "精通"


def mastery_action(level: str) -> str:
    return {
        "未接触": "先做基础题建立覆盖",
        "初学": "安排入门题并精读解析",
        "不稳定": "做专项题并复盘错因",
        "已掌握": "降低频率，隔几天抽查",
        "精通": "冲刺前抽查即可",
    }.get(level, "继续练习")


def recency_factor(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    recent = records[-5:]
    if not recent:
        return 0.0
    hits = sum(1 for record in recent if record.get("is_correct"))
    return hits / len(recent)


def build_mastery_rows() -> list[dict[str, Any]]:
    index = knowledge_point_index()
    progress = load_progress()
    archive = load_archive()
    by_point_records: dict[str, list[dict[str, Any]]] = {}
    wrong_by_point: Counter[str] = Counter()
    _, by_id, _ = load_all_questions()

    for answer in progress.get("answers", []):
        point = str(answer.get("knowledge_point") or "").strip()
        if point:
            by_point_records.setdefault(point, []).append(answer)

    for item in archive.get("archive", []):
        qid = item.get("question_id")
        question = by_id.get(qid)
        point = str((question or {}).get("knowledge_point") or "").strip()
        if point:
            wrong_by_point[point] += int(item.get("wrong_count", item.get("error_count", 1)) or 1)

    rows: list[dict[str, Any]] = []
    for point, meta in index.items():
        records = by_point_records.get(point, [])
        answered = len(records)
        correct = sum(1 for record in records if record.get("is_correct"))
        accuracy = correct / answered if answered else None
        volume_score = min(1.0, answered / 6)
        accuracy_score = accuracy if accuracy is not None else 0.0
        recent_score = recency_factor(records)
        wrong_penalty = min(0.3, wrong_by_point[point] * 0.06)
        score = round(max(0, min(100, (accuracy_score * 0.5 + volume_score * 0.25 + recent_score * 0.25 - wrong_penalty) * 100)), 2)
        if answered == 0:
            score = 0.0
        level = mastery_level(score)
        rows.append(
            {
                "knowledge_point": point,
                "score": score,
                "level": level,
                "answered": answered,
                "correct": correct,
                "accuracy": round(accuracy, 4) if accuracy is not None else None,
                "recent_accuracy": round(recent_score, 4) if answered else None,
                "wrong_attempts": wrong_by_point[point],
                "question_count": meta["question_count"],
                "chapters": meta["chapters"],
                "sections": meta["sections"],
                "action": mastery_action(level),
                "command": chapter_command_for_point(point, meta.get("chapters")),
            }
        )
    rows.sort(key=lambda row: (row["score"], -int(row["question_count"]), row["knowledge_point"]))
    return rows


def build_mastery_payload(args: argparse.Namespace) -> dict[str, Any]:
    rows = build_mastery_rows()
    if getattr(args, "chapter", None):
        chapter = int(args.chapter)
        rows = [row for row in rows if chapter in row.get("chapters", {})]
    levels = Counter(row["level"] for row in rows)
    total = len(rows)
    avg_score = round(sum(float(row["score"]) for row in rows) / total, 2) if total else 0
    weak_levels = {"未接触", "初学", "不稳定"}
    weak_rows = [row for row in rows if row["level"] in weak_levels]
    stable_rows = [row for row in rows if row["level"] in {"已掌握", "精通"}]
    return {
        "total_knowledge_points": total,
        "average_mastery_score": avg_score,
        "counts_by_level": dict(levels),
        "weak_points": weak_rows[: args.limit],
        "stable_points": sorted(stable_rows, key=lambda row: (-float(row["score"]), row["knowledge_point"]))[: args.limit],
        "all_points": rows,
    }


def render_mastery_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 知识点掌握度",
        "",
        f"- 知识点数：{payload['total_knowledge_points']}",
        f"- 平均掌握度：{payload['average_mastery_score']}/100",
        "",
        "## 分布",
    ]
    for level in ("未接触", "初学", "不稳定", "已掌握", "精通"):
        lines.append(f"- {level}: {payload['counts_by_level'].get(level, 0)}")
    lines.append("")
    lines.append("## 优先突破")
    if payload["weak_points"]:
        for row in payload["weak_points"]:
            lines.append(
                f"- {row['knowledge_point']}: {row['score']}/100，{row['level']}，"
                f"answered={row['answered']}，accuracy={round(row['accuracy'] * 100, 2) if row['accuracy'] is not None else '-'}%"
            )
            lines.append(f"  {row['action']}: {row['command']}")
    else:
        lines.append("- 暂无明显薄弱知识点。")
    lines.append("")
    lines.append("## 稳定掌握")
    if payload["stable_points"]:
        for row in payload["stable_points"]:
            lines.append(f"- {row['knowledge_point']}: {row['score']}/100，{row['level']}")
    else:
        lines.append("- 暂无稳定掌握知识点，先扩大练习覆盖。")
    return "\n".join(lines) + "\n"


def command_mastery(args: argparse.Namespace) -> int:
    payload = build_mastery_payload(args)
    if args.format == "markdown":
        print(render_mastery_markdown(payload))
    else:
        print(json.dumps(simplify_json(payload), ensure_ascii=False, indent=2))
    return 0


def build_coverage_payload(args: argparse.Namespace) -> dict[str, Any]:
    index = knowledge_point_index()
    practiced = practiced_knowledge_stats()
    total = len(index)
    practiced_points = set(practiced)
    unpracticed = sorted(set(index) - practiced_points)
    low_accuracy = [
        row for row in practiced.values()
        if int(row.get("answered", 0)) >= args.min_attempts and row.get("accuracy") is not None and float(row["accuracy"]) < args.threshold
    ]
    low_accuracy.sort(key=lambda row: (float(row["accuracy"]), -int(row["answered"]), row["knowledge_point"]))
    priority_unpracticed = sorted(
        (index[point] for point in unpracticed),
        key=lambda row: (-int(row["question_count"]), row["knowledge_point"]),
    )
    suggestions = []
    for row in low_accuracy[: args.limit]:
        suggestions.append(
            {
                "type": "low_accuracy",
                "knowledge_point": row["knowledge_point"],
                "accuracy": row["accuracy"],
                "answered": row["answered"],
                "command": chapter_command_for_point(row["knowledge_point"], row.get("chapters")),
            }
        )
    for row in priority_unpracticed[: max(0, args.limit - len(suggestions))]:
        suggestions.append(
            {
                "type": "unpracticed",
                "knowledge_point": row["knowledge_point"],
                "question_count": row["question_count"],
                "command": chapter_command_for_point(row["knowledge_point"], row.get("chapters")),
            }
        )
    return {
        "total_knowledge_points": total,
        "practiced_knowledge_points": len(practiced_points),
        "unpracticed_knowledge_points": len(unpracticed),
        "coverage_percent": round((len(practiced_points) / total) * 100, 2) if total else 0,
        "low_accuracy_threshold": args.threshold,
        "low_accuracy_points": low_accuracy[: args.limit],
        "top_unpracticed_points": priority_unpracticed[: args.limit],
        "suggestions": suggestions,
    }


def render_coverage_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 知识点覆盖率报告",
        "",
        f"- 知识点总数：{payload['total_knowledge_points']}",
        f"- 已练知识点：{payload['practiced_knowledge_points']}",
        f"- 未练知识点：{payload['unpracticed_knowledge_points']}",
        f"- 覆盖率：{payload['coverage_percent']}%",
        "",
    ]
    if payload["low_accuracy_points"]:
        lines.append("## 低正确率知识点")
        for row in payload["low_accuracy_points"]:
            lines.append(f"- {row['knowledge_point']}: accuracy={round(row['accuracy'] * 100, 2)}%, answered={row['answered']}")
        lines.append("")
    else:
        lines.append("## 低正确率知识点")
        lines.append("- 暂无低正确率知识点；如果进度为空，请先完成章节练习。")
        lines.append("")
    lines.append("## 优先补练知识点")
    if payload["top_unpracticed_points"]:
        for row in payload["top_unpracticed_points"]:
            chapters = ",".join(str(chapter) for chapter, _ in row["chapters"].most_common(3))
            lines.append(f"- {row['knowledge_point']}: questions={row['question_count']}, chapters={chapters}")
    else:
        lines.append("- 所有已索引知识点至少练过一次。")
    lines.append("")
    lines.append("## 建议命令")
    if payload["suggestions"]:
        for item in payload["suggestions"]:
            lines.append(f"- [{item['type']}] {item['knowledge_point']}: {item['command']}")
    else:
        lines.append("- python scripts/study.py plan --format markdown")
    return "\n".join(lines) + "\n"


def command_coverage(args: argparse.Namespace) -> int:
    payload = build_coverage_payload(args)
    if args.format == "markdown":
        print(render_coverage_markdown(payload))
    else:
        print(json.dumps(simplify_json(payload), ensure_ascii=False, indent=2))
    return 0
