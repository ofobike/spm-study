#!/usr/bin/env python
"""Parse internal chapter-practice markdown into a candidate question bank.

This script intentionally writes to references/internal, not assets/questions.
Candidate questions must be reviewed, deduplicated, and enriched before they are
merged into the formal training question bank.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "references" / "internal" / "chapter-practice" / "2025新版系规千题闯关-解析版.md"
OUTPUT_DIR = ROOT / "references" / "internal" / "chapter-practice" / "structured"
CHAPTER_TITLES = {
    1: "信息系统与信息技术发展",
    2: "数字中国与数智化发展",
    3: "系统科学与哲学方法论",
    4: "信息系统规划",
    5: "应用系统规划",
    6: "云资源规划",
    7: "网络环境规划",
    8: "数据资源规划",
    9: "信息安全规划",
    10: "云原生系统规划",
    11: "信息系统治理",
    12: "信息系统服务管理",
    13: "人员管理",
    14: "规范与过程管理",
    15: "技术与研发管理",
    16: "资源与工具管理",
    17: "信息系统项目管理",
    18: "智慧城市发展规划",
    19: "智慧园区发展规划",
    20: "数字乡村发展规划",
    21: "企业数字化转型发展规划",
    22: "智能制造发展规划",
    23: "新型消费系统规划",
    24: "法律法规和标准规范",
}
CN_NUMBERS = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "十一": 11,
    "十二": 12,
    "十三": 13,
    "十四": 14,
    "十五": 15,
    "十六": 16,
    "十七": 17,
    "十八": 18,
    "十九": 19,
    "二十": 20,
    "二十一": 21,
    "二十二": 22,
    "二十三": 23,
    "二十四": 24,
}


def normalize_text(text: str) -> str:
    value = text.replace("\u3000", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def normalize_question_text(lines: list[str]) -> str:
    text = "\n".join(line.strip() for line in lines if line.strip())
    text = text.replace("（\n）。", "（ ）。")
    text = text.replace("（\n）", "（ ）")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def chapter_from_heading(line: str) -> int | None:
    match = re.match(r"^第([一二三四五六七八九十]{1,3})章", line.strip())
    if match:
        return CN_NUMBERS.get(match.group(1))
    return None


def clean_lines(text: str) -> list[str]:
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith(">") or line == "---":
            continue
        if re.match(r"^## 第 \d+ 页$", line):
            continue
        if line == "目录":
            continue
        if re.match(r"^第[一二三四五六七八九十]{1,3}章.+（\d+ 题）.*\d+$", line):
            continue
        lines.append(line)
    return lines


def parse_candidate_questions(text: str) -> list[dict[str, Any]]:
    lines = clean_lines(text)
    questions: list[dict[str, Any]] = []
    chapter = None
    current: dict[str, Any] | None = None
    state = "idle"
    local_no = 0

    def flush() -> None:
        nonlocal current
        if not current:
            return
        if current.get("question") and len(current.get("options", [])) >= 4 and current.get("answer"):
            questions.append(current)
        current = None

    for line in lines:
        chapter_no = chapter_from_heading(line)
        if chapter_no:
            flush()
            chapter = chapter_no
            local_no = 0
            state = "idle"
            continue

        match = re.match(r"^(\d+)\.(.+)", line)
        if match and chapter:
            flush()
            local_no = int(match.group(1))
            current = {
                "id": f"internal_qt_ch{chapter:02d}_{local_no:04d}",
                "chapter": f"第{chapter}章",
                "chapter_no": chapter,
                "chapter_title": CHAPTER_TITLES.get(chapter, ""),
                "question": normalize_question_text([match.group(2)]),
                "options": [],
                "answer": "",
                "explanation": "",
                "source": "2025新版系规千题闯关-解析版",
                "source_ref": f"references/internal/chapter-practice/2025新版系规千题闯关-解析版.md#第{chapter}章",
                "status": "candidate",
            }
            state = "question"
            continue

        if current is None:
            continue

        option_match = re.match(r"^([ABCD])\.(.*)", line)
        if option_match:
            current["options"].append(f"{option_match.group(1)}. {option_match.group(2).strip()}")
            state = "options"
            continue

        answer_match = re.match(r"^参考答案[:：]\s*([ABCD])", line)
        if answer_match:
            current["answer"] = answer_match.group(1)
            state = "answer"
            continue

        explanation_match = re.match(r"^解析[:：]\s*(.*)", line)
        if explanation_match:
            current["explanation"] = explanation_match.group(1).strip()
            state = "explanation"
            continue

        if state == "question":
            current["question"] = normalize_question_text([current["question"], line])
        elif state == "options" and current["options"]:
            current["options"][-1] = f"{current['options'][-1]} {line}".strip()
        elif state == "explanation":
            current["explanation"] = normalize_question_text([current.get("explanation", ""), line])

    flush()
    return questions


def audit_candidates(questions: list[dict[str, Any]]) -> dict[str, Any]:
    by_chapter = Counter(int(item["chapter_no"]) for item in questions)
    answers = Counter(item["answer"] for item in questions)
    issue_counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = defaultdict(list)

    seen_text: dict[str, str] = {}
    for item in questions:
        qid = item["id"]
        if len(item.get("options", [])) != 4:
            issue_counts["option_count"] += 1
            samples["option_count"].append(qid)
        if item.get("answer") not in {"A", "B", "C", "D"}:
            issue_counts["answer_invalid"] += 1
            samples["answer_invalid"].append(qid)
        if len(item.get("explanation", "")) < 12:
            issue_counts["short_explanation"] += 1
            samples["short_explanation"].append(qid)
        normalized_question = re.sub(r"\s+", "", item.get("question", ""))
        if normalized_question in seen_text:
            issue_counts["duplicate_question_text"] += 1
            samples["duplicate_question_text"].append(qid)
        else:
            seen_text[normalized_question] = qid

    return {
        "total": len(questions),
        "by_chapter": dict(sorted(by_chapter.items())),
        "answer_distribution": dict(sorted(answers.items())),
        "issue_counts": dict(sorted(issue_counts.items())),
        "issue_samples": {key: value[:10] for key, value in samples.items()},
    }


def write_outputs(questions: list[dict[str, Any]], source: Path, write: bool = True) -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = audit_candidates(questions)
    by_chapter: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        by_chapter[int(question["chapter_no"])].append(question)

    written: list[Path] = []
    if write:
        all_file = OUTPUT_DIR / "candidate_questions.json"
        all_file.write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(all_file)
        for chapter, rows in sorted(by_chapter.items()):
            path = OUTPUT_DIR / f"chapter_{chapter:02d}.json"
            path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            written.append(path)
        audit_file = OUTPUT_DIR / "quality_report.json"
        audit_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(audit_file)

        lines = [
            "# 章节习题候选题源",
            "",
            f"> 来源：`{source.relative_to(ROOT)}`",
            "> 说明：候选题源不直接合并正式题库；合并前必须去重、补元数据并通过回归测试。",
            "",
            f"- 候选题数：{audit['total']}",
            f"- 答案分布：{audit['answer_distribution']}",
            f"- 质量问题：{audit['issue_counts'] or '暂无'}",
            "",
            "| 章 | 章节 | 候选题数 | 文件 |",
            "|---:|---|---:|---|",
        ]
        for chapter, count in sorted(audit["by_chapter"].items(), key=lambda item: int(item[0])):
            path = f"references/internal/chapter-practice/structured/chapter_{int(chapter):02d}.json"
            lines.append(f"| {chapter} | {CHAPTER_TITLES.get(int(chapter), '')} | {count} | `{path}` |")
        index_file = OUTPUT_DIR / "index.md"
        index_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(index_file)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Import internal chapter practice markdown as candidate questions.")
    parser.add_argument("--source", default=str(SOURCE_FILE))
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()

    source = Path(args.source)
    text = source.read_text(encoding="utf-8")
    questions = parse_candidate_questions(normalize_text(text))
    audit = audit_candidates(questions)
    written = write_outputs(questions, source, write=not args.no_write)

    if args.format == "json":
        print(json.dumps({"audit": audit, "written": [str(path.relative_to(ROOT)) for path in written]}, ensure_ascii=False, indent=2))
    else:
        print("# 章节习题候选题源导入")
        print(f"- 候选题数：{audit['total']}")
        print(f"- 章节数：{len(audit['by_chapter'])}")
        print(f"- 答案分布：{audit['answer_distribution']}")
        print(f"- 质量问题：{audit['issue_counts'] or '暂无'}")
        if written:
            print("## Written")
            for path in written[:8]:
                print(f"- {path.relative_to(ROOT)}")
            if len(written) > 8:
                print(f"- ... {len(written) - 8} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
