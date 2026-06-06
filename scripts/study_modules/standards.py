from __future__ import annotations

import argparse
import json
import re
from typing import Any

from study_modules.common import display_command, normalize_lookup_text, session_file_value, session_next_step, should_write_session
from study_modules.settings import BACKUP_PDFS_DIR, STANDARDS_TRAINING_FILE
from study_utils import ROOT, choose_questions, load_json, make_session, public_question, render_questions_markdown


def normalize_search_text(value: str | None) -> str:
    return normalize_lookup_text(value)

def load_standards_training() -> dict[str, Any]:
    return load_json(
        STANDARDS_TRAINING_FILE,
        {
            "stats": {},
            "documents": [],
            "clauses": [],
            "questions": [],
            "skipped_documents": [],
        },
    )


def load_standard_documents() -> list[dict[str, Any]]:
    rows = load_standards_training().get("documents", [])
    return rows if isinstance(rows, list) else []


def load_standard_clauses() -> list[dict[str, Any]]:
    rows = load_standards_training().get("clauses", [])
    return rows if isinstance(rows, list) else []


def load_standard_questions() -> list[dict[str, Any]]:
    rows = load_standards_training().get("questions", [])
    return rows if isinstance(rows, list) else []


def standards_question_lookup() -> dict[str, dict[str, Any]]:
    return {str(question.get("id")): question for question in load_standard_questions() if question.get("id")}

def match_document_text(row: dict[str, Any], keyword: str | None) -> bool:
    if not keyword:
        return True
    needle = normalize_search_text(keyword)
    if not needle:
        return True
    values = [
        row.get("title"),
        row.get("id"),
        row.get("document_id"),
        row.get("section"),
        row.get("source_ref"),
    ]
    values.extend(row.get("tags") or [])
    return any(needle in normalize_search_text(str(value)) for value in values if value)


def standard_doc_by_id() -> dict[str, dict[str, Any]]:
    return {str(doc.get("id")): doc for doc in load_standard_documents() if doc.get("id")}


def filter_standard_rows(rows: list[dict[str, Any]], document: str | None = None, tag: str | None = None) -> list[dict[str, Any]]:
    result = [row for row in rows if match_document_text(row, document)]
    if tag:
        result = [row for row in result if any(tag in str(item) for item in row.get("tags", []))]
    return result

def public_standard_question(question: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    result = public_question(question, include_answer=include_answer)
    for key in ("document_id", "clause_id", "source_pdf"):
        if key in question:
            result[key] = question[key]
    return result


def build_standards_list_payload(args: argparse.Namespace) -> dict[str, Any]:
    data = load_standards_training()
    documents = filter_standard_rows(load_standard_documents(), getattr(args, "document", None), getattr(args, "tag", None))
    skipped = data.get("skipped_documents", [])
    limit = max(1, int(getattr(args, "limit", 20) or 20))
    return {
        "title": "标准规范结构化训练库",
        "source": str(STANDARDS_TRAINING_FILE.relative_to(ROOT)),
        "summary_file": str((BACKUP_PDFS_DIR / "standards" / "structured-summary.md").relative_to(ROOT)),
        "stats": data.get("stats", {}),
        "documents": documents[:limit],
        "matched_count": len(documents),
        "skipped_documents": skipped,
    }


def render_standards_list_markdown(payload: dict[str, Any]) -> str:
    stats = payload.get("stats") or {}
    lines = [
        "# 标准规范结构化训练库",
        "",
        f"- 资产：`{payload['source']}`",
        f"- 摘要：`{payload['summary_file']}`",
        f"- 已结构化文档：{stats.get('structured_documents', 0)}/{stats.get('source_documents', 0)}",
        f"- 条款：{stats.get('clauses', 0)}，训练题：{stats.get('questions', 0)}",
        f"- 匹配文档：{payload['matched_count']}",
        "",
        "## 可训练文档",
    ]
    if not payload.get("documents"):
        lines.append("- 暂无匹配文档。")
    for doc in payload.get("documents") or []:
        lines.append(f"- [{doc.get('id')}] {doc.get('title')}：{doc.get('clause_count', 0)} 条款，类型 {doc.get('document_type')}")
        lines.append(f"  `{doc.get('source_ref')}`")
    skipped = payload.get("skipped_documents") or []
    if skipped:
        lines.extend(["", "## 待 OCR / 未结构化"])
        for item in skipped[:10]:
            lines.append(f"- {item.get('title')}：{item.get('reason')}，文本 {item.get('text_chars', 0)} 字")
    lines.extend(
        [
            "",
            "Next: python scripts/study.py standards start --document 网络安全法 --count 5 --format markdown",
        ]
    )
    return "\n".join(lines) + "\n"


def command_standards_list(args: argparse.Namespace) -> int:
    payload = build_standards_list_payload(args)
    if args.format == "markdown":
        print(render_standards_list_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_standards_clauses_payload(args: argparse.Namespace) -> dict[str, Any]:
    clauses = filter_standard_rows(load_standard_clauses(), getattr(args, "document", None), getattr(args, "tag", None))
    if getattr(args, "keyword", None):
        keyword = str(args.keyword)
        clauses = [
            clause for clause in clauses
            if keyword in str(clause.get("title") or "") or keyword in str(clause.get("text") or "") or keyword in str(clause.get("summary") or "")
        ]
    docs = standard_doc_by_id()
    limit = max(1, int(getattr(args, "limit", 10) or 10))
    rows = []
    for clause in clauses[:limit]:
        doc = docs.get(str(clause.get("document_id")), {})
        rows.append({**clause, "document_title": doc.get("title")})
    return {
        "title": "标准规范条款检索",
        "source": str(STANDARDS_TRAINING_FILE.relative_to(ROOT)),
        "document": getattr(args, "document", None),
        "keyword": getattr(args, "keyword", None),
        "matched_count": len(clauses),
        "clauses": rows,
    }


def render_standards_clauses_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 标准规范条款检索",
        "",
        f"- 来源：`{payload['source']}`",
        f"- 文档筛选：{payload.get('document') or '全部'}",
        f"- 关键词：{payload.get('keyword') or '-'}",
        f"- 匹配条款：{payload['matched_count']}",
        "",
    ]
    if not payload.get("clauses"):
        lines.append("暂无匹配条款。")
        return "\n".join(lines) + "\n"
    for index, clause in enumerate(payload["clauses"], start=1):
        summary = re.sub(r"\s+", " ", str(clause.get("summary") or clause.get("text") or "")).strip()
        summary = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", summary)
        summary = re.sub(r"(?<=[，、；：。])\s+(?=[\u4e00-\u9fff])", "", summary)
        clause_no = str(clause.get("clause_no") or "")
        clause_title = str(clause.get("title") or "")
        title_part = clause_title if clause_title and clause_title != clause_no else ""
        lines.append(f"{index}. [{clause.get('id')}] {clause.get('document_title')} {clause_no} {title_part}".rstrip())
        lines.append(f"   {summary[:220]}")
        lines.append(f"   Source: {clause.get('source_ref')}")
    return "\n".join(lines).rstrip() + "\n"


def command_standards_clauses(args: argparse.Namespace) -> int:
    payload = build_standards_clauses_payload(args)
    if args.format == "markdown":
        print(render_standards_clauses_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_standards_start_payload(args: argparse.Namespace, write: bool = True) -> dict[str, Any]:
    questions = filter_standard_rows(load_standard_questions(), getattr(args, "document", None), getattr(args, "tag", None))
    if getattr(args, "keyword", None):
        keyword = str(args.keyword)
        questions = [
            question for question in questions
            if keyword in str(question.get("question") or "")
            or keyword in str(question.get("knowledge_point") or "")
            or keyword in str(question.get("explanation") or "")
            or any(keyword in str(tag) for tag in question.get("tags", []))
        ]
    available = len(questions)
    selected = choose_questions(questions, int(args.count), seed=getattr(args, "seed", None))
    session = make_session(
        "standards_training",
        [question["id"] for question in selected],
        {
            "document": getattr(args, "document", None),
            "keyword": getattr(args, "keyword", None),
            "tag": getattr(args, "tag", None),
            "count": int(args.count),
            "seed": getattr(args, "seed", None),
            "source": str(STANDARDS_TRAINING_FILE.relative_to(ROOT)),
        },
    )
    write = write and should_write_session(args)
    next_step = f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown"
    return {
        "title": "标准规范专项训练",
        "session": session,
        "session_file": session_file_value(session, write),
        "document": getattr(args, "document", None),
        "keyword": getattr(args, "keyword", None),
        "tag": getattr(args, "tag", None),
        "available": available,
        "questions": [public_standard_question(question) for question in selected],
        "next_step": session_next_step(next_step, write),
        "note": "本训练题由标准规范/法律法规条款结构化生成，不是历年真题。",
    }


def render_standards_start_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 标准规范专项训练",
        "",
        f"- Session: {payload['session']['id']}",
        f"- File: {payload['session_file']}",
        f"- 筛选：{payload.get('document') or '全部文档'} {payload.get('keyword') or ''}".rstrip(),
        f"- 可用题数：{payload['available']}",
        f"- 说明：{payload['note']}",
        "",
    ]
    if payload.get("questions"):
        lines.append(render_questions_markdown(payload["questions"]).rstrip())
        lines.append("")
        lines.append(f"Next: {display_command(payload['next_step'])}")
    else:
        lines.append("没有匹配到可训练的标准规范题。")
        lines.append("Next: python scripts/study.py standards list --format markdown")
    return "\n".join(lines) + "\n"


def command_standards_start(args: argparse.Namespace) -> int:
    payload = build_standards_start_payload(args)
    if args.format == "markdown":
        print(render_standards_start_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
