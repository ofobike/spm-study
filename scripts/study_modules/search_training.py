from __future__ import annotations

import argparse
import json
import re
from typing import Any

from study_utils import (
    ROOT,
    choose_questions,
    load_json,
    make_session,
    public_question,
    render_questions_markdown,
)

from study_modules.common import (
    normalize_lookup_text,
    session_file_value,
    session_next_step,
    should_write_session,
)
from study_modules.settings import SEARCH_INDEX_FILE, SPRINT_TRAINING_FILE


def load_sprint_training() -> dict[str, Any]:
    return load_json(
        SPRINT_TRAINING_FILE,
        {
            "stats": {},
            "cards": [],
            "choice_questions": [],
            "case_prompts": [],
            "note": "尚未生成冲刺训练库。请先运行 python scripts/build_sprint_training.py --write --format markdown。",
        },
    )


def load_sprint_training_cards() -> list[dict[str, Any]]:
    rows = load_sprint_training().get("cards", [])
    return rows if isinstance(rows, list) else []


def load_sprint_training_choices() -> list[dict[str, Any]]:
    rows = load_sprint_training().get("choice_questions", [])
    return rows if isinstance(rows, list) else []


def load_sprint_training_cases() -> list[dict[str, Any]]:
    rows = load_sprint_training().get("case_prompts", [])
    return rows if isinstance(rows, list) else []


def sprint_training_question_lookup() -> dict[str, dict[str, Any]]:
    return {str(question.get("id")): question for question in load_sprint_training_choices() if question.get("id")}


def filter_sprint_kind(rows: list[dict[str, Any]], kind: str | None = None, keyword: str | None = None) -> list[dict[str, Any]]:
    result = list(rows)
    if kind and kind != "all":
        result = [row for row in result if row.get("kind") == kind]
    if keyword:
        needle = str(keyword)
        result = [
            row
            for row in result
            if needle in str(row.get("title") or "")
            or needle in str(row.get("prompt") or "")
            or needle in str(row.get("question") or "")
            or needle in str(row.get("answer") or "")
            or needle in str(row.get("explanation") or "")
        ]
    return result


def load_search_index() -> dict[str, Any]:
    return load_json(
        SEARCH_INDEX_FILE,
        {
            "chunk_count": 0,
            "source_counts": {},
            "entries": [],
            "note": "尚未生成全资料检索索引。请先运行 python scripts/build_search_index.py --write --format markdown。",
        },
    )


def normalize_search_text(value: str | None) -> str:
    return normalize_lookup_text(value)


def tokenize_search_query(text: str) -> list[str]:
    value = normalize_search_text(text)
    tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9+\-_/\.]*|[\u4e00-\u9fff]{2,}", value)
    result: list[str] = []
    for token in tokens:
        if len(token) <= 8:
            result.append(token.lower())
            continue
        if re.fullmatch(r"[\u4e00-\u9fff]+", token):
            result.append(token)
            result.extend(token[index : index + 2] for index in range(0, len(token) - 1))
        else:
            result.append(token.lower())
    seen: set[str] = set()
    deduped: list[str] = []
    for token in result:
        if token and token not in seen:
            seen.add(token)
            deduped.append(token)
    return deduped


def clean_text_for_preview(text: str) -> str:
    value = str(text or "").replace("\u3000", " ")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", value)
    return value.strip()


def search_entry_score(entry: dict[str, Any], query: str, tokens: list[str]) -> tuple[float, list[str]]:
    haystack = normalize_search_text(
        "\n".join(
            str(entry.get(key) or "")
            for key in ("title", "heading", "source_type", "path", "text")
        )
    ).lower()
    query_norm = normalize_search_text(query).lower()
    score = 0.0
    matched: list[str] = []
    if query_norm and query_norm in haystack:
        score += 8.0
        matched.append(query_norm)
    for token in tokens:
        token_norm = token.lower()
        if not token_norm or token_norm not in haystack:
            continue
        count = haystack.count(token_norm)
        weight = 1.0
        if len(token_norm) >= 4:
            weight += 0.8
        if token_norm in normalize_search_text(str(entry.get("title") or "")).lower():
            weight += 1.2
        if token_norm in normalize_search_text(str(entry.get("heading") or "")).lower():
            weight += 0.8
        score += min(4, count) * weight
        matched.append(token)
    return score, matched[:10]


def clean_search_snippet(text: str, query: str, tokens: list[str], max_chars: int = 260) -> str:
    body = clean_text_for_preview(text)
    if not body:
        return ""
    lower = body.lower()
    candidates = [normalize_search_text(query).lower()] + [token.lower() for token in tokens]
    positions = [lower.find(token) for token in candidates if token and lower.find(token) >= 0]
    start = max(0, min(positions) - 60) if positions else 0
    snippet = body[start : start + max_chars]
    if start > 0:
        snippet = "..." + snippet
    if start + max_chars < len(body):
        snippet += "..."
    return snippet


def build_search_payload(args: argparse.Namespace) -> dict[str, Any]:
    index = load_search_index()
    query = str(getattr(args, "query", "") or "").strip()
    tokens = tokenize_search_query(query)
    source_type = getattr(args, "source_type", None)
    chapter = getattr(args, "chapter", None)
    entries = index.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    scored: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if source_type and entry.get("source_type") != source_type:
            continue
        if chapter is not None and int(entry.get("chapter") or 0) != int(chapter):
            continue
        score, matched = search_entry_score(entry, query, tokens)
        if score <= 0:
            continue
        snippet = clean_search_snippet(str(entry.get("text") or ""), query, tokens)
        scored.append({**entry, "score": round(score, 3), "matched_terms": matched, "snippet": snippet})
    scored.sort(key=lambda item: (-float(item["score"]), len(str(item.get("text") or ""))))
    limit = max(1, int(getattr(args, "limit", 8) or 8))
    return {
        "query": query,
        "tokens": tokens,
        "source_type": source_type,
        "chapter": chapter,
        "index_file": str(SEARCH_INDEX_FILE.relative_to(ROOT)),
        "chunk_count": index.get("chunk_count", len(entries)),
        "source_counts": index.get("source_counts", {}),
        "matched_count": len(scored),
        "results": scored[:limit],
        "note": index.get("note"),
    }


def render_search_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 全资料检索",
        "",
        f"- 查询：{payload.get('query')}",
        f"- 索引：{payload.get('index_file')}",
        f"- 片段数：{payload.get('chunk_count', 0)}",
        f"- 筛选：{payload.get('source_type') or '全部来源'} {('第' + str(payload.get('chapter')) + '章') if payload.get('chapter') else ''}".rstrip(),
        f"- 命中：{payload.get('matched_count', 0)}",
        "",
    ]
    if payload.get("note"):
        lines.append(f"> {payload['note']}")
        lines.append("")
    if not payload.get("results"):
        lines.append("没有匹配到资料片段。可以换一个关键词，或先运行 `python scripts/build_search_index.py --write --format markdown` 更新索引。")
        return "\n".join(lines) + "\n"
    for index, item in enumerate(payload["results"], start=1):
        heading = f" / {item.get('heading')}" if item.get("heading") else ""
        chapter = f"；第{item.get('chapter')}章" if item.get("chapter") else ""
        lines.append(f"## {index}. {item.get('title')}{heading}")
        lines.append(f"- 来源：{item.get('path')}；类型：{item.get('source_type')}{chapter}")
        lines.append(f"- 相关度：{item.get('score')}；命中词：{', '.join(item.get('matched_terms') or [])}")
        if item.get("snippet"):
            lines.append(f"- 摘要：{item['snippet']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_search(args: argparse.Namespace) -> int:
    payload = build_search_payload(args)
    if args.format == "markdown":
        print(render_search_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def public_sprint_training_question(question: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    result = public_question(question, include_answer=include_answer)
    for key in ("kind", "kind_label", "note"):
        if key in question:
            result[key] = question[key]
    return result


def build_sprint_training_cards_payload(args: argparse.Namespace) -> dict[str, Any]:
    training = load_sprint_training()
    rows = filter_sprint_kind(load_sprint_training_cards(), getattr(args, "kind", "all"), getattr(args, "keyword", None))
    selected = choose_questions(rows, int(args.count), seed=getattr(args, "seed", None))
    return {
        "title": "冲刺背诵卡",
        "kind": getattr(args, "kind", "all"),
        "keyword": getattr(args, "keyword", None),
        "available": len(rows),
        "cards": selected,
        "show_answer": bool(getattr(args, "show_answer", False)),
        "stats": training.get("stats", {}),
        "source": str(SPRINT_TRAINING_FILE.relative_to(ROOT)),
        "note": training.get("note"),
    }


def build_sprint_training_start_payload(args: argparse.Namespace, write: bool = True) -> dict[str, Any]:
    training = load_sprint_training()
    rows = filter_sprint_kind(load_sprint_training_choices(), getattr(args, "kind", "all"), getattr(args, "keyword", None))
    selected = choose_questions(rows, int(args.count), seed=getattr(args, "seed", None))
    session = make_session(
        "sprint_training",
        [question["id"] for question in selected],
        {
            "kind": getattr(args, "kind", "all"),
            "keyword": getattr(args, "keyword", None),
            "count": int(args.count),
            "seed": getattr(args, "seed", None),
            "source": str(SPRINT_TRAINING_FILE.relative_to(ROOT)),
        },
    )
    write = write and should_write_session(args)
    next_step = f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown"
    return {
        "title": "冲刺模拟候选题训练",
        "session": session,
        "session_file": session_file_value(session, write),
        "kind": getattr(args, "kind", "all"),
        "keyword": getattr(args, "keyword", None),
        "available": len(rows),
        "questions": [public_sprint_training_question(question) for question in selected],
        "next_step": session_next_step(next_step, write),
        "stats": training.get("stats", {}),
        "source": str(SPRINT_TRAINING_FILE.relative_to(ROOT)),
        "note": "冲刺模拟候选题来自自编模考 OCR 资料，支持提交判分；不是历年真题。",
    }


def build_sprint_training_case_payload(args: argparse.Namespace) -> dict[str, Any]:
    training = load_sprint_training()
    rows = filter_sprint_kind(load_sprint_training_cases(), getattr(args, "kind", "all"), getattr(args, "keyword", None))
    selected = choose_questions(rows, int(args.count), seed=getattr(args, "seed", None))
    return {
        "title": "冲刺案例采分点训练",
        "kind": getattr(args, "kind", "all"),
        "keyword": getattr(args, "keyword", None),
        "available": len(rows),
        "items": selected,
        "show_answer": bool(getattr(args, "show_answer", False)),
        "stats": training.get("stats", {}),
        "source": str(SPRINT_TRAINING_FILE.relative_to(ROOT)),
        "note": "案例采分点来自冲刺资料 OCR/抽取文本，用于主观题默写和素材补充；不是历年真题。",
    }


def render_sprint_training_cards_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 冲刺背诵卡",
        "",
        f"- 来源：{payload['source']}",
        f"- 筛选：{payload.get('kind') or 'all'} {payload.get('keyword') or ''}".rstrip(),
        f"- 可用卡片：{payload['available']}",
        f"- 说明：{payload.get('note')}",
        "",
    ]
    if not payload.get("cards"):
        lines.append("没有匹配到冲刺背诵卡。")
        return "\n".join(lines) + "\n"
    for index, card in enumerate(payload["cards"], start=1):
        lines.append(f"{index}. [{card.get('id')}] {card.get('prompt')}")
        lines.append(f"   类型：{card.get('kind_label')}；来源：{card.get('source_ref')}")
        if payload.get("show_answer"):
            answer = clean_text_for_preview(str(card.get("answer") or ""))
            lines.append(f"   参考答案：{answer[:600]}")
        lines.append("")
    if not payload.get("show_answer"):
        lines.append("提示：加 `--show-answer` 可显示参考答案。")
    return "\n".join(lines).rstrip() + "\n"


def render_sprint_training_start_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 冲刺模拟候选题训练",
        "",
        f"- Session: {payload['session']['id']}",
        f"- File: {payload['session_file']}",
        f"- 筛选：{payload.get('kind') or 'all'} {payload.get('keyword') or ''}".rstrip(),
        f"- 可用题数：{payload['available']}",
        f"- 说明：{payload['note']}",
        "",
    ]
    if payload.get("questions"):
        lines.append(render_questions_markdown(payload["questions"]).rstrip())
        lines.append("")
        lines.append(f"Next: {payload['next_step']}")
    else:
        lines.append("没有匹配到可训练的冲刺模拟候选题。")
        lines.append("Next: python scripts/study.py sprint-training cards --format markdown")
    return "\n".join(lines) + "\n"


def render_sprint_training_case_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 冲刺案例采分点训练",
        "",
        f"- 来源：{payload['source']}",
        f"- 筛选：{payload.get('kind') or 'all'} {payload.get('keyword') or ''}".rstrip(),
        f"- 可用采分点：{payload['available']}",
        f"- 说明：{payload.get('note')}",
        "",
    ]
    if not payload.get("items"):
        lines.append("没有匹配到冲刺案例采分点。")
        return "\n".join(lines) + "\n"
    for index, item in enumerate(payload["items"], start=1):
        lines.append(f"{index}. [{item.get('id')}] {item.get('prompt')}")
        lines.append(f"   类型：{item.get('kind_label')}；来源：{item.get('source_ref')}")
        if payload.get("show_answer"):
            answer = clean_text_for_preview(str(item.get("answer") or ""))
            lines.append(f"   参考采分点：{answer[:800]}")
        lines.append("")
    if not payload.get("show_answer"):
        lines.append("提示：先默写，再加 `--show-answer` 对照采分点。")
    return "\n".join(lines).rstrip() + "\n"


def command_sprint_training_cards(args: argparse.Namespace) -> int:
    payload = build_sprint_training_cards_payload(args)
    if args.format == "markdown":
        print(render_sprint_training_cards_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_sprint_training_start(args: argparse.Namespace) -> int:
    payload = build_sprint_training_start_payload(args)
    if args.format == "markdown":
        print(render_sprint_training_start_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_sprint_training_case(args: argparse.Namespace) -> int:
    payload = build_sprint_training_case_payload(args)
    if args.format == "markdown":
        print(render_sprint_training_case_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
