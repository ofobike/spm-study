from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from pathlib import Path
from typing import Any

from study_modules.common import compact_text
from study_modules.materials import load_paper_special_index
from study_modules.settings import DEFAULT_PAPER_TOPIC, PAPER_RUBRIC, PAPER_SPECIAL_INDEX, PAPER_TOPICS, resolve_paper_topic
from study_utils import ROOT, chapter_no_from_label, load_all_questions, load_progress, now_iso, save_json


def select_paper_samples(index: dict[str, Any], topic: str | None = None, scenario: str | None = None) -> list[dict[str, Any]]:
    samples = list(index.get("samples") or [])
    if topic:
        direct = [sample for sample in samples if str(sample.get("topic") or "") == topic]
        if direct:
            samples = direct
    if scenario:
        scenario_text = str(scenario).strip()
        filtered = [
            sample
            for sample in samples
            if scenario_text
            and (
                scenario_text in str(sample.get("scenario") or "")
                or scenario_text in str(sample.get("best_for") or "")
            )
        ]
        if filtered:
            samples = filtered
    return samples[:3]


def paper_internal_references(topic: str | None = None, scenario: str | None = None) -> dict[str, Any]:
    index = load_paper_special_index()
    documents = list(index.get("documents") or [])
    guidance = next((item for item in documents if item.get("type") == "guidance"), None)
    framework_doc = next((item for item in documents if item.get("type") == "framework"), None)
    samples = select_paper_samples(index, topic=topic, scenario=scenario)
    has_direct_sample = any(str(sample.get("topic") or "") == topic for sample in samples) if topic else False
    return {
        "status": index.get("status"),
        "index_file": str(PAPER_SPECIAL_INDEX.relative_to(ROOT)),
        "guidance": guidance,
        "framework_document": framework_doc,
        "rubric": index.get("rubric") or {},
        "framework": index.get("framework") or {},
        "samples": samples,
        "sample_note": None if has_direct_sample else "暂无该主题专属范文，当前范文主要用于借鉴结构、叙事密度和量化表达。",
    }


def build_paper_reference_payload(args: argparse.Namespace) -> dict[str, Any]:
    resolved = resolve_paper_topic(getattr(args, "topic", None))
    topic = resolved[0] if resolved else (getattr(args, "topic", None) or DEFAULT_PAPER_TOPIC)
    return {
        "topic": topic,
        "scenario": getattr(args, "scenario", None),
        "internal_references": paper_internal_references(topic, getattr(args, "scenario", None)),
    }


def render_internal_paper_reference_lines(internal_references: dict[str, Any]) -> list[str]:
    if not internal_references:
        return ["- 暂未发现内部论文专题索引。"]
    rubric = internal_references.get("rubric") or {}
    framework = internal_references.get("framework") or {}
    guidance = internal_references.get("guidance") or {}
    framework_document = internal_references.get("framework_document") or {}
    dimensions = rubric.get("dimensions") or []
    lines = [f"- 索引：{internal_references.get('index_file')}"]
    if guidance.get("markdown"):
        lines.append(f"- 评分与避坑：{guidance['markdown']}")
    if framework_document.get("markdown"):
        lines.append(f"- 框架与格式：{framework_document['markdown']}")
    if dimensions:
        dim_text = "、".join(f"{item.get('name')} {item.get('weight')}%" for item in dimensions)
        lines.append(f"- 五维评分：{dim_text}")
    if framework:
        abstract = (framework.get("abstract") or {}).get("target_chars")
        body = (framework.get("body") or {}).get("target_chars")
        role_logic = framework.get("role_logic")
        detail = []
        if role_logic:
            detail.append(str(role_logic))
        if abstract:
            detail.append(f"摘要{abstract}字")
        if body:
            detail.append(f"正文{body}字")
        if detail:
            lines.append(f"- 写作框架：{'；'.join(detail)}")
    samples = internal_references.get("samples") or []
    if samples:
        if internal_references.get("sample_note"):
            lines.append(f"- 范文说明：{internal_references['sample_note']}")
        for sample in samples:
            lines.append(f"- 范文参考：{sample.get('scenario')} - {sample.get('markdown')}（{sample.get('best_for')}）")
    return lines


def render_paper_reference_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 内部论文专题参考",
        "",
        f"- 主题：{payload['topic']}",
        f"- 场景：{payload['scenario'] or '未指定'}",
        "",
    ]
    lines.extend(render_internal_paper_reference_lines(payload.get("internal_references") or {}))
    refs = payload.get("internal_references") or {}
    rubric = refs.get("rubric") or {}
    deductions = rubric.get("deductions") or []
    fatal_risks = rubric.get("fatal_risks") or []
    if deductions:
        lines.extend(["", "## 常见扣分风险"])
        lines.extend(f"- {item}" for item in deductions)
    if fatal_risks:
        lines.extend(["", "## 不及格高风险"])
        lines.extend(f"- {item}" for item in fatal_risks)
    return "\n".join(lines) + "\n"


def command_paper_reference(args: argparse.Namespace) -> int:
    payload = build_paper_reference_payload(args)
    if args.format == "markdown":
        print(render_paper_reference_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def chapter_questions(chapter_no: int) -> list[dict[str, Any]]:
    _, _, by_chapter = load_all_questions()
    return by_chapter.get(chapter_no, [])


def is_weak_paper_knowledge_point(point: str) -> bool:
    text = str(point or "").strip()
    if len(text) < 3:
        return True
    return any(
        re.compile(pattern).match(text)
        for pattern in (
            r"^第\d+章",
            r"^\d+(\.\d+)*$",
            r"^章节",
            r"^选择题",
            r"^案例",
            r"^综合",
        )
    )


def top_knowledge_points_for_chapter(chapter_no: int, limit: int = 12) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    sections: dict[str, Counter[str]] = {}
    for question in chapter_questions(chapter_no):
        point = str(question.get("knowledge_point") or "").strip()
        if not point:
            continue
        counter[point] += 1
        section = str(question.get("section") or "").strip()
        if section:
            sections.setdefault(point, Counter())[section] += 1
    rows = []
    for point, count in counter.most_common():
        if is_weak_paper_knowledge_point(point):
            continue
        section = sections.get(point, Counter()).most_common(1)
        rows.append({"knowledge_point": point, "question_count": count, "section": section[0][0] if section else None})
        if len(rows) >= limit:
            break
    return rows


def build_paper_payload(args: argparse.Namespace) -> dict[str, Any]:
    resolved = resolve_paper_topic(args.topic)
    if not resolved:
        return {
            "error": f"Unsupported paper topic: {args.topic}",
            "supported_topics": list(PAPER_TOPICS.keys()),
        }
    topic, data = resolved
    chapter = int(data["chapter"])
    metadata_points = top_knowledge_points_for_chapter(chapter, args.limit)
    knowledge_points = [
        {
            "knowledge_point": point,
            "section": "论文核心点",
            "question_count": next((row["question_count"] for row in metadata_points if row["knowledge_point"] in point or point in row["knowledge_point"]), 0),
        }
        for point in data.get("paper_points", [])
    ]
    seen_points = {row["knowledge_point"] for row in knowledge_points}
    for row in metadata_points:
        if row["knowledge_point"] not in seen_points and len(knowledge_points) < args.limit:
            knowledge_points.append(row)
            seen_points.add(row["knowledge_point"])
    title = f"论{topic}发展规划的组织实施与持续改进"
    return {
        "topic": topic,
        "chapter": f"第{chapter}章",
        "chapter_title": data["chapter_title"],
        "title": title,
        "scenario": data["scenario"],
        "abstract_outline": [
            "项目背景：说明组织所处环境、痛点和规划目标。",
            "规划方法：交代顶层设计、现状评估、需求分析和路线图设计。",
            "实施过程：围绕平台、数据、业务、治理、安全和组织保障展开。",
            "实施效果：用管理效率、服务质量、成本收益、风险控制等指标收束。",
        ],
        "body_structure": [
            {"section": "一、项目背景与规划目标", "points": ["业务痛点", "外部政策或行业趋势", "建设边界", "可量化目标"]},
            {"section": "二、现状评估与总体架构", "points": ["业务现状", "数据与系统现状", "能力差距", "总体架构和路线图"]},
            {"section": "三、关键能力建设与实施路径", "points": data["focus"]},
            {"section": "四、治理、安全与持续改进", "points": ["组织机制", "标准规范", "安全合规", "绩效评价", "迭代优化"]},
            {"section": "五、效果总结与经验反思", "points": ["效果指标", "风险处置", "经验沉淀", "后续计划"]},
        ],
        "knowledge_points": knowledge_points,
        "internal_references": paper_internal_references(topic),
        "common_deductions": [
            "只写技术堆砌，没有规划目标、治理机制和实施路径。",
            "项目背景过泛，缺少业务痛点、边界和角色职责。",
            "章节知识点没有落到案例场景，像教材摘要而不是项目论文。",
            "缺少量化效果、风险控制、安全合规和持续改进。",
            "结构不完整，摘要、正文和总结之间没有因果闭环。",
        ],
        "self_check": [
            "是否明确写出项目背景、建设目标和本人职责。",
            "是否覆盖总体规划、现状评估、路线图、资源保障和治理机制。",
            "是否至少使用3个本章核心知识点，并结合具体场景展开。",
            "是否给出可衡量效果，而不是只写“效果良好”。",
            "是否留下风险、问题和改进措施，形成闭环。",
        ],
        "next_step": f"写一版800-1200字草稿后，让助手按自评清单逐段点评；也可先练：python scripts/study.py start --chapters {chapter} --count 5 --format markdown",
    }


def render_paper_markdown(payload: dict[str, Any]) -> str:
    if payload.get("error"):
        topics = "、".join(payload.get("supported_topics", []))
        return f"{payload['error']}\nSupported topics: {topics}\n"
    lines = [
        f"# {payload['title']}",
        "",
        f"- 主题：{payload['topic']}（{payload['chapter']} {payload['chapter_title']}）",
        f"- 场景：{payload['scenario']}",
        "",
        "## 摘要框架",
    ]
    lines.extend(f"- {item}" for item in payload["abstract_outline"])
    lines.append("")
    lines.append("## 正文结构")
    for block in payload["body_structure"]:
        lines.append(f"- {block['section']}：{'、'.join(block['points'])}")
    lines.append("")
    lines.append("## 可用知识点")
    for row in payload["knowledge_points"]:
        if row.get("question_count"):
            suffix = f"（{row['section']}，题库出现{row['question_count']}次）" if row.get("section") else f"（题库出现{row['question_count']}次）"
        else:
            suffix = f"（{row['section']}）" if row.get("section") else ""
        lines.append(f"- {row['knowledge_point']}{suffix}")
    lines.append("")
    lines.append("## 内部论文专题参考")
    lines.extend(render_internal_paper_reference_lines(payload.get("internal_references") or {}))
    lines.append("")
    lines.append("## 常见扣分点")
    lines.extend(f"- {item}" for item in payload["common_deductions"])
    lines.append("")
    lines.append("## 自评清单")
    lines.extend(f"- {item}" for item in payload["self_check"])
    lines.append("")
    lines.append(f"Next: {payload['next_step']}")
    return "\n".join(lines) + "\n"


def normalize_text(text: str) -> str:
    return compact_text(text)


def read_text_file(path_text: str) -> str:
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    return path.read_text(encoding="utf-8")


def score_keyword_group(text: str, keywords: list[str], max_score: int) -> tuple[int, list[str], list[str]]:
    normalized = normalize_text(text)
    matched = [keyword for keyword in keywords if keyword and keyword in normalized]
    missing = [keyword for keyword in keywords if keyword and keyword not in normalized]
    ratio = len(matched) / len(keywords) if keywords else 0
    return round(max_score * ratio), matched, missing


def record_paper_attempt(payload: dict[str, Any], record: bool = True) -> dict[str, Any]:
    progress = load_progress()
    attempts = progress.setdefault("paper_attempts", []) if record else list(progress.get("paper_attempts", []))
    previous = next((attempt for attempt in reversed(attempts) if attempt.get("topic") == payload["topic"]), None)
    submitted_at = now_iso()
    attempt = {
        "topic": payload["topic"],
        "chapter": payload["chapter"],
        "submitted_at": submitted_at,
        "attempt_no": sum(1 for item in attempts if item.get("topic") == payload["topic"]) + 1,
        "score": payload["score"],
        "word_count": payload["word_count"],
        "dimension_scores": {row["key"]: row["score"] for row in payload["dimensions"]},
    }
    if previous:
        attempt["delta_score"] = payload["score"] - int(previous.get("score", 0))
        payload["improvement"] = {
            "previous_score": previous.get("score"),
            "current_score": payload["score"],
            "delta_score": attempt["delta_score"],
            "previous_word_count": previous.get("word_count"),
            "current_word_count": payload["word_count"],
        }
    if record:
        attempts.append(attempt)
        progress["last_updated"] = submitted_at
        save_json(ROOT / "assets" / "questions" / "progress.json", progress)
    payload["recorded"] = record
    payload["attempt_no"] = attempt["attempt_no"]
    return payload


def build_paper_review_payload(args: argparse.Namespace) -> dict[str, Any]:
    resolved = resolve_paper_topic(args.topic)
    if not resolved:
        return {"error": f"Unsupported paper topic: {args.topic}", "supported_topics": list(PAPER_TOPICS.keys())}
    topic, topic_data = resolved
    if args.text is None and args.draft is None:
        return {"error": "paper submit requires --draft <file> or --text <draft text>"}
    draft = args.text if args.text is not None else read_text_file(args.draft)
    clean = normalize_text(draft)
    word_count = len(clean)
    topic_points = list(topic_data.get("paper_points", []))
    focus_points = list(topic_data.get("focus", []))
    checks = {
        "abstract": ["摘要", "背景", "目标", "效果"],
        "background": ["项目", "背景", "职责", "痛点", "目标"],
        "planning": ["规划", "架构", "现状", "需求", "路线图"],
        "implementation": ["实施", "数据", "平台", "治理", "安全", "组织"],
        "domain": topic_points + focus_points,
        "outcome": ["效果", "指标", "效率", "质量", "风险", "改进"],
    }
    dimensions = []
    total_score = 0
    for key, label, max_score in PAPER_RUBRIC:
        score, matched, missing = score_keyword_group(clean, checks[key], max_score)
        dimensions.append({"key": key, "label": label, "score": score, "max_score": max_score, "matched": matched, "missing": missing[:8]})
        total_score += score
    if word_count < args.min_chars:
        penalty = min(15, round((args.min_chars - word_count) / args.min_chars * 15))
        total_score = max(0, total_score - penalty)
    else:
        penalty = 0
    issues = []
    for row in dimensions:
        if row["score"] < row["max_score"] * 0.6:
            issues.append(f"{row['label']}展开不足，缺少：{'、'.join(row['missing'][:4])}")
    if penalty:
        issues.append(f"篇幅偏短，当前约 {word_count} 字符，建议不少于 {args.min_chars} 字符。")
    if not re.search(r"\d+|%|％|天|月|年|万元|人次|次", draft):
        issues.append("缺少量化效果或指标，建议补充效率、质量、成本、周期、风险等数据。")
    strengths = [row["label"] for row in dimensions if row["score"] >= row["max_score"] * 0.8]
    rewrite_plan = [
        "先补项目背景、本人角色、建设边界和可量化目标。",
        "再把总体架构、数据治理、平台建设、组织保障和安全合规串成实施路径。",
        "最后用效果指标、风险处置和持续改进收束，避免只写口号。",
    ]
    payload = {
        "topic": topic,
        "chapter": f"第{topic_data['chapter']}章",
        "word_count": word_count,
        "score": min(100, total_score),
        "exam_score_estimate": round(min(100, total_score) * 0.75, 1),
        "penalty": penalty,
        "dimensions": dimensions,
        "strengths": strengths,
        "issues": issues,
        "rewrite_plan": rewrite_plan,
        "internal_references": paper_internal_references(topic),
        "next_step": f"按问题清单改一版后再次提交：python scripts/study.py paper submit --topic {topic} --draft <draft.md> --format markdown",
    }
    return record_paper_attempt(payload, record=not getattr(args, "no_record", False))


def render_paper_review_markdown(payload: dict[str, Any]) -> str:
    if payload.get("error"):
        topics = payload.get("supported_topics")
        suffix = f"\nSupported topics: {'、'.join(topics)}" if topics else ""
        return f"{payload['error']}{suffix}\n"
    lines = [
        f"# 论文评分反馈：{payload['topic']}",
        "",
        f"- 章节：{payload['chapter']}",
        f"- 篇幅：约 {payload['word_count']} 字符",
        f"- 总分：{payload['score']}/100",
        f"- 75分制估算：{payload.get('exam_score_estimate')}/75",
        f"- 记录写入：{'是' if payload.get('recorded', True) else '否'}",
        f"- 轮次：第 {payload.get('attempt_no', 1)} 稿",
    ]
    if payload.get("penalty"):
        lines.append(f"- 篇幅扣分：{payload['penalty']}")
    if payload.get("improvement"):
        improvement = payload["improvement"]
        lines.append(f"- 较上一稿：{improvement['delta_score']} 分，篇幅 {improvement['previous_word_count']} -> {improvement['current_word_count']} 字符")
    lines.extend(["", "## 维度评分"])
    for row in payload["dimensions"]:
        lines.append(f"- {row['label']}: {row['score']}/{row['max_score']}")
        if row["missing"]:
            lines.append(f"  缺少：{'、'.join(row['missing'])}")
    lines.append("")
    lines.append("## 内部五维评分参考")
    lines.append("- 当前自动评分用于训练闭环；人工复评时按内部资料五维标准再校准。")
    refs = payload.get("internal_references") or {}
    rubric = refs.get("rubric") or {}
    for row in rubric.get("dimensions") or []:
        checkpoints = row.get("checkpoints") or []
        suffix = f"：{'、'.join(checkpoints[:3])}" if checkpoints else ""
        lines.append(f"- {row.get('name')} {row.get('weight')}%{suffix}")
    if refs.get("guidance", {}).get("markdown"):
        lines.append(f"- 评分来源：{refs['guidance']['markdown']}")
    lines.append("")
    lines.append("## 主要优点")
    if payload["strengths"]:
        lines.extend(f"- {item}" for item in payload["strengths"])
    else:
        lines.append("- 暂无明显高分维度，建议先补完整结构。")
    lines.append("")
    lines.append("## 优先修改")
    if payload["issues"]:
        lines.extend(f"- {item}" for item in payload["issues"])
    else:
        lines.append("- 结构较完整，可继续打磨表达和案例细节。")
    lines.append("")
    lines.append("## 改写路径")
    lines.extend(f"- {item}" for item in payload["rewrite_plan"])
    lines.append("")
    lines.append(f"Next: {payload['next_step']}")
    return "\n".join(lines) + "\n"


def command_paper(args: argparse.Namespace) -> int:
    payload = build_paper_payload(args)
    if args.format == "markdown":
        print(render_paper_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload.get("error") else 0


def command_paper_submit(args: argparse.Namespace) -> int:
    payload = build_paper_review_payload(args)
    if args.format == "markdown":
        print(render_paper_review_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload.get("error") else 0
