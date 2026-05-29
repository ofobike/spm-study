#!/usr/bin/env python
"""Build a structured past-exam training bank from extracted backup PDFs."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_FILE = ROOT / "references" / "backup-pdfs" / "manifest.json"
OUTPUT_FILE = ROOT / "assets" / "questions" / "past_exams.json"
SUMMARY_FILE = ROOT / "references" / "backup-pdfs" / "past-exams" / "structured-summary.md"


NOISE_PATTERNS = (
    r"信管网\(.*",
    r"信管网：.*",
    r"第\d+页共\d+页",
    r"本资料由.*",
    r"最终答案以.*",
    r"查看解析[:：].*",
    r"https?://\S+",
)

ANSWER_RE = re.compile(
    r"(?:信管网参考答案(?:[（(][^）)]*[）)])?|【参考答案】)\s*[:：]?\s*([A-D])",
    re.IGNORECASE,
)
OCR_ANSWER_RE = re.compile(
    r"(?m)^[\[(（{]?\s*江山答[案桊][^\nA-D0O&]{0,8}([A-D0O&])\s*$",
    re.IGNORECASE,
)
CHOICE_START_RE = re.compile(r"(?m)(?:^|\n)\s*(\d{1,2})[、.](?!html\b)\s*")
ANSWER_KEY_RE = re.compile(r"(?m)^\s*(\d{1,2})(?:\s*[~～-]\s*(\d{1,2}))?[.、]\s*([A-D]{1,10})\b")
QUESTION_HEADER_RE = re.compile(r"(?m)^\s*【?问题\s*(\d+)】?\s*(?:[（(]([^）)]*分[^）)]*)[）)])?\s*[：:]?\s*")
NUMBERED_QUESTION_RE = re.compile(r"(?m)^\s*(\d+)[.、]\s*(?:[（(]([^）)]*分[^）)]*)[）)])?\s*")
OCR_QUESTION_START_RE = re.compile(r"(?m)^\s*(?:(\d{1,2}|[IiLl]0)[.、]?)\s*")
OCR_CASE_HEADING_RE = re.compile(r"(?m)^\s*第([一二三四五六七八九十])题[。.:：]?\s*(.*)$")
OCR_PAPER_HEADING_RE = re.compile(r"(?m)^\s*试题([一二三四五六七八九十])[:：]\s*(.*)$")


def clean_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        if "参考答案" in line:
            lines.append(line)
            continue
        if any(re.fullmatch(pattern, line, flags=re.IGNORECASE) for pattern in NOISE_PATTERNS):
            continue
        lines.append(line)
    value = "\n".join(lines)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def source_text(item: dict[str, Any]) -> str:
    markdown = item.get("markdown")
    if not markdown:
        return ""
    path = ROOT / markdown
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore")
    body = re.sub(r"^# .+?\n(?:\n|> .+?\n)*", "", text, flags=re.DOTALL)
    return clean_text(body)


def normalize_option_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" ．.、")


def source_ref(item: dict[str, Any]) -> str | None:
    markdown = item.get("markdown")
    return str(markdown).replace("\\", "/") if markdown else None


def is_2024_ocr_combined_exam(item: dict[str, Any]) -> bool:
    """The 2024 下半年 source is a scanned combined PDF with OCR quirks."""
    return (
        item.get("year") == 2024
        and item.get("period") == "下半年"
        and item.get("subject") == "综合知识+案例"
        and "2024年系统规划与管理师真题解析" in str(item.get("markdown") or item.get("title") or "")
    )


def option_markers(block: str) -> list[re.Match[str]]:
    markers = list(re.finditer(r"(?m)^\s*([ABCD])\s*[、.．]\s*", block))
    if len(markers) >= 4:
        return markers
    markers = list(re.finditer(r"(?<![A-Za-z0-9\u4e00-\u9fff])([ABCD])\s*[、.．]\s*", block))
    if len(markers) >= 4:
        return markers
    markers = list(re.finditer(r"(?m)^\s*([ABCD])\s+", block))
    return markers if len(markers) >= 4 else []


def parse_options(block: str) -> tuple[str, list[str]] | None:
    markers = option_markers(block)
    if len(markers) < 4:
        return None
    option_map: dict[str, str] = {}
    for idx, marker in enumerate(markers):
        letter = marker.group(1)
        if letter in option_map:
            return None
        start = marker.end()
        end = markers[idx + 1].start() if idx + 1 < len(markers) else len(block)
        option_map[letter] = normalize_option_text(block[start:end])
    if set(option_map) != {"A", "B", "C", "D"}:
        return None
    question_text = normalize_option_text(block[: markers[0].start()])
    options = [f"{letter}. {option_map[letter]}" for letter in "ABCD"]
    return question_text, options


def normalize_ocr_answer(value: str) -> str | None:
    token = value.strip().upper()
    if token in {"0", "O"}:
        return "D"
    if token == "&":
        return "B"
    return token if token in {"A", "B", "C", "D"} else None


def normalize_ocr_option_marker(value: str) -> str | None:
    token = value.strip().upper()
    if token == "4":
        return "A"
    if token in {"0", "O"}:
        return "D"
    return token if token in {"A", "B", "C", "D"} else None


def normalize_ocr_question_number(value: str) -> int | None:
    token = value.strip().upper()
    if token in {"I0", "L0"}:
        return 10
    if not token.isdigit():
        return None
    number = int(token)
    return number if 1 <= number <= 75 else None


def option_text_quality(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    if not compact:
        return False
    meaningful = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]", compact)
    return len(meaningful) >= 2


def ocr_option_candidates(block: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    offset = 0
    for raw_line in block.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        match = re.match(r"^\s*([ABCD0O4])(?:(\s*[.．、]\s*)|(\s+))?(.*)$", line, flags=re.IGNORECASE)
        if match:
            marker = normalize_ocr_option_marker(match.group(1))
            rest = match.group(4) or ""
            has_separator = bool(match.group(2) or match.group(3))
            if marker and (has_separator or len(rest) <= 80):
                candidates.append(
                    {
                        "letter": marker,
                        "start": offset + match.start(1),
                        "end": offset + match.end(3 if match.group(3) else 2 if match.group(2) else 1),
                    }
                )
        offset += len(raw_line)
    return candidates


def parse_ocr_options(block: str) -> tuple[str, list[str]] | None:
    candidates = ocr_option_candidates(block)
    markers: list[dict[str, Any]] | None = None
    for index in range(0, max(0, len(candidates) - 3)):
        group = candidates[index : index + 4]
        if [item["letter"] for item in group] == list("ABCD"):
            markers = group
            break
    if not markers:
        return None

    option_map: dict[str, str] = {}
    for index, marker in enumerate(markers):
        letter = str(marker["letter"])
        start = int(marker["end"])
        end = int(markers[index + 1]["start"]) if index + 1 < len(markers) else len(block)
        option_map[letter] = normalize_option_text(block[start:end])

    if set(option_map) != {"A", "B", "C", "D"}:
        return None
    if not all(option_text_quality(option_map[letter]) for letter in "ABCD"):
        return None

    question_text = normalize_option_text(block[: int(markers[0]["start"])])
    options = [f"{letter}. {option_map[letter]}" for letter in "ABCD"]
    return question_text, options


def choice_section_2024(text: str) -> str:
    start_match = re.search(r"2024年系统规划与管理师综合知识真题与答案解析", text)
    end_match = re.search(r"2024年系统规划与管理师案例分析真题与答案解析", text)
    start = start_match.end() if start_match else 0
    end = end_match.start() if end_match else len(text)
    return text[start:end].strip()


def ocr_choice_block_start(segment: str, expected_number: int | None = None, fallback_to_start: bool = False) -> int | None:
    matches = []
    for match in OCR_QUESTION_START_RE.finditer(segment):
        number = normalize_ocr_question_number(match.group(1))
        if number is None:
            continue
        matches.append((number, match))
    if expected_number is not None:
        for number, match in matches:
            if number == expected_number:
                return match.start()
    if matches:
        return matches[-1][1].start()
    return 0 if fallback_to_start else None


def split_2024_ocr_choice_blocks(text: str) -> tuple[list[tuple[int, str, str]], list[str]]:
    section = choice_section_2024(text)
    answer_matches = list(OCR_ANSWER_RE.finditer(section))
    rows: list[tuple[int, str, str]] = []
    warnings: list[str] = []
    previous_answer_end = 0
    for index, answer_match in enumerate(answer_matches, start=1):
        answer = normalize_ocr_answer(answer_match.group(1))
        if not answer:
            warnings.append(f"choice_{index}: answer_parse_failed")
            previous_answer_end = answer_match.end()
            continue
        segment = section[previous_answer_end : answer_match.start()]
        block_start = ocr_choice_block_start(segment, expected_number=index, fallback_to_start=index == 1)
        if block_start is None:
            warnings.append(f"choice_{index}: start_parse_failed")
            previous_answer_end = answer_match.end()
            continue
        block = segment[block_start:].strip()
        block = re.sub(r"^L(?=IT\s)", "1.", block)
        block = re.sub(r"^\s*(?:\d{1,2}|[IiLl]0)[.、]?\s*", "", block, count=1)
        if block:
            rows.append((index, block, answer))
        previous_answer_end = answer_match.end()
    return rows, warnings


def parse_2024_ocr_choice_questions(item: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    text = source_text(item)
    questions: list[dict[str, Any]] = []
    warnings: list[str] = []
    rows, split_warnings = split_2024_ocr_choice_blocks(text)
    warnings.extend(split_warnings)
    for number, block, answer in rows:
        parsed = parse_ocr_options(block)
        if not parsed:
            warnings.append(f"choice_{number}: option_parse_failed")
            continue
        question_text, options = parsed
        if len(question_text) < 8:
            warnings.append(f"choice_{number}: short_question")
            continue
        year = item.get("year")
        period = item.get("period")
        qid = f"pe_{year}_{period_code(period)}_am_q{number:02d}"
        questions.append(
            {
                "id": qid,
                "year": year,
                "period": period,
                "subject": "综合知识",
                "number": number,
                "question": question_text,
                "options": options,
                "answer": answer,
                "explanation": "2024 下半年真题来源为扫描 PDF OCR 抽取，已跳过选项无法稳定识别的题；原文解析请核对 source_ref。",
                "chapter": "历年真题",
                "source": "past_exam",
                "question_type": "single_choice",
                "difficulty": "medium",
                "section": f"{year}{period or ''}综合知识真题（OCR抽取）",
                "knowledge_point": "历年真题综合知识",
                "source_ref": source_ref(item),
                "source_pdf": item.get("path"),
                "tags": ["历年真题", "综合知识", str(year), str(period or ""), "OCR抽取"],
            }
        )
    return questions, warnings


def answer_key(text: str) -> dict[int, str]:
    answers: dict[int, str] = {}
    for match in ANSWER_KEY_RE.finditer(text):
        start = int(match.group(1))
        end = int(match.group(2) or start)
        values = match.group(3).strip().upper()
        if end < start or len(values) < end - start + 1:
            continue
        for offset, number in enumerate(range(start, end + 1)):
            answers[number] = values[offset]
    return answers


def split_choice_blocks(text: str) -> list[tuple[int, str, str]]:
    rows: list[tuple[int, str, str]] = []
    seen: set[int] = set()
    for answer_match in ANSWER_RE.finditer(text):
        starts = [match for match in CHOICE_START_RE.finditer(text[: answer_match.start()]) if 1 <= int(match.group(1)) <= 75]
        if not starts:
            continue
        start_match = starts[-1]
        number = int(start_match.group(1))
        if not (1 <= number <= 75):
            continue
        block = text[start_match.end() : answer_match.start()].strip()
        if "信管网解析" in block:
            block = block.split("信管网解析", 1)[0].strip()
        if "\n解析" in block:
            block = block.split("\n解析", 1)[0].strip()
        if number not in seen:
            rows.append((number, block, answer_match.group(1).strip().upper()))
            seen.add(number)

    keys = answer_key(text)
    starts = [match for match in CHOICE_START_RE.finditer(text) if 1 <= int(match.group(1)) <= 75]
    for idx, start_match in enumerate(starts):
        number = int(start_match.group(1))
        if number in seen or number not in keys:
            continue
        end = starts[idx + 1].start() if idx + 1 < len(starts) else len(text)
        block = text[start_match.end() : end].strip()
        if "解析" in block:
            block = block.split("解析", 1)[0].strip()
        rows.append((number, block, keys[number]))
        seen.add(number)
    return sorted(rows, key=lambda row: row[0])


def parse_choice_questions(item: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    if is_2024_ocr_combined_exam(item):
        return parse_2024_ocr_choice_questions(item)

    text = source_text(item)
    questions: list[dict[str, Any]] = []
    warnings: list[str] = []
    for number, block, answer in split_choice_blocks(text):
        parsed = parse_options(block)
        if not parsed:
            warnings.append(f"choice_{number}: option_parse_failed")
            continue
        question_text, options = parsed
        if len(question_text) < 8:
            warnings.append(f"choice_{number}: short_question")
            continue
        year = item.get("year")
        period = item.get("period")
        qid = f"pe_{year}_{period_code(period)}_am_q{number:02d}"
        questions.append(
            {
                "id": qid,
                "year": year,
                "period": period,
                "subject": "综合知识",
                "number": number,
                "question": question_text,
                "options": options,
                "answer": answer,
                "explanation": "历年真题解析来源于备份 PDF，原文解析可在 source_ref 中查看。",
                "chapter": "历年真题",
                "source": "past_exam",
                "question_type": "single_choice",
                "difficulty": "medium",
                "section": f"{year}{period or ''}综合知识真题",
                "knowledge_point": "历年真题综合知识",
                "source_ref": source_ref(item),
                "source_pdf": item.get("path"),
                "tags": ["历年真题", "综合知识", str(year), str(period or "")],
            }
        )
    return questions, warnings


def period_code(period: str | None) -> str:
    if period == "上半年":
        return "h1"
    if period == "下半年":
        return "h2"
    return "hx"


def split_exam_blocks(text: str) -> list[tuple[int, str]]:
    matches = list(re.finditer(r"(?m)^.*?试题\s*([一二三四五六七八九十]+).*$", text))
    if not matches:
        return []
    blocks: list[tuple[int, str]] = []
    chinese_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        number = chinese_nums.get(match.group(1), idx + 1)
        blocks.append((number or idx + 1, text[start:end].strip()))
    return blocks


def chinese_number(value: str, default: int = 0) -> int:
    chinese_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    return chinese_nums.get(value, default)


def first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def split_reference_answer(block: str) -> tuple[str, str]:
    match = re.search(r"(?m)^.*参考答案.*$", block)
    if not match:
        return block, ""
    return block[: match.start()].strip(), block[match.start() :].strip()


def parse_score(score_text: str | None) -> int | None:
    score_match = re.search(r"(\d+)\s*分", score_text or "")
    return int(score_match.group(1)) if score_match else None


def parse_case_reference_answers(answer_text: str) -> dict[str, str]:
    if not answer_text:
        return {}
    matches = list(QUESTION_HEADER_RE.finditer(answer_text))
    if not matches:
        matches = list(NUMBERED_QUESTION_RE.finditer(answer_text))
    refs: dict[str, str] = {}
    for idx, match in enumerate(matches):
        number = match.group(1)
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(answer_text)
        value = clean_text(answer_text[start:end])
        if value:
            refs[number] = value
    return refs


def fill_case_scores(questions: list[dict[str, Any]], total_score: int = 25) -> None:
    missing = [question for question in questions if question.get("score") is None]
    if not missing:
        return
    known = sum(int(question.get("score") or 0) for question in questions if question.get("score") is not None)
    remaining = max(0, total_score - known)
    base = remaining // len(missing) if remaining else max(1, total_score // max(1, len(questions)))
    extra = remaining % len(missing) if remaining else 0
    for index, question in enumerate(missing):
        question["score"] = base + (1 if index < extra else 0)


def section_between(text: str, start_pattern: str, end_pattern: str | None = None) -> str:
    start_match = re.search(start_pattern, text)
    if not start_match:
        return ""
    start = start_match.end()
    end = len(text)
    if end_pattern:
        end_match = re.search(end_pattern, text[start:])
        if end_match:
            end = start + end_match.start()
    return text[start:end].strip()


def case_section_2024(text: str) -> str:
    return section_between(
        text,
        r"2024年系统规划与管理师案例分析真题与答案解析",
        r"2024年系统规划与管理师论文写作真题与答案解析",
    )


def paper_section_2024(text: str) -> str:
    return section_between(text, r"2024年系统规划与管理师论文写作真题与答案解析")


def split_2024_ocr_case_blocks(text: str) -> list[tuple[int, str, str]]:
    section = case_section_2024(text)
    matches = list(OCR_CASE_HEADING_RE.finditer(section))
    blocks: list[tuple[int, str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        number = chinese_number(match.group(1), index + 1)
        title = normalize_option_text(match.group(2)) or f"案例试题{number}"
        blocks.append((number, title, section[start:end].strip()))
    return blocks


def split_2024_ocr_paper_blocks(text: str) -> list[tuple[int, str, str]]:
    section = paper_section_2024(text)
    matches = list(OCR_PAPER_HEADING_RE.finditer(section))
    blocks: list[tuple[int, str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        number = chinese_number(match.group(1), index + 1)
        title = normalize_option_text(match.group(2)) or f"论文试题{number}"
        blocks.append((number, title, section[start:end].strip()))
    return blocks


def split_2024_ocr_reference_answer(block: str) -> tuple[str, str]:
    match = re.search(r"(?m)^\s*\(江山老师参考答案\)\s*$", block)
    if not match:
        return block.strip(), ""
    return block[: match.start()].strip(), block[match.end() :].strip()


def parse_2024_case_reference_answers(answer_text: str) -> dict[str, str]:
    refs: dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^\s*([1-9])\s*[.、]?\s*(?=\S|$)", answer_text))
    for index, match in enumerate(matches):
        number = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(answer_text)
        value = clean_text(answer_text[start:end])
        if value:
            refs[number] = value
    return refs


def parse_2024_ocr_case_block(item: dict[str, Any], number: int, title: str, block: str) -> dict[str, Any] | None:
    question_part, answer_part = split_2024_ocr_reference_answer(block)
    question_part = re.sub(r"(?m)^(\s*)45分判断题[（(]5分[）)]", r"\g<1>4.判断题(5分)", question_part)
    question_matches = list(re.finditer(r"(?m)^\s*(\d+)\s*[.、]?\s*(.*?)(?:[（(](\d+)\s*分[）)])?\s*$", question_part))
    valid_matches = []
    for match in question_matches:
        question_number = int(match.group(1))
        if 1 <= question_number <= 9:
            valid_matches.append(match)
    if not valid_matches:
        return None

    scenario_end = valid_matches[0].start()
    scenario = clean_text(question_part[:scenario_end])
    if not scenario:
        scenario = f"2024 下半年案例分析试题{number}：{title}。原始资料背景标注为暂缺，请结合 source_ref 查看 OCR 原文。"

    reference_answers = parse_2024_case_reference_answers(answer_part)
    questions: list[dict[str, Any]] = []
    for index, match in enumerate(valid_matches):
        start = match.start()
        end = valid_matches[index + 1].start() if index + 1 < len(valid_matches) else len(question_part)
        raw_question = clean_text(question_part[start:end])
        if not raw_question:
            continue
        question_number = match.group(1)
        score = int(match.group(3)) if match.group(3) else parse_score(raw_question)
        reference = reference_answers.get(question_number, "")
        questions.append(
            {
                "id": f"pe_{item.get('year')}_{period_code(item.get('period'))}_case{number}_q{question_number}",
                "question": raw_question,
                "question_type": "subjective",
                "score": score,
                "answer": reference,
                "explanation": "2024 下半年案例答案来源为扫描 PDF OCR 抽取；暂缺或噪声答案请结合 source_ref 人工核对。",
            }
        )
    if not questions:
        return None
    fill_case_scores(questions)
    total_score = sum(int(question.get("score") or 0) for question in questions) or 25
    return {
        "id": f"pe_{item.get('year')}_{period_code(item.get('period'))}_case{number}",
        "year": item.get("year"),
        "period": item.get("period"),
        "subject": "案例分析",
        "number": number,
        "title": f"{item.get('year')}{item.get('period') or ''}案例试题{number}：{title}",
        "scenario": scenario,
        "questions": questions,
        "difficulty": "hard",
        "total_score": total_score,
        "source": "past_exam",
        "source_ref": source_ref(item),
        "source_pdf": item.get("path"),
        "tags": ["历年真题", "案例分析", str(item.get("year")), str(item.get("period") or ""), "OCR抽取"],
    }


def parse_2024_ocr_case_studies(item: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    text = source_text(item)
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for number, title, block in split_2024_ocr_case_blocks(text):
        row = parse_2024_ocr_case_block(item, number, title, block)
        if row:
            rows.append(row)
        else:
            warnings.append(f"case_{number}: parse_failed")
    return rows, warnings


def parse_2024_ocr_paper_topics(item: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    text = source_text(item)
    topics: list[dict[str, Any]] = []
    warnings: list[str] = []
    for number, title, block in split_2024_ocr_paper_blocks(text):
        title = re.split(r"[（(]", title, maxsplit=1)[0].strip() or title
        prompt = clean_text(block)
        if len(prompt) < 30:
            warnings.append(f"paper_{number}: short_prompt")
            continue
        topics.append(
            {
                "id": f"pe_{item.get('year')}_{period_code(item.get('period'))}_paper{number}",
                "year": item.get("year"),
                "period": item.get("period"),
                "subject": "论文",
                "number": number,
                "title": title,
                "prompt": prompt,
                "source": "past_exam",
                "source_ref": source_ref(item),
                "source_pdf": item.get("path"),
                "tags": ["历年真题", "论文", str(item.get("year")), str(item.get("period") or ""), "OCR抽取"],
            }
        )
    return topics, warnings


def parse_case_block(item: dict[str, Any], number: int, block: str) -> dict[str, Any] | None:
    title_match = re.search(r"^.*?试题\s*[一二三四五六七八九十]+[：:]?\s*(.*)$", block, re.M)
    title_suffix = normalize_option_text(title_match.group(1)) if title_match else ""
    question_part, answer_part = split_reference_answer(block)
    question_matches = list(QUESTION_HEADER_RE.finditer(question_part))
    if not question_matches:
        question_matches = list(NUMBERED_QUESTION_RE.finditer(question_part))
    scenario_end = question_matches[0].start() if question_matches else len(block)
    scenario = clean_text(question_part[:scenario_end])
    reference_answers = parse_case_reference_answers(answer_part)
    questions = []
    for idx, match in enumerate(question_matches):
        start = match.end()
        end = question_matches[idx + 1].start() if idx + 1 < len(question_matches) else len(question_part)
        score_text = match.group(2) if match.lastindex and match.lastindex >= 2 else None
        score = parse_score(score_text)
        q_text = clean_text(question_part[start:end])
        if not q_text:
            continue
        reference = reference_answers.get(match.group(1), "")
        questions.append(
            {
                "id": f"pe_{item.get('year')}_{period_code(item.get('period'))}_case{number}_q{match.group(1)}",
                "question": q_text,
                "question_type": "subjective",
                "score": score,
                "answer": reference,
                "explanation": "参考答案来源于历年真题解析 PDF。" if reference else "该题参考答案未能从 PDF 文本中稳定抽取，请结合 source_ref 原文人工核对。",
            }
        )
    if not scenario or not questions:
        return None
    fill_case_scores(questions)
    total_score = sum(int(question.get("score") or 0) for question in questions) or 25
    return {
        "id": f"pe_{item.get('year')}_{period_code(item.get('period'))}_case{number}",
        "year": item.get("year"),
        "period": item.get("period"),
        "subject": "案例分析",
        "number": number,
        "title": f"{item.get('year')}{item.get('period') or ''}案例试题{number}" + (f"：{title_suffix}" if title_suffix else ""),
        "scenario": scenario,
        "questions": questions,
        "difficulty": "hard",
        "total_score": total_score,
        "source": "past_exam",
        "source_ref": source_ref(item),
        "source_pdf": item.get("path"),
        "tags": ["历年真题", "案例分析", str(item.get("year")), str(item.get("period") or "")],
    }


def parse_case_studies(item: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    if is_2024_ocr_combined_exam(item):
        return parse_2024_ocr_case_studies(item)

    text = source_text(item)
    rows = []
    warnings = []
    for number, block in split_exam_blocks(text):
        if "参考答案" in first_non_empty_line(block):
            continue
        row = parse_case_block(item, number, block)
        if row:
            rows.append(row)
        else:
            warnings.append(f"case_{number}: parse_failed")
    return rows, warnings


def parse_paper_topics(item: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    if is_2024_ocr_combined_exam(item):
        return parse_2024_ocr_paper_topics(item)

    text = source_text(item)
    topics = []
    warnings = []
    for number, block in split_exam_blocks(text):
        if "参考答案" in first_non_empty_line(block):
            continue
        title_match = re.search(r"^.*?试题\s*[一二三四五六七八九十]+[：:]?\s*(.+)$", block, re.M)
        title = normalize_option_text(title_match.group(1)) if title_match else f"论文试题{number}"
        title = re.sub(r"^论", "论", title).strip()
        prompt = clean_text(block)
        if len(prompt) < 30:
            warnings.append(f"paper_{number}: short_prompt")
            continue
        topics.append(
            {
                "id": f"pe_{item.get('year')}_{period_code(item.get('period'))}_paper{number}",
                "year": item.get("year"),
                "period": item.get("period"),
                "subject": "论文",
                "number": number,
                "title": title,
                "prompt": prompt,
                "source": "past_exam",
                "source_ref": source_ref(item),
                "source_pdf": item.get("path"),
                "tags": ["历年真题", "论文", str(item.get("year")), str(item.get("period") or "")],
            }
        )
    return topics, warnings


def dedupe_by_id(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for row in rows:
        qid = str(row.get("id") or "")
        if not qid:
            continue
        if qid not in deduped:
            deduped[qid] = row
            continue
        current = deduped[qid]
        current_score = len(str(current.get("question") or current.get("scenario") or current.get("prompt") or ""))
        new_score = len(str(row.get("question") or row.get("scenario") or row.get("prompt") or ""))
        if new_score > current_score:
            deduped[qid] = row
    return list(deduped.values())


def build_past_exam_bank() -> dict[str, Any]:
    manifest = load_manifest()
    files = [item for item in manifest.get("files", []) if item.get("category") == "past-exam" and item.get("markdown")]
    choice_questions: list[dict[str, Any]] = []
    case_studies: list[dict[str, Any]] = []
    paper_topics: list[dict[str, Any]] = []
    warnings: dict[str, list[str]] = {}
    for item in files:
        subject = str(item.get("subject") or "")
        if subject == "综合知识" or subject == "综合知识+案例":
            rows, warn = parse_choice_questions(item)
            choice_questions.extend(rows)
            if warn:
                warnings[item["relative_path"]] = warn[:20]
        if subject == "案例分析" or subject == "综合知识+案例":
            rows, warn = parse_case_studies(item)
            case_studies.extend(rows)
            if warn:
                warnings.setdefault(item["relative_path"], []).extend(warn[:20])
        if subject == "论文" or is_2024_ocr_combined_exam(item):
            rows, warn = parse_paper_topics(item)
            paper_topics.extend(rows)
            if warn:
                warnings[item["relative_path"]] = warn[:20]
    choice_questions = dedupe_by_id(choice_questions)
    case_studies = dedupe_by_id(case_studies)
    paper_topics = dedupe_by_id(paper_topics)
    return {
        "schema_version": 1,
        "source": str(MANIFEST_FILE.relative_to(ROOT)),
        "generated_from": "references/backup-pdfs/past-exams",
        "stats": {
            "choice_questions": len(choice_questions),
            "case_studies": len(case_studies),
            "case_subquestions": sum(len(item.get("questions", [])) for item in case_studies),
            "paper_topics": len(paper_topics),
            "years": sorted({item.get("year") for item in [*choice_questions, *case_studies, *paper_topics] if item.get("year")}),
            "choice_answer_distribution": dict(Counter(item.get("answer") for item in choice_questions)),
            "warnings": warnings,
        },
        "choice_questions": sorted(choice_questions, key=lambda item: (item.get("year") or 0, str(item.get("period") or ""), item.get("number") or 0)),
        "case_studies": sorted(case_studies, key=lambda item: (item.get("year") or 0, str(item.get("period") or ""), item.get("number") or 0)),
        "paper_topics": sorted(paper_topics, key=lambda item: (item.get("year") or 0, str(item.get("period") or ""), item.get("number") or 0)),
    }


def render_summary(bank: dict[str, Any]) -> str:
    stats = bank["stats"]
    lines = [
        "# 历年真题结构化入库报告",
        "",
        f"- 来源：`{bank['source']}`",
        f"- 选择题：{stats['choice_questions']}",
        f"- 案例题：{stats['case_studies']}，子问题：{stats['case_subquestions']}",
        f"- 论文题目：{stats['paper_topics']}",
        f"- 年份：{stats['years']}",
        f"- 选择题答案分布：{stats['choice_answer_distribution']}",
        "",
        "## 使用方式",
        "",
        "```bash",
        "python scripts/study.py past-exam start --year 2022 --count 5 --format markdown",
        "python scripts/study.py past-exam case --year 2021 --format markdown",
        "python scripts/study.py past-exam paper --year 2022 --format markdown",
        "```",
        "",
    ]
    warnings = stats.get("warnings") or {}
    lines.append("## 解析警告")
    if not warnings:
        lines.append("- 暂无。")
    else:
        for source, items in warnings.items():
            lines.append(f"- {source}: {', '.join(items[:8])}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Import structured past exams from extracted PDFs.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()
    bank = build_past_exam_bank()
    if args.write:
        OUTPUT_FILE.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        SUMMARY_FILE.write_text(render_summary(bank), encoding="utf-8")
    if args.format == "json":
        print(json.dumps(bank["stats"], ensure_ascii=False, indent=2))
    else:
        print(render_summary(bank))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
