#!/usr/bin/env python
"""Build a structured standards/laws training bank from extracted backup PDFs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE = ROOT / "references" / "backup-pdfs" / "manifest.json"
OUTPUT_FILE = ROOT / "assets" / "questions" / "standards_training.json"
SUMMARY_FILE = ROOT / "references" / "backup-pdfs" / "standards" / "structured-summary.md"

MIN_TEXT_CHARS = 1200
MAX_QUESTIONS_PER_DOC = 12
QUESTION_TARGETS_BY_TYPE = {
    "law": 12,
    "standard": 10,
    "service_spec": 10,
    "construction_spec": 10,
    "management_norm": 8,
}

ARTICLE_RE = re.compile(r"(?m)^\s*(第[一二三四五六七八九十百零〇]+条)[ \t　]*")
CHAPTER_RE = re.compile(r"(?m)^\s*(第[一二三四五六七八九十百零〇]+章)\s+(.+?)\s*$")
NUMERIC_HEADING_RE = re.compile(r"(?m)^\s*(\d+(?:\.\d+){0,3})\s+([^\n.。]{2,60}?)\s*$")
TOC_DOTS_RE = re.compile(r"\.{3,}|…{2,}|_{3,}")
PAGE_ONLY_RE = re.compile(r"^\s*\d{1,3}\s*$")

NOISE_PATTERNS = (
    r"^>.*$",
    r"^本标准由.*$",
    r"^.*www\..*$",
    r"^.*仅供学习参考.*$",
    r"^.*免费.*分享.*$",
    r"^.*整理不易.*$",
    r"^.*全国人民代表大会常务委员会公报.*$",
    r"^—\s*[０-９\d\s]+\s*—$",
    r"^中华人民共和国国家标准.*$",
    r"^ICS\s+.*$",
)

IMPORTANT_TERMS = (
    "网络安全",
    "关键信息基础设施",
    "个人信息",
    "等级保护",
    "应急",
    "监测",
    "服务管理",
    "服务级别",
    "服务请求",
    "事件",
    "问题",
    "变更",
    "配置",
    "发布",
    "供应商",
    "信息安全",
    "保密",
    "密码",
    "采购",
    "评审",
    "施工",
    "验收",
    "机房",
    "桌面",
    "外围设备",
)


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def clean_line(line: str) -> str:
    line = line.replace("\u3000", " ")
    line = re.sub(r"[ \t]+", " ", line).strip()
    line = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", line)
    return line


def clean_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    lines: list[str] = []
    for raw in text.splitlines():
        line = clean_line(raw)
        if not line:
            lines.append("")
            continue
        if PAGE_ONLY_RE.fullmatch(line):
            continue
        if any(re.fullmatch(pattern, line, flags=re.IGNORECASE) for pattern in NOISE_PATTERNS):
            continue
        lines.append(line)
    value = "\n".join(lines)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def read_markdown(item: dict[str, Any]) -> str:
    markdown = item.get("markdown")
    if not markdown:
        return ""
    path = ROOT / str(markdown)
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"^# .+?\n", "", text, count=1)
    return clean_text(text)


def rel_markdown(item: dict[str, Any]) -> str | None:
    markdown = item.get("markdown")
    return str(markdown).replace("\\", "/") if markdown else None


def slug(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    ascii_part = re.sub(r"[^a-z0-9]+", "_", value.lower())
    ascii_part = ascii_part.strip("_")[:30]
    return f"{ascii_part}_{digest}" if ascii_part else digest


def document_type(title: str) -> str:
    if "法" in title and title.startswith("中华人民共和国"):
        return "law"
    if "信用管理规范" in title:
        return "management_norm"
    if "桌面" in title or "外围设备" in title:
        return "service_spec"
    if "机房施工" in title or "验收规范" in title:
        return "construction_spec"
    return "standard"


def infer_tags(title: str, dtype: str, text: str = "") -> list[str]:
    tags = ["标准规范"]
    if dtype == "law":
        tags.append("法律法规")
    elif dtype == "standard":
        tags.append("国家/国际标准")
    elif dtype == "service_spec":
        tags.append("IT服务规范")
    elif dtype == "construction_spec":
        tags.append("机房工程")
    elif dtype == "management_norm":
        tags.append("管理规范")
    haystack = f"{title} {text}"
    for term in IMPORTANT_TERMS:
        if term in haystack and term not in tags:
            tags.append(term)
        if len(tags) >= 5:
            break
    return tags[:5]


def sentence_candidates(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    pieces = re.split(r"(?<=[。；;])", compact)
    rows: list[str] = []
    for piece in pieces:
        value = piece.strip(" ；;。")
        if len(value) < 18:
            continue
        if len(value) > 140:
            value = value[:140].rstrip("，、；;。")
        if value and value not in rows:
            rows.append(value)
    return rows


def first_good_sentence(text: str) -> str:
    for sentence in sentence_candidates(text):
        sentence = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", sentence)
        sentence = re.sub(r"(?<=[，、；：。])\s+(?=[\u4e00-\u9fff])", "", sentence)
        if any(term in sentence for term in IMPORTANT_TERMS) or len(sentence) >= 28:
            return sentence
    compact = re.sub(r"\s+", " ", text).strip()
    compact = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", compact)
    compact = re.sub(r"(?<=[，、；：。])\s+(?=[\u4e00-\u9fff])", "", compact)
    return compact[:120].rstrip("，、；;。")


def chapter_at(text: str, position: int) -> str | None:
    chapter = None
    for match in CHAPTER_RE.finditer(text[:position]):
        chapter = f"{match.group(1)} {match.group(2)}"
    return chapter


def split_law_clauses(item: dict[str, Any], doc_id: str, text: str) -> list[dict[str, Any]]:
    matches = list(ARTICLE_RE.finditer(text))
    clauses: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = clean_text(text[start:end])
        if len(body) < 25:
            continue
        clause_no = match.group(1)
        chapter = chapter_at(text, match.start())
        clauses.append(
            {
                "id": f"std_clause_{doc_id}_{len(clauses) + 1:03d}",
                "document_id": doc_id,
                "title": clause_no,
                "chapter": chapter,
                "clause_no": clause_no,
                "text": body,
                "summary": first_good_sentence(body),
                "source_ref": rel_markdown(item),
                "source_pdf": item.get("path"),
                "tags": infer_tags(str(item.get("title") or ""), "law", body),
            }
        )
    return clauses


def numeric_heading_matches(text: str) -> list[re.Match[str]]:
    matches = []
    for match in NUMERIC_HEADING_RE.finditer(text):
        number = match.group(1)
        heading = clean_line(match.group(2))
        line = clean_line(match.group(0))
        if TOC_DOTS_RE.search(line):
            continue
        if number.endswith(".0") or re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", heading):
            continue
        if heading in {"范围", "总则", "术语和定义", "规范性引用文件"} and match.start() < 1000:
            # Keep the real body heading if it appears later; early ones are often TOC rows.
            continue
        if len(heading) < 2:
            continue
        matches.append(match)
    return matches


def split_numeric_clauses(item: dict[str, Any], doc_id: str, dtype: str, text: str) -> list[dict[str, Any]]:
    matches = numeric_heading_matches(text)
    clauses: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, match in enumerate(matches):
        number = match.group(1)
        heading = clean_line(match.group(2))
        key = (number, heading)
        if key in seen:
            continue
        seen.add(key)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = clean_text(text[start:end])
        if len(body) < 35:
            continue
        if len(body) > 1600:
            body = body[:1600].rstrip()
        chapter = number.split(".", 1)[0]
        clauses.append(
            {
                "id": f"std_clause_{doc_id}_{len(clauses) + 1:03d}",
                "document_id": doc_id,
                "title": heading,
                "chapter": chapter,
                "clause_no": number,
                "text": body,
                "summary": first_good_sentence(body),
                "source_ref": rel_markdown(item),
                "source_pdf": item.get("path"),
                "tags": infer_tags(str(item.get("title") or ""), dtype, f"{heading} {body}"),
            }
        )
    return clauses


def split_clauses(item: dict[str, Any], doc_id: str, dtype: str, text: str) -> list[dict[str, Any]]:
    if dtype == "law":
        clauses = split_law_clauses(item, doc_id, text)
        if clauses:
            return clauses
    return split_numeric_clauses(item, doc_id, dtype, text)


def clause_priority(clause: dict[str, Any]) -> tuple[int, int]:
    text = f"{clause.get('title', '')} {clause.get('text', '')}"
    score = sum(3 for term in IMPORTANT_TERMS if term in text)
    if re.fullmatch(r"\d+(?:\.\d+){2,3}", str(clause.get("clause_no") or "")):
        score += 1
    if "定义" in str(clause.get("title") or "") or "要求" in text:
        score += 2
    return score, min(len(str(clause.get("text") or "")), 600)


def option_text(sentence: str, limit: int = 86) -> str:
    value = re.sub(r"\s+", " ", sentence).strip(" 。；;")
    value = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", value)
    value = re.sub(r"(?<=[，、；：。])\s+(?=[\u4e00-\u9fff])", "", value)
    if len(value) > limit:
        value = value[:limit].rstrip("，、；;。") + "..."
    return value


def make_question(
    doc: dict[str, Any],
    clause: dict[str, Any],
    distractor_pool: list[dict[str, Any]],
    index: int,
) -> dict[str, Any] | None:
    correct = option_text(str(clause.get("summary") or ""))
    if len(correct) < 12:
        return None
    distractors: list[str] = []
    for other in distractor_pool:
        if other.get("id") == clause.get("id"):
            continue
        candidate = option_text(str(other.get("summary") or ""))
        if len(candidate) < 12 or candidate == correct or candidate in distractors:
            continue
        distractors.append(candidate)
        if len(distractors) >= 3:
            break
    if len(distractors) < 3:
        return None
    variants = [correct, *distractors[:3]]
    rotation = index % 4
    ordered = variants[rotation:] + variants[:rotation]
    answer = "ABCD"[ordered.index(correct)]
    title = str(doc.get("title") or "")
    clause_title = str(clause.get("title") or clause.get("clause_no") or "")
    question_text = f"根据《{title}》，关于“{clause_title}”，哪一项最符合对应条款原文？"
    return {
        "id": f"std_q{index:04d}",
        "question": question_text,
        "options": [f"{letter}. {text}" for letter, text in zip("ABCD", ordered, strict=True)],
        "answer": answer,
        "explanation": f"依据《{title}》{clause.get('clause_no') or ''}：{correct}",
        "chapter": "第24章",
        "source": "standards_training",
        "question_type": "single_choice",
        "difficulty": "medium",
        "section": title,
        "knowledge_point": clause_title[:60] or title,
        "source_ref": clause.get("source_ref"),
        "source_pdf": clause.get("source_pdf"),
        "document_id": doc.get("id"),
        "clause_id": clause.get("id"),
        "tags": list(dict.fromkeys([*(clause.get("tags") or []), "标准规范专项训练"]))[:5],
    }


def build_questions(documents: list[dict[str, Any]], clauses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for clause in clauses:
        by_doc[str(clause.get("document_id"))].append(clause)
    all_ranked = sorted(clauses, key=clause_priority, reverse=True)
    questions: list[dict[str, Any]] = []
    for doc in documents:
        doc_id = str(doc.get("id"))
        doc_clauses = sorted(by_doc.get(doc_id, []), key=clause_priority, reverse=True)
        limit = min(MAX_QUESTIONS_PER_DOC, QUESTION_TARGETS_BY_TYPE.get(str(doc.get("document_type")), 8))
        selected = doc_clauses[:limit]
        pool = doc_clauses[limit:] + [clause for clause in all_ranked if clause.get("document_id") != doc_id]
        for clause in selected:
            question = make_question(doc, clause, pool, len(questions) + 1)
            if question:
                questions.append(question)
    return questions


def build_payload() -> dict[str, Any]:
    manifest = load_manifest()
    source_items = [item for item in manifest.get("files", []) if item.get("category") == "standards"]
    documents: list[dict[str, Any]] = []
    clauses: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for item in source_items:
        title = str(item.get("title") or "")
        markdown = rel_markdown(item)
        text = read_markdown(item)
        text_chars = len(re.sub(r"\s+", "", text))
        if not markdown or item.get("needs_ocr") or text_chars < MIN_TEXT_CHARS:
            skipped.append(
                {
                    "title": title,
                    "reason": "needs_ocr_or_low_text",
                    "markdown": markdown,
                    "text_chars": text_chars,
                    "source_pdf": item.get("path"),
                }
            )
            continue
        dtype = document_type(title)
        doc_id = f"std_doc_{slug(title)}"
        doc = {
            "id": doc_id,
            "title": title,
            "document_type": dtype,
            "source_ref": markdown,
            "source_pdf": item.get("path"),
            "year": item.get("year"),
            "pages": item.get("pages"),
            "text_chars": text_chars,
            "needs_ocr": bool(item.get("needs_ocr")),
            "tags": infer_tags(title, dtype),
        }
        doc_clauses = split_clauses(item, doc_id, dtype, text)
        doc["clause_count"] = len(doc_clauses)
        documents.append(doc)
        clauses.extend(doc_clauses)

    questions = build_questions(documents, clauses)
    stats = {
        "source_documents": len(source_items),
        "structured_documents": len(documents),
        "skipped_documents": len(skipped),
        "clauses": len(clauses),
        "questions": len(questions),
        "document_types": dict(Counter(doc.get("document_type") for doc in documents)),
        "questions_by_document": dict(Counter(question.get("document_id") for question in questions)),
        "skipped_by_reason": dict(Counter(item.get("reason") for item in skipped)),
    }
    return {
        "schema_version": 1,
        "source": str(MANIFEST_FILE.relative_to(ROOT)).replace("\\", "/"),
        "generated_from": "references/backup-pdfs/standards",
        "stats": stats,
        "documents": documents,
        "clauses": clauses,
        "questions": questions,
        "skipped_documents": skipped,
        "notes": [
            "本训练库由已抽取文本的标准规范/法律法规自动结构化生成，用于标准规范专项训练。",
            "生成题不是历年真题；答案依据 source_ref 对应原文条款。",
            "needs_ocr 或文本过少的扫描件暂不生成训练题，需 OCR 后再重新导入。",
        ],
    }


def render_summary(payload: dict[str, Any]) -> str:
    stats = payload["stats"]
    lines = [
        "# 标准规范结构化训练摘要",
        "",
        f"- 来源：`{payload['source']}`",
        f"- 已结构化文档：{stats['structured_documents']}/{stats['source_documents']}",
        f"- 条款数：{stats['clauses']}",
        f"- 训练题：{stats['questions']}",
        f"- 跳过文档：{stats['skipped_documents']}（多为需 OCR 或文本过少）",
        "",
        "## 已结构化文档",
        "",
    ]
    for doc in payload["documents"]:
        question_count = stats["questions_by_document"].get(doc["id"], 0)
        lines.append(f"- {doc['title']}：{doc['clause_count']} 条款，{question_count} 题，`{doc['source_ref']}`")
    lines.extend(["", "## 待 OCR / 未结构化文档", ""])
    if payload["skipped_documents"]:
        for item in payload["skipped_documents"]:
            lines.append(f"- {item['title']}：{item['reason']}，文本 {item['text_chars']} 字")
    else:
        lines.append("- 暂无。")
    lines.extend(
        [
            "",
            "## 使用方式",
            "",
            "```bash",
            "python scripts/study.py standards list --format markdown",
            "python scripts/study.py standards clauses --document 网络安全法 --limit 10 --format markdown",
            "python scripts/study.py standards start --document ISO20000 --count 5 --format markdown",
            "python scripts/study.py ask \"给我出5道网络安全法标准规范题\" --format markdown",
            "```",
            "",
            "> 注意：标准规范训练题是专项训练题，不是历年真题。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build structured standards training assets.")
    parser.add_argument("--write", action="store_true", help="Write JSON asset and Markdown summary.")
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    payload = build_payload()
    if args.write:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_FILE.write_text(render_summary(payload), encoding="utf-8")

    if args.format == "markdown":
        print(render_summary(payload))
    else:
        print(json.dumps(payload["stats"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
