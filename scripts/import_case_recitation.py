#!/usr/bin/env python
"""Parse internal case-recitation materials into a candidate subjective bank."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / "references" / "internal" / "case-special"
ANSWER_FILE = CASE_DIR / "有答案版-系规案例背诵.md"
NO_ANSWER_FILE = CASE_DIR / "无答案版-系规案例背诵.md"
OUTPUT_DIR = CASE_DIR / "structured"

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


def clean_line(line: str) -> str:
    value = line.strip()
    value = re.sub(r"\s+", " ", value)
    return value


def is_noise(line: str) -> bool:
    return (
        not line
        or line.startswith("#")
        or line.startswith(">")
        or line == "---"
        or re.match(r"^## 第 \d+ 页$", line) is not None
        or "软考系规" in line
        or "淘宝店铺" in line
        or "公益" in line
        or "郑房新" in line
        or re.fullmatch(r"\d+", line) is not None
    )


def chapter_from_heading(line: str) -> int | None:
    match = re.search(r"第\s*(\d{1,2})\s*章", line)
    if match:
        value = int(match.group(1))
        if 1 <= value <= 24:
            return value
    return None


def parse_answer_file(path: Path) -> list[dict[str, Any]]:
    lines = [clean_line(line) for line in path.read_text(encoding="utf-8", errors="ignore").splitlines()]
    items: list[dict[str, Any]] = []
    chapter: int | None = None
    chapter_started = False
    current: dict[str, Any] | None = None

    def flush() -> None:
        nonlocal current
        if not current:
            return
        current["question"] = re.sub(r"\s+", " ", current.get("question", "")).strip()
        current["answer"] = "\n".join(current.get("answer_lines", [])).strip()
        current.pop("answer_lines", None)
        if current["question"] and current["answer"]:
            items.append(current)
        current = None

    for raw in lines:
        line = clean_line(raw)
        if is_noise(line):
            continue
        chapter_no = chapter_from_heading(line)
        if chapter_no and "【问题" not in line:
            flush()
            chapter = chapter_no
            chapter_started = False
            continue

        question_match = re.match(r"^【问题\s*(\d+)\s*】(.+)?", line)
        if question_match and chapter:
            question_no = int(question_match.group(1))
            if question_no == 1:
                chapter_started = True
            elif not chapter_started:
                continue
            flush()
            current = {
                "id": f"internal_case_recite_ch{chapter:02d}_{question_no:03d}",
                "chapter": f"第{chapter}章",
                "chapter_no": chapter,
                "chapter_title": CHAPTER_TITLES.get(chapter, ""),
                "question_no": question_no,
                "question": (question_match.group(2) or "").strip(),
                "answer_lines": [],
                "source": "有答案版-系规案例背诵",
                "source_ref": f"references/internal/case-special/有答案版-系规案例背诵.md#第{chapter}章",
                "status": "candidate",
                "training_type": "case_recitation",
                "case_focus": chapter >= 4,
            }
            continue

        if current is None:
            continue

        if not current["answer_lines"] and not re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩(（]|\d+[.、]", line):
            current["question"] = f"{current['question']} {line}".strip()
        else:
            current["answer_lines"].append(line)

    flush()
    return items


def audit_items(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_chapter = Counter(int(item["chapter_no"]) for item in items)
    issue_counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = defaultdict(list)
    seen = set()
    for item in items:
        qid = item["id"]
        if len(item.get("question", "")) < 6:
            issue_counts["short_question"] += 1
            samples["short_question"].append(qid)
        if len(item.get("answer", "")) < 10:
            issue_counts["short_answer"] += 1
            samples["short_answer"].append(qid)
        key = re.sub(r"\s+", "", item.get("question", ""))
        if key in seen:
            issue_counts["duplicate_question_text"] += 1
            samples["duplicate_question_text"].append(qid)
        seen.add(key)
    return {
        "total": len(items),
        "by_chapter": dict(sorted(by_chapter.items())),
        "issue_counts": dict(sorted(issue_counts.items())),
        "issue_samples": {key: value[:10] for key, value in samples.items()},
    }


def write_outputs(items: list[dict[str, Any]]) -> list[Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    all_file = OUTPUT_DIR / "recitation_items.json"
    all_file.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    written.append(all_file)

    by_chapter: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        by_chapter[int(item["chapter_no"])].append(item)
    for chapter, rows in sorted(by_chapter.items()):
        path = OUTPUT_DIR / f"chapter_{chapter:02d}.json"
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(path)

    audit = audit_items(items)
    report_file = OUTPUT_DIR / "quality_report.json"
    report_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    written.append(report_file)

    lines = [
        "# 案例背诵候选题源",
        "",
        f"> 来源：`{ANSWER_FILE.relative_to(ROOT)}` / `{NO_ANSWER_FILE.relative_to(ROOT)}`",
        "> 说明：用于案例默写、主观题采分点背诵和二次补答训练；不直接覆盖正式 case_studies.json。",
        "",
        f"- 候选题数：{audit['total']}",
        f"- 质量问题：{audit['issue_counts'] or '暂无'}",
        "",
        "| 章 | 章节 | 候选题数 | 文件 |",
        "|---:|---|---:|---|",
    ]
    for chapter, count in sorted(audit["by_chapter"].items(), key=lambda pair: int(pair[0])):
        path = f"references/internal/case-special/structured/chapter_{int(chapter):02d}.json"
        lines.append(f"| {chapter} | {CHAPTER_TITLES.get(int(chapter), '')} | {count} | `{path}` |")
    index_file = OUTPUT_DIR / "index.md"
    index_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    written.append(index_file)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Import internal case recitation materials.")
    parser.add_argument("--source", default=str(ANSWER_FILE))
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()

    source = Path(args.source)
    items = parse_answer_file(source)
    written = write_outputs(items)
    audit = audit_items(items)
    if args.format == "json":
        print(json.dumps({"audit": audit, "written": [str(path.relative_to(ROOT)) for path in written]}, ensure_ascii=False, indent=2))
    else:
        print("# 案例背诵候选题源导入")
        print(f"- 候选题数：{audit['total']}")
        print(f"- 章节数：{len(audit['by_chapter'])}")
        print(f"- 质量问题：{audit['issue_counts'] or '暂无'}")
        print("## Written")
        for path in written[:8]:
            print(f"- {path.relative_to(ROOT)}")
        if len(written) > 8:
            print(f"- ... {len(written) - 8} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
