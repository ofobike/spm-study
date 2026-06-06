#!/usr/bin/env python
"""Build a lightweight local retrieval index for all spm-study materials."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from study_utils import ROOT, load_json, save_json


OUTPUT_FILE = ROOT / "assets" / "search" / "index.json"
MAX_CHUNK_CHARS = 1400
MIN_CHUNK_CHARS = 80


SOURCE_RULES: list[tuple[str, str]] = [
    ("references/internal/sprint-materials/", "sprint_material"),
    ("references/internal/vip-materials/", "vip_material"),
    ("references/internal/three-color-notes/", "three_color_notes"),
    ("references/internal/mindmaps/", "mindmap"),
    ("references/internal/guide/", "exam_guide"),
    ("references/internal/syllabus/", "syllabus"),
    ("references/internal/paper-special/", "paper_special"),
    ("references/internal/chapter-practice/", "chapter_practice"),
    ("references/internal/case-special/", "case_special"),
    ("references/pdf-skill-parsed/past-exams-", "past_exam_pdf_enhanced"),
    ("references/pdf-skill-parsed/mock-bank-", "mock_bank_enhanced"),
    ("references/backup-pdfs/past-exams/", "past_exam_pdf"),
    ("references/backup-pdfs/standards/", "standards_pdf"),
    ("references/backup-pdfs/mock-bank/", "mock_bank"),
    ("references/zfx/", "zfx_material"),
    ("references/", "chapter_reference"),
    ("assets/questions/chapters/", "chapter_question"),
    ("assets/questions/case_studies.json", "case_study"),
    ("assets/questions/past_exams.json", "past_exam"),
    ("assets/questions/standards_training.json", "standards_training"),
    ("assets/questions/sprint_training.json", "sprint_training"),
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def source_type_for(path_text: str) -> str:
    normalized = path_text.replace("\\", "/")
    for prefix, source_type in SOURCE_RULES:
        if normalized.startswith(prefix):
            return source_type
    return "other"


def clean_text(text: str) -> str:
    value = text.replace("\u3000", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def title_from_path(path: Path) -> str:
    title = path.stem
    match = re.search(r"第(\d+)章[_-](.+)", title)
    if match:
        return f"第{int(match.group(1))}章 {match.group(2)}"
    return title


def chunk_id(path_text: str, title: str, index: int) -> str:
    digest = hashlib.sha1(f"{path_text}|{title}|{index}".encode("utf-8")).hexdigest()[:12]
    return f"chunk_{digest}"


def chapter_from_text(*values: str | None) -> int | None:
    for value in values:
        match = re.search(r"(?:第|chapter_)(\d{1,2})", str(value or ""), re.IGNORECASE)
        if match:
            chapter = int(match.group(1))
            if 1 <= chapter <= 24:
                return chapter
    return None


def emit_chunk(
    entries: list[dict[str, Any]],
    *,
    path: Path,
    title: str,
    heading: str | None,
    text: str,
    index: int,
    source_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    body = clean_text(text)
    if len(re.sub(r"\s+", "", body)) < MIN_CHUNK_CHARS:
        return
    path_text = rel(path)
    entries.append(
        {
            "id": chunk_id(path_text, heading or title, index),
            "title": title,
            "heading": heading,
            "path": path_text,
            "source_type": source_type or source_type_for(path_text),
            "chapter": chapter_from_text(title, heading, path_text),
            "text": body[:MAX_CHUNK_CHARS],
            "char_count": len(body),
            "metadata": metadata or {},
        }
    )


def split_long_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in paragraphs:
        p_len = len(paragraph)
        if current and current_len + p_len > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        if p_len > max_chars:
            for start in range(0, p_len, max_chars):
                chunks.append(paragraph[start : start + max_chars])
            continue
        current.append(paragraph)
        current_len += p_len
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def iter_markdown_entries(path: Path) -> Iterable[dict[str, Any]]:
    title = title_from_path(path)
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    heading = title
    buffer: list[str] = []
    chunk_index = 0
    entries: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal chunk_index, buffer
        body = "\n".join(buffer).strip()
        buffer = []
        for piece in split_long_text(body):
            chunk_index += 1
            emit_chunk(entries, path=path, title=title, heading=heading, text=piece, index=chunk_index)

    for line in lines:
        if line.startswith("#"):
            flush()
            heading = line.strip("# ").strip() or title
            continue
        if line.strip() == "---":
            flush()
            continue
        buffer.append(line)
    flush()
    return entries


def question_text(question: dict[str, Any]) -> str:
    parts = [str(question.get("question") or "")]
    parts.extend(str(option) for option in question.get("options", []) if option)
    for key in ("answer", "explanation", "knowledge_point", "section", "source_ref"):
        if question.get(key):
            parts.append(str(question[key]))
    return "\n".join(parts)


def iter_chapter_question_entries(path: Path) -> Iterable[dict[str, Any]]:
    questions = load_json(path, [])
    entries: list[dict[str, Any]] = []
    if not isinstance(questions, list):
        return entries
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            continue
        qid = str(question.get("id") or f"q{index}")
        title = f"{question.get('chapter') or title_from_path(path)} {qid}"
        emit_chunk(
            entries,
            path=path,
            title=title,
            heading=str(question.get("knowledge_point") or question.get("section") or qid),
            text=question_text(question),
            index=index,
            source_type="chapter_question",
            metadata={"question_id": qid, "tags": question.get("tags", [])},
        )
    return entries


def iter_case_study_entries(path: Path) -> Iterable[dict[str, Any]]:
    data = load_json(path, {})
    entries: list[dict[str, Any]] = []
    for index, case in enumerate(data.get("case_studies", []) if isinstance(data, dict) else [], start=1):
        if not isinstance(case, dict):
            continue
        parts = [str(case.get("scenario") or "")]
        for question in case.get("questions", []):
            if isinstance(question, dict):
                parts.append(question_text(question))
        emit_chunk(
            entries,
            path=path,
            title=str(case.get("title") or case.get("id") or f"案例{index}"),
            heading=str(case.get("id") or ""),
            text="\n".join(parts),
            index=index,
            source_type="case_study",
            metadata={"case_id": case.get("id"), "chapters": case.get("chapters") or [case.get("chapter")]},
        )
    return entries


def iter_past_exam_entries(path: Path) -> Iterable[dict[str, Any]]:
    data = load_json(path, {})
    entries: list[dict[str, Any]] = []
    index = 0
    for question in data.get("choice_questions", []) if isinstance(data, dict) else []:
        index += 1
        title = f"{question.get('year')} {question.get('period')} 上午真题 {question.get('number')}"
        emit_chunk(entries, path=path, title=title, heading=str(question.get("id")), text=question_text(question), index=index, source_type="past_exam", metadata={"id": question.get("id"), "subject": "choice"})
    for case in data.get("case_studies", []) if isinstance(data, dict) else []:
        index += 1
        parts = [str(case.get("scenario") or "")]
        for question in case.get("questions", []):
            if isinstance(question, dict):
                parts.append(question_text(question))
        title = f"{case.get('year')} {case.get('period')} 案例真题 {case.get('number')}"
        emit_chunk(entries, path=path, title=title, heading=str(case.get("id")), text="\n".join(parts), index=index, source_type="past_exam", metadata={"id": case.get("id"), "subject": "case"})
    for paper in data.get("paper_topics", []) if isinstance(data, dict) else []:
        index += 1
        title = f"{paper.get('year')} {paper.get('period')} 论文真题 {paper.get('title')}"
        emit_chunk(entries, path=path, title=title, heading=str(paper.get("id")), text=str(paper.get("prompt") or ""), index=index, source_type="past_exam", metadata={"id": paper.get("id"), "subject": "paper"})
    return entries


def iter_standards_entries(path: Path) -> Iterable[dict[str, Any]]:
    data = load_json(path, {})
    entries: list[dict[str, Any]] = []
    index = 0
    for clause in data.get("clauses", []) if isinstance(data, dict) else []:
        index += 1
        title = f"{clause.get('document_title')} {clause.get('clause_no') or ''}".strip()
        text = "\n".join(str(clause.get(key) or "") for key in ("title", "summary", "text", "source_ref"))
        emit_chunk(entries, path=path, title=title, heading=str(clause.get("id")), text=text, index=index, source_type="standards_training", metadata={"id": clause.get("id"), "tags": clause.get("tags", [])})
    for question in data.get("questions", []) if isinstance(data, dict) else []:
        index += 1
        emit_chunk(entries, path=path, title=f"标准规范专项题 {question.get('id')}", heading=str(question.get("knowledge_point") or ""), text=question_text(question), index=index, source_type="standards_training", metadata={"id": question.get("id"), "tags": question.get("tags", [])})
    return entries


def iter_sprint_training_entries(path: Path) -> Iterable[dict[str, Any]]:
    data = load_json(path, {})
    entries: list[dict[str, Any]] = []
    index = 0
    for key, source_type in (("cards", "sprint_training"), ("choice_questions", "sprint_training"), ("case_prompts", "sprint_training")):
        for item in data.get(key, []) if isinstance(data, dict) else []:
            index += 1
            text = "\n".join(str(item.get(field) or "") for field in ("prompt", "question", "answer", "explanation", "source_ref"))
            emit_chunk(entries, path=path, title=str(item.get("title") or item.get("id") or key), heading=str(item.get("kind") or key), text=text, index=index, source_type=source_type, metadata={"id": item.get("id"), "kind": item.get("kind")})
    return entries


def collect_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted((ROOT / "references").rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        if "pdf-skill-parsed/diagnostics" in rel(path):
            continue
        entries.extend(iter_markdown_entries(path))

    for path in sorted((ROOT / "assets" / "questions" / "chapters").glob("chapter_*.json")):
        entries.extend(iter_chapter_question_entries(path))

    special_files = [
        (ROOT / "assets" / "questions" / "case_studies.json", iter_case_study_entries),
        (ROOT / "assets" / "questions" / "past_exams.json", iter_past_exam_entries),
        (ROOT / "assets" / "questions" / "standards_training.json", iter_standards_entries),
        (ROOT / "assets" / "questions" / "sprint_training.json", iter_sprint_training_entries),
    ]
    for path, loader in special_files:
        if path.exists():
            entries.extend(loader(path))
    return entries


def build_index() -> dict[str, Any]:
    entries = collect_entries()
    source_counts = Counter(entry["source_type"] for entry in entries)
    return {
        "schema_version": 1,
        "generated_by": "scripts/build_search_index.py",
        "chunk_count": len(entries),
        "source_counts": dict(sorted(source_counts.items())),
        "entries": entries,
    }


def render_markdown(index: dict[str, Any]) -> str:
    lines = [
        "# 全资料检索索引",
        "",
        f"- 片段数：{index.get('chunk_count', 0)}",
        f"- 输出：`{OUTPUT_FILE.relative_to(ROOT)}`",
        "",
        "## 来源分布",
    ]
    for source_type, count in (index.get("source_counts") or {}).items():
        lines.append(f"- {source_type}: {count}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build local search index for spm-study references and question assets.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()
    index = build_index()
    if args.write:
        save_json(OUTPUT_FILE, index)
    if args.format == "json":
        print(json.dumps(index, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(index))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
