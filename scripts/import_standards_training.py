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
DATA_NEEDED_FILE = ROOT / "references" / "backup-pdfs" / "standards" / "pdf-data-needed.md"
PDF_SKILL_PARSED_DIR = ROOT / "references" / "pdf-skill-parsed"
ENHANCED_STANDARD_DIRS = (
    ("pdf_skill_ocr", PDF_SKILL_PARSED_DIR / "standards-ocr"),
)

MIN_TEXT_CHARS = 1200
MAX_QUESTIONS_PER_DOC = 12
QUESTION_TARGETS_BY_TYPE = {
    "law": 12,
    "standard": 10,
    "service_spec": 10,
    "construction_spec": 10,
    "management_norm": 8,
}
USER_SKIPPED_STANDARD_TITLE_FRAGMENTS = (
    "GBT 28827.1",
    "GBT 28827.2",
    "GBT 28827.3",
)

ARTICLE_RE = re.compile(r"(?m)^\s*(第[一二三四五六七八九十百零〇]+条)[ \t　]*")
CHAPTER_RE = re.compile(r"(?m)^\s*(第[一二三四五六七八九十百零〇]+章)\s*(.+?)\s*$")
NUMERIC_HEADING_RE = re.compile(r"(?m)^\s*(\d+(?:\.\d+){0,3})\s+([^\n.。]{2,60}?)\s*$")
TOC_DOTS_RE = re.compile(r"\.{3,}|…{2,}|_{3,}")
PAGE_ONLY_RE = re.compile(r"^\s*\d{1,3}\s*$")
CHINESE_NUMERAL_CHARS = "一二三四五六七八九十百零〇"

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
    r"^# OCR Output$",
    r"^- Source:.*$",
    r"^- Backend:.*$",
    r"^- Language:.*$",
    r"^- DPI:.*$",
    r"^## Page \d+$",
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

OCR_CORRECTIONS = (
    ("信恳投术", "信息技术"),
    ("信恳技术", "信息技术"),
    ("沼围", "范围"),
    ("范图", "范围"),
    ("规跋", "规定"),
    ("运行细护", "运行维护"),
    ("木用信息技术", "利用信息技术"),
    ("绕构化", "结构化"),
    ("绣司布缆", "综合布缆"),
    ("文撑", "支撑"),
    ("答见服务", "常见服务"),
    ("GB/工", "GB/T"),
    ("GB/TIT", "GB/T"),
    ("邃循", "遵循"),
    ("遨循", "遵循"),
    ("遨守", "遵守"),
    ("韶争", "竞争"),
    ("限频", "限额"),
    ("雄用", "雇用"),
    ("进人", "进入"),
    ("本欧定", "本决定"),
)


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def clean_line(line: str) -> str:
    line = line.replace("\u3000", " ")
    line = re.sub(r"[ \t]+", " ", line).strip()
    line = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", line)
    line = normalize_ocr_law_markers(line)
    return line


def normalize_ocr_law_markers(line: str) -> str:
    numeral = f"[{CHINESE_NUMERAL_CHARS}]"

    def compact_marker(match: re.Match[str]) -> str:
        middle = re.sub(r"\s+", "", match.group(1))
        return f"第{middle}{match.group(2)}"

    line = re.sub(rf"第\s*({numeral}(?:\s*{numeral})*)\s*(条|章)", compact_marker, line)
    return line


def apply_ocr_corrections(text: str) -> str:
    for wrong, right in OCR_CORRECTIONS:
        text = text.replace(wrong, right)
    text = re.sub(r"合\s*社\s*会\s*公\s*开\s*发\s*布", "向社会公开发布", text)
    text = re.sub(r"\s*[一—-]\s*\d{1,4}\s*[一—-]\s*", " ", text)
    text = re.sub(r"\s+[“\"']\s*(第[一二三四五六七八九十百零〇]+条)", r"\n\1", text)
    text = re.sub(r"(?<=[。；;])\s*(第[一二三四五六七八九十百零〇]+条)", r"\n\1", text)
    text = re.sub(r"^[“\"'`]+", "", text.strip())
    text = re.sub(r"^[_\-—]+\s*", "", text)
    text = re.sub(r"GB/\s*工", "GB/T", text)
    text = re.sub(r"《\s*国民经济行业分类\s*%", "《国民经济行业分类》", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s*\.\s*(?=[\u4e00-\u9fff])", "，", text)
    text = re.sub(r"\s+([,，。；;：:])", r"\1", text)
    return text


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
    value = apply_ocr_corrections(value)
    return value.strip()


def compact_key(value: str) -> str:
    value = value.lower()
    value = re.sub(r"\.(pdf|md)$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"【.*?】|\(.*?\)|（.*?）|\[.*?\]", "", value)
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value)
    return value


def text_quality(text: str) -> dict[str, Any]:
    compact = re.sub(r"\s+", "", text)
    cjk_chars = count_cjk(compact)
    article_count = len(ARTICLE_RE.findall(text))
    numeric_heading_count = len(numeric_heading_matches(text))
    return {
        "text_chars": len(compact),
        "cjk_chars": cjk_chars,
        "cjk_ratio": round(cjk_chars / max(1, len(compact)), 3),
        "article_markers": article_count,
        "numeric_headings": numeric_heading_count,
    }


def is_quality_usable(quality: dict[str, Any]) -> bool:
    if int(quality.get("text_chars", 0) or 0) < MIN_TEXT_CHARS:
        return False
    if int(quality.get("cjk_chars", 0) or 0) < 600:
        return False
    return int(quality.get("article_markers", 0) or 0) >= 3 or int(quality.get("numeric_headings", 0) or 0) >= 3


def count_cjk(value: str) -> int:
    return sum(1 for char in value if "\u4e00" <= char <= "\u9fff")


def enhanced_markdown_candidates(item: dict[str, Any]) -> list[dict[str, Any]]:
    title_key = compact_key(str(item.get("title") or ""))
    path_key = compact_key(Path(str(item.get("path") or "")).stem)
    candidates: list[dict[str, Any]] = []
    for source_kind, directory in ENHANCED_STANDARD_DIRS:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.stem.endswith("-sample"):
                continue
            stem_key = compact_key(path.stem)
            if not stem_key:
                continue
            if stem_key not in title_key and title_key not in stem_key and stem_key not in path_key and path_key not in stem_key:
                continue
            raw = path.read_text(encoding="utf-8", errors="ignore")
            text = clean_text(re.sub(r"^# .+?\n", "", raw, count=1))
            quality = text_quality(text)
            candidates.append(
                {
                    "path": path,
                    "source_ref": rel_path(path),
                    "source_kind": source_kind,
                    "text": text,
                    "quality": quality,
                    "usable": is_quality_usable(quality),
                }
            )
    candidates.sort(key=lambda row: (bool(row["usable"]), int(row["quality"].get("text_chars", 0) or 0)), reverse=True)
    return candidates


def rel_path(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def read_markdown_path(markdown: str | None) -> tuple[str, dict[str, Any]]:
    if not markdown:
        return "", {"text_chars": 0, "cjk_chars": 0, "cjk_ratio": 0, "article_markers": 0, "numeric_headings": 0}
    path = ROOT / str(markdown)
    if not path.exists():
        return "", {"text_chars": 0, "cjk_chars": 0, "cjk_ratio": 0, "article_markers": 0, "numeric_headings": 0}
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"^# .+?\n", "", text, count=1)
    cleaned = clean_text(text)
    return cleaned, text_quality(cleaned)


def select_markdown_source(item: dict[str, Any]) -> dict[str, Any]:
    enhanced = enhanced_markdown_candidates(item)
    if enhanced and enhanced[0]["usable"]:
        return enhanced[0]

    markdown = rel_markdown(item)
    text, quality = read_markdown_path(markdown)
    usable = is_quality_usable(quality) and not bool(item.get("needs_ocr"))
    return {
        "path": ROOT / markdown if markdown else None,
        "source_ref": markdown,
        "source_kind": "backup_pdf_text",
        "text": text,
        "quality": quality,
        "usable": usable,
        "enhanced_candidates": enhanced,
    }


def rel_markdown(item: dict[str, Any]) -> str | None:
    selected = item.get("_selected_markdown")
    if selected:
        return str(selected).replace("\\", "/")
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


def is_user_skipped_standard(title: str) -> bool:
    return any(fragment in title for fragment in USER_SKIPPED_STANDARD_TITLE_FRAGMENTS)


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
    source_kind = str(item.get("_selected_source_kind") or "")
    matches = list(ARTICLE_RE.finditer(text))
    clauses: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = clean_text(text[start:end])
        if len(body) < 12 or has_bad_ocr_noise(body, dtype="law", source_kind=source_kind):
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
    source_kind = str(item.get("_selected_source_kind") or "")
    matches = numeric_heading_matches(text)
    clauses: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, match in enumerate(matches):
        number = match.group(1)
        heading = clean_line(match.group(2))
        heading = heading.strip(" “ ”\"'`")
        if has_bad_ocr_heading(number, heading, dtype=dtype, source_kind=source_kind):
            continue
        key = (number, heading)
        if key in seen:
            continue
        seen.add(key)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = clean_text(text[start:end])
        if len(body) < 35 or has_bad_ocr_noise(body, dtype=dtype, source_kind=source_kind):
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


def has_bad_ocr_noise(text: str, dtype: str, source_kind: str = "") -> bool:
    if "�" in text:
        return True
    if dtype == "law" and source_kind == "pdf_skill_ocr":
        if re.search(r"[A-Za-z]{3,}", text):
            return True
        if re.search(r"[!`=<>′〉]", text):
            return True
    if dtype == "standard" and source_kind == "pdf_skill_ocr":
        if re.search(r"[|<>{}\[\]`′丨]", text):
            return True
        if re.search(r"[_=]{3,}|一{6,}", text):
            return True
        if re.search(r"PEA BSE|中国标准出版社|版权专有|新华书店|参考文献|读者服务|发行中心|印刷|举报电话", text):
            return True
    return False


def has_bad_ocr_heading(number: str, heading: str, dtype: str, source_kind: str = "") -> bool:
    if source_kind != "pdf_skill_ocr":
        return False
    if re.fullmatch(r"(?:19|20)\d{2}", number):
        return True
    if re.search(r"[|<>{}\[\]`′丨]", heading):
        return True
    if dtype == "standard":
        digit_count = len(re.sub(r"\D", "", number))
        if "." not in number and (number.startswith("0") or digit_count > 2):
            return True
        if count_cjk(heading) < 2:
            return True
    return False


def structured_skip_item(item: dict[str, Any], selected: dict[str, Any], reason: str) -> dict[str, Any]:
    quality = selected.get("quality") or {}
    return {
        "title": str(item.get("title") or ""),
        "reason": reason,
        "markdown": selected.get("source_ref"),
        "text_chars": int(quality.get("text_chars", 0) or 0),
        "text_quality": quality,
        "source_kind": selected.get("source_kind"),
        "source_pdf": item.get("path"),
        "needed_data": needed_data_hint(item, selected),
        "user_skipped": is_user_skipped_standard(str(item.get("title") or "")),
    }


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
        selected = select_markdown_source(item)
        markdown = selected.get("source_ref")
        text = str(selected.get("text") or "")
        quality = selected.get("quality") or {}
        text_chars = int(quality.get("text_chars", 0) or 0)
        if not markdown or not selected.get("usable"):
            skipped.append(structured_skip_item(item, selected, skip_reason(item, selected)))
            continue
        item = {**item, "_selected_markdown": markdown, "_selected_source_kind": selected.get("source_kind")}
        dtype = document_type(title)
        doc_id = f"std_doc_{slug(title)}"
        doc_clauses = split_clauses(item, doc_id, dtype, text)
        if not doc_clauses:
            skipped.append(structured_skip_item(item, selected, "low_structure_confidence"))
            continue
        doc = {
            "id": doc_id,
            "title": title,
            "document_type": dtype,
            "source_ref": markdown,
            "source_pdf": item.get("path"),
            "source_kind": selected.get("source_kind"),
            "year": item.get("year"),
            "pages": item.get("pages"),
            "text_chars": text_chars,
            "text_quality": quality,
            "needs_ocr": bool(item.get("needs_ocr")),
            "tags": infer_tags(title, dtype),
        }
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
            f"需补充 PDF/文本清单见 {rel_path(DATA_NEEDED_FILE)}。",
        ],
    }


def skip_reason(item: dict[str, Any], selected: dict[str, Any]) -> str:
    quality = selected.get("quality") or {}
    if not selected.get("source_ref"):
        return "missing_text_source"
    if int(quality.get("text_chars", 0) or 0) < MIN_TEXT_CHARS:
        return "low_text"
    if int(quality.get("cjk_chars", 0) or 0) < 600:
        return "low_chinese_text"
    if bool(item.get("needs_ocr")) and selected.get("source_kind") == "backup_pdf_text":
        return "needs_pdf_skill_ocr"
    return "low_structure_confidence"


def needed_data_hint(item: dict[str, Any], selected: dict[str, Any]) -> str:
    title = str(item.get("title") or "")
    if "GB" in title or "ISO" in title or "信息技术" in title:
        return "请提供文字层正常或高清扫描版标准 PDF；若只有扫描版，建议提供可 OCR 的 300dpi 以上 PDF。"
    if "法" in title:
        return "请提供官方网页文本、Word/Markdown 文本，或文字层正常 PDF；扫描版需 OCR 后再入库。"
    if selected.get("source_ref"):
        return "已有 PDF 但当前文本质量不足，请提供更清晰版本或可复制文本。"
    return "请提供 PDF 或可复制正文文本。"


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
        f"- 需补充数据清单：`{rel_path(DATA_NEEDED_FILE)}`",
        "",
        "## 已结构化文档",
        "",
    ]
    for doc in payload["documents"]:
        question_count = stats["questions_by_document"].get(doc["id"], 0)
        source_kind = doc.get("source_kind") or "backup_pdf_text"
        lines.append(f"- {doc['title']}：{doc['clause_count']} 条款，{question_count} 题，{source_kind}，`{doc['source_ref']}`")
    lines.extend(["", "## 待 OCR / 未结构化文档", ""])
    if payload["skipped_documents"]:
        for item in payload["skipped_documents"]:
            if item.get("user_skipped"):
                lines.append(f"- {item['title']}：{item['reason']}，文本 {item['text_chars']} 字；本轮按用户要求跳过。")
            else:
                lines.append(f"- {item['title']}：{item['reason']}，文本 {item['text_chars']} 字；需要：{item.get('needed_data')}")
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


def render_data_needed(payload: dict[str, Any]) -> str:
    skipped = payload.get("skipped_documents") or []
    user_skipped = [item for item in skipped if item.get("user_skipped")]
    needs_input = [item for item in skipped if not item.get("user_skipped")]
    lines = [
        "# 标准规范库需补充 PDF / 文本清单",
        "",
        "- 来源：`references/backup-pdfs/manifest.json`",
        "- 用途：补齐 `assets/questions/standards_training.json` 的标准规范专项训练库。",
        "- 原则：优先提供文字层正常 PDF、官方网页正文、Word/Markdown 文本；扫描件需能稳定 OCR，不用低清截图。",
        "",
        "## 这次已补",
        "",
    ]
    enhanced_docs = [doc for doc in payload.get("documents", []) if doc.get("source_kind") != "backup_pdf_text"]
    if enhanced_docs:
        for doc in enhanced_docs:
            lines.append(f"- {doc.get('title')}：已使用 `{doc.get('source_ref')}`，结构化 {doc.get('clause_count', 0)} 条款。")
    else:
        lines.append("- 暂无增强解析补入文档。")

    lines.extend(["", "## 本轮按要求跳过", ""])
    if user_skipped:
        for item in user_skipped:
            lines.append(f"- {item.get('title')}：本轮按用户要求跳过，不列入当前需补数据。")
    else:
        lines.append("- 暂无。")

    lines.extend(["", "## 还需要你提供的数据", ""])
    if not needs_input:
        lines.append("- 暂无。")
    for index, item in enumerate(needs_input, start=1):
        quality = item.get("text_quality") or {}
        lines.extend(
            [
                f"{index}. {item.get('title')}",
                f"   - 当前状态：{item.get('reason')}，文本 {item.get('text_chars', 0)} 字，中文 {quality.get('cjk_chars', 0)} 字，条款标记 {quality.get('article_markers', 0)}，数字标题 {quality.get('numeric_headings', 0)}。",
                f"   - 当前 PDF：`{item.get('source_pdf')}`",
                f"   - 建议提供：{item.get('needed_data')}",
            ]
        )
        if item.get("markdown"):
            lines.append(f"   - 当前文本源：`{item.get('markdown')}`")
    lines.extend(
        [
            "",
            "## 接入后重建命令",
            "",
            "```bash",
            "python scripts/import_standards_training.py --write --format markdown",
            "python scripts/validate_questions.py",
            "python scripts/update_skill_summary.py",
            "python scripts/build_search_index.py --write --format markdown",
            "```",
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
        DATA_NEEDED_FILE.parent.mkdir(parents=True, exist_ok=True)
        DATA_NEEDED_FILE.write_text(render_data_needed(payload), encoding="utf-8")

    if args.format == "markdown":
        print(render_summary(payload))
    else:
        print(json.dumps(payload["stats"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
