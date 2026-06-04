#!/usr/bin/env python
"""Turn sprint/cram markdown materials into conservative training assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from study_utils import ROOT, choose_questions, save_json


SPRINT_DIR = ROOT / "references" / "internal" / "sprint-materials"
MANIFEST_FILE = SPRINT_DIR / "manifest.json"
OUTPUT_FILE = ROOT / "assets" / "questions" / "sprint_training.json"
INDEX_FILE = SPRINT_DIR / "structured-training.md"
CHOICES = ["A", "B", "C", "D"]


KIND_LABELS = {
    "mnemonic": "记忆口诀",
    "gold-points": "金色考点",
    "mock-exam": "综合模考题",
    "csf-risk": "关键成功因素与风险控制",
    "activities": "130个活动",
    "sprint-guide": "规划冲刺资料",
}

DOMAIN_HINTS = (
    "服务",
    "信息",
    "系统",
    "管理",
    "规划",
    "设计",
    "过程",
    "活动",
    "需求",
    "风险",
    "质量",
    "安全",
    "数据",
    "资源",
    "技术",
    "人员",
    "项目",
    "成本",
    "目录",
    "级别",
    "标准",
    "能力",
    "可用",
    "连续",
    "知识",
    "监控",
    "应急",
    "部署",
    "实施",
    "运营",
    "改进",
    "治理",
    "论文",
    "案例",
    "云",
    "网络",
    "智能",
    "数字",
    "口诀",
    "模型",
    "工具",
    "KPI",
    "IT",
    "SLA",
    "OLA",
    "UC",
    "PDCA",
    "DMAIC",
    "ITSS",
    "ISO",
    "CMMM",
    "大数据",
    "电子商务",
    "诺兰",
    "等保",
)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def clean_text(text: str) -> str:
    value = text.replace("\u3000", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def clean_line(text: str) -> str:
    value = clean_text(text)
    value = re.sub(r"^(?:江山老师|蜗牛老师|报名|QQ|VX|淘宝|视频号|抖音|公众号).*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^第\s*\d+\s*页$", "", value)
    return value.strip()


def is_quality_title(title: str) -> bool:
    value = clean_text(title).strip("。:：,，;；")
    if len(value) < 2 or len(value) > 90:
        return False
    if re.search(r"[_%$@#=<>\\/\[\]{}^|]{1,}", value):
        return False
    if re.search(r"(报名|QQ|VX|微信|公众号|淘宝|老师|资料库|免费|页|关注|获取|woniu|taobao)", value, re.I):
        return False
    if not any(hint in value for hint in DOMAIN_HINTS):
        return False
    chinese_count = len(re.findall(r"[\u4e00-\u9fff]", value))
    if chinese_count >= 4:
        common_count = len(re.findall(r"[的一是在了和及或与对中为可有应能需管服信系规设过资数安风质项标准技人]", value))
        if common_count == 0:
            return False
    return True


def normalize_ocr_choice_letter(value: str) -> str | None:
    raw = value.strip().upper()
    mapping = {"召": "B", "曰": "B", "口": "D", "0": "D", "O": "D", "Ｃ": "C", "Ａ": "A", "Ｂ": "B", "Ｄ": "D"}
    if raw in CHOICES:
        return raw
    return mapping.get(raw)


def is_quality_mock_question(question: str, options: dict[str, str]) -> bool:
    q = clean_text(question)
    if len(q) < 10:
        return False
    if re.fullmatch(r"[\d\s第笫页,，.。:：()-]+", q):
        return False
    if re.search(r"(蜗牛老师|公众号|淘宝|第\s*\d+\s*页|ULOOSN|Laonao|O[sS]\s*$)", q, re.I):
        return False
    if not re.search(r"[\u4e00-\u9fff]", q):
        return False
    if not any(word in q for word in ("关于", "下列", "不属于", "正确", "错误", "活动", "管理", "规划", "服务", "信息", "系统", "项目", "风险", "质量", "技术", "数据", "安全", "能力")):
        return False
    if set(options) != set(CHOICES):
        return False
    quality_options = 0
    for option in options.values():
        value = clean_text(option)
        if len(value) < 2:
            return False
        if re.search(r"(蜗牛老师|公众号|淘宝|第\s*\d+\s*页|ULOOSN|Laonao)", value, re.I):
            return False
        if re.search(r"[\u4e00-\u9fff]|[A-Za-z]{2,}", value):
            quality_options += 1
    return quality_options >= 4


def clean_mock_question_text(question: str) -> str:
    value = clean_text(question)
    value = re.sub(r"^(?:\d{1,2}\s*\n)+", "", value)
    value = re.sub(r"^(?:第|笫)\s*\d+\s*页\s*", "", value)
    value = re.sub(r"^(?:\d{1,2}\s+)(?=[《\u4e00-\u9fff])", "", value)
    value = re.sub(r"\n(?:第|笫)\s*\d+\s*页.*$", "", value, flags=re.S)
    return value.strip()


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def read_material_text(row: dict[str, Any]) -> str:
    markdown = row.get("markdown")
    if not markdown:
        return ""
    path = ROOT / str(markdown)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def material_rows(kind: str | None = None) -> list[dict[str, Any]]:
    manifest = load_json(MANIFEST_FILE, {"files": []})
    rows = [row for row in manifest.get("files", []) if row.get("markdown")]
    if kind:
        rows = [row for row in rows if row.get("kind") == kind]
    return rows


def source_ref(row: dict[str, Any], page: str | None = None) -> str:
    markdown = row.get("markdown") or ""
    if page:
        return f"{markdown}#{page}"
    return markdown


def split_topic_blocks(text: str) -> list[tuple[str | None, str]]:
    blocks: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current: list[str] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line:
            continue
        heading_match = re.match(r"^##\s+(.+)$", line)
        if heading_match:
            if current:
                blocks.append((current_heading, "\n".join(current)))
                current = []
            current_heading = heading_match.group(1).strip()
            continue
        current.append(line)
    if current:
        blocks.append((current_heading, "\n".join(current)))
    return blocks


def extract_qa_cards(row: dict[str, Any], limit: int = 120) -> list[dict[str, Any]]:
    text = read_material_text(row)
    kind = str(row.get("kind") or "sprint")
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for heading, block in split_topic_blocks(text):
        lines = [clean_line(line) for line in block.splitlines()]
        compact_lines = [line for line in lines if line]
        for index, line in enumerate(compact_lines):
            if len(cards) >= limit:
                return cards
            match = re.match(r"^(?P<num>\d{1,3})[,.、，]?\s*(?P<title>[^:：]{2,80})[:：]\s*(?P<body>.+)$", line)
            if not match:
                continue
            title = clean_text(match.group("title")).strip("。:：,，")
            if not is_quality_title(title):
                continue
            body_parts = [clean_text(match.group("body"))]
            lookahead = index + 1
            while lookahead < len(compact_lines) and len("\n".join(body_parts)) < 700:
                next_line = compact_lines[lookahead]
                if re.match(r"^\d{1,3}[,.、，]?\s*[^:：]{2,80}[:：]", next_line):
                    break
                if next_line.startswith("(") or next_line.startswith("（") or re.match(r"^[①②③④⑤⑥⑦⑧⑨⑩(（\d]", next_line):
                    body_parts.append(next_line)
                lookahead += 1
            answer = clean_text("\n".join(body_parts))
            if len(answer) < 12 or len(title) < 2:
                continue
            fingerprint = f"{kind}|{title}|{answer[:80]}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            page = heading if heading and "第 " in heading else None
            cards.append(
                {
                    "id": stable_id("st_card", kind, title, answer[:120]),
                    "kind": kind,
                    "kind_label": KIND_LABELS.get(kind, kind),
                    "title": title,
                    "prompt": f"默写：{title}",
                    "answer": answer,
                    "training_type": "recall_card",
                    "difficulty": "medium",
                    "source": row.get("title"),
                    "source_ref": source_ref(row, page),
                    "note": "冲刺资料 OCR 训练卡，适合背诵和查漏补缺；不是历年真题。",
                }
            )
    return cards


def extract_numbered_cards(row: dict[str, Any], limit: int = 160) -> list[dict[str, Any]]:
    text = read_material_text(row)
    kind = str(row.get("kind") or "sprint")
    cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    pattern = re.compile(r"(?m)^(?P<num>\d{1,3})[,.、，]\s*(?P<body>.+?)(?=^\d{1,3}[,.、，]\s*|\Z)", re.S)
    for match in pattern.finditer(text):
        if len(cards) >= limit:
            break
        body = clean_text(match.group("body"))
        body = re.sub(r"^#+\s*", "", body)
        if len(body) < 25:
            continue
        title = body.split("\n", 1)[0][:70].strip("。:：")
        if len(title) < 4 or not is_quality_title(title):
            continue
        fingerprint = f"{kind}|{title}|{body[:80]}"
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        cards.append(
            {
                "id": stable_id("st_card", kind, str(match.group("num")), body[:120]),
                "kind": kind,
                "kind_label": KIND_LABELS.get(kind, kind),
                "title": title,
                "prompt": f"默写/复述：{title}",
                "answer": body[:1200],
                "training_type": "recall_card",
                "difficulty": "medium",
                "source": row.get("title"),
                "source_ref": source_ref(row),
                "note": "冲刺资料 OCR 训练卡，适合背诵和查漏补缺；不是历年真题。",
            }
        )
    return cards


def parse_mock_question_blocks(text: str) -> list[dict[str, Any]]:
    normalized = clean_text(text)
    pattern = re.compile(
        r"(?:\(|（)?(?:第|笫)\s*(?P<num>\d{1,2})\s*题(?:\)|）)?(?P<body>.*?)(?=(?:\(|（)?(?:第|笫)\s*\d{1,2}\s*题|\Z)",
        re.S,
    )
    blocks: list[dict[str, Any]] = []
    for match in pattern.finditer(normalized):
        body = match.group("body").strip()
        if len(body) < 40:
            continue
        blocks.append({"number": int(match.group("num")), "body": body})
    return blocks


def parse_mock_choice(row: dict[str, Any], block: dict[str, Any]) -> dict[str, Any] | None:
    number = int(block["number"])
    body = block["body"]
    answer_match = re.search(r"(?:答案|案)\s*[1lI]?\s*[:：]?\s*([A-D召曰口0O])", body, re.I)
    if not answer_match:
        return None
    answer = normalize_ocr_choice_letter(answer_match.group(1))
    if not answer:
        return None
    before_answer = body[: answer_match.start()]
    after_answer = body[answer_match.end() :]
    explanation = clean_text(re.sub(r"^(?:蜗牛解析|解析)[)）:：\s]*", "", after_answer, flags=re.I))[:600]
    option_matches = list(re.finditer(r"(?m)^\s*([A-D召曰口0O])\s*[.。:：、]?\s*(.+)", before_answer))
    if len(option_matches) < 4:
        option_matches = list(re.finditer(r"([A-D召曰口0O])\s*[.。:：、]\s*([^A-D召曰口0O]{2,120})", before_answer))
    options: dict[str, str] = {}
    for idx, option_match in enumerate(option_matches):
        letter = normalize_ocr_choice_letter(option_match.group(1))
        if not letter or letter in options:
            continue
        start = option_match.end(1)
        end = option_matches[idx + 1].start() if idx + 1 < len(option_matches) else len(before_answer)
        option_text = clean_text(before_answer[start:end])
        option_text = re.sub(r"^[.。:：、\s]+", "", option_text)
        option_text = option_text.split("\n")[0].strip()
        if len(option_text) >= 2:
            options[letter] = option_text[:180]
    if len(options) < 4:
        return None
    question_part = before_answer[: option_matches[0].start()]
    question_part = re.sub(r"^(?:蜗牛老师自编模拟题|['’]蜗牛老师自编模拟题[)）]?)", "", question_part).strip()
    question = clean_mock_question_text(question_part)
    question = re.sub(r"^[)）\s:：]+", "", question)
    if not is_quality_mock_question(question, options):
        return None
    option_rows = [f"{letter}. {options[letter]}" for letter in CHOICES]
    return {
        "id": f"st_mock_q{number:02d}",
        "kind": "mock-exam",
        "kind_label": KIND_LABELS["mock-exam"],
        "chapter": "冲刺模拟题",
        "question": question[:500],
        "options": option_rows,
        "answer": answer,
        "explanation": explanation or "解析来源于冲刺综合模考 OCR 文本；如有疑问以原 PDF 为准。",
        "question_type": "single_choice",
        "difficulty": "medium",
        "section": "24年11月系规综合模考题-第1套",
        "knowledge_point": "冲刺综合模考",
        "source": "sprint_training",
        "source_ref": source_ref(row),
        "tags": ["冲刺资料", "模拟题", "候选题源"],
        "note": "自编综合模考候选题，不是历年真题。",
    }


def extract_mock_questions(row: dict[str, Any]) -> list[dict[str, Any]]:
    text = read_material_text(row)
    questions: list[dict[str, Any]] = []
    seen_numbers: set[int] = set()
    for block in parse_mock_question_blocks(text):
        if block["number"] in seen_numbers:
            continue
        question = parse_mock_choice(row, block)
        if question:
            questions.append(question)
            seen_numbers.add(block["number"])
    return questions


def extract_case_prompts(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {kind: [] for kind in ("csf-risk", "activities", "gold-points", "sprint-guide")}
    for card in cards:
        if card.get("kind") not in {"csf-risk", "gold-points", "activities", "sprint-guide"}:
            continue
        title = str(card.get("title") or "")
        answer = str(card.get("answer") or "")
        if not any(word in title + answer for word in ("关键成功因素", "风险", "活动", "服务", "管理", "规划", "案例", "论文")):
            continue
        prompt = (
            {
                "id": stable_id("st_case", str(card.get("id")), title),
                "kind": card.get("kind"),
                "kind_label": card.get("kind_label"),
                "title": title,
                "prompt": f"按案例分析题方式分点回答：{title}",
                "answer": answer,
                "training_type": "case_points",
                "score": 10,
                "source": card.get("source"),
                "source_ref": card.get("source_ref"),
                "note": "冲刺资料采分点训练，适合案例/论文素材补充；不是历年真题。",
            }
        )
        grouped.setdefault(str(card.get("kind")), []).append(prompt)

    prompts: list[dict[str, Any]] = []
    per_kind_limit = {"csf-risk": 60, "activities": 60, "gold-points": 60, "sprint-guide": 60}
    for kind in ("csf-risk", "activities", "gold-points", "sprint-guide"):
        prompts.extend(grouped.get(kind, [])[: per_kind_limit[kind]])
    return prompts


def build_training() -> dict[str, Any]:
    rows = material_rows()
    cards: list[dict[str, Any]] = []
    choice_questions: list[dict[str, Any]] = []
    for row in rows:
        kind = row.get("kind")
        if kind == "mock-exam":
            choice_questions.extend(extract_mock_questions(row))
            cards.extend(extract_numbered_cards(row, limit=40))
        elif kind in {"activities", "csf-risk"}:
            cards.extend(extract_numbered_cards(row, limit=160))
            cards.extend(extract_qa_cards(row, limit=60))
        elif kind in {"mnemonic", "gold-points", "sprint-guide"}:
            cards.extend(extract_qa_cards(row, limit=160))
            cards.extend(extract_numbered_cards(row, limit=80))
    deduped_cards: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in cards:
        key = f"{card.get('kind')}|{card.get('title')}|{str(card.get('answer'))[:80]}"
        if key in seen:
            continue
        seen.add(key)
        deduped_cards.append(card)
    case_prompts = extract_case_prompts(deduped_cards)
    kind_counts = Counter(card.get("kind") for card in deduped_cards)
    return {
        "schema_version": 1,
        "source": rel(MANIFEST_FILE),
        "generated_by": "scripts/build_sprint_training.py",
        "note": "冲刺资料训练库来自 OCR/抽取文本，是背诵卡、案例采分点和自编模拟候选题源；不等同正式题库或历年真题。",
        "stats": {
            "cards": len(deduped_cards),
            "choice_questions": len(choice_questions),
            "case_prompts": len(case_prompts),
            "kind_counts": dict(sorted(kind_counts.items())),
        },
        "cards": deduped_cards,
        "choice_questions": choice_questions,
        "case_prompts": case_prompts,
    }


def render_index(training: dict[str, Any]) -> str:
    stats = training.get("stats") or {}
    lines = [
        "# 冲刺资料训练化索引",
        "",
        "> 说明：本库来自冲刺资料 OCR/抽取文本，只作为背诵卡、案例采分点和模拟候选题源，不是历年真题，不自动混入正式章节题库。",
        "",
        "## 总览",
        "",
        f"- 背诵卡：{stats.get('cards', 0)}",
        f"- 模拟选择候选题：{stats.get('choice_questions', 0)}",
        f"- 案例采分点训练：{stats.get('case_prompts', 0)}",
        f"- 输出：`{OUTPUT_FILE.relative_to(ROOT)}`",
        "",
        "## 类型分布",
    ]
    for kind, count in (stats.get("kind_counts") or {}).items():
        lines.append(f"- {KIND_LABELS.get(kind, kind)}：{count}")
    lines.extend(["", "## 使用方式", ""])
    lines.append("- `python scripts/study.py sprint-training cards --kind activities --count 5 --format markdown`")
    lines.append("- `python scripts/study.py sprint-training start --count 5 --format markdown`")
    lines.append("- `python scripts/study.py sprint-training case --kind csf-risk --count 3 --format markdown`")
    return "\n".join(lines) + "\n"


def sample_payload(training: dict[str, Any], kind: str | None, count: int, mode: str) -> dict[str, Any]:
    rows = list(training.get(mode, []))
    if kind and kind != "all":
        rows = [row for row in rows if row.get("kind") == kind]
    selected = choose_questions(rows, count, seed=1)
    return {"available": len(rows), "items": selected}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build structured sprint training assets.")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--sample", choices=["cards", "choice_questions", "case_prompts"], default=None)
    parser.add_argument("--kind", default=None)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
    args = parser.parse_args()

    training = build_training()
    if args.write:
        save_json(OUTPUT_FILE, training)
        INDEX_FILE.write_text(render_index(training), encoding="utf-8")
    output: Any = training
    if args.sample:
        output = sample_payload(training, args.kind, args.count, args.sample)
    if args.format == "json":
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.sample:
        print(f"# 冲刺训练样例\n\n- 可用：{output['available']}\n")
        for item in output["items"]:
            print(f"## {item.get('title') or item.get('id')}")
            print(item.get("prompt") or item.get("question"))
            print("")
    else:
        print(render_index(training))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
