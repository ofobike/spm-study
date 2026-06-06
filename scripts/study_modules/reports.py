from __future__ import annotations

import argparse
from collections import Counter
import json
from typing import Any

from study_utils import (
    chapter_no_from_label,
    load_all_questions,
    load_archive,
    load_config,
    load_progress,
    today,
)

from study_modules.common import display_command, due_review_items, simplify_json
from study_modules.materials import (
    build_exam_guide_payload,
    case_range_chapters_text,
    chapter_guide_row,
    exam_focus_chapters,
    load_syllabus_analysis,
    paper_range_chapters,
)
from study_modules.mastery import (
    build_coverage_payload,
    build_mastery_payload,
    chapter_command_for_point,
)
from study_modules.profile import (
    load_learner_profile,
    profile_case_count,
    profile_dynamic_insights,
    profile_dynamic_weak_subject_names,
    profile_has_weak_subject,
    profile_practice_count,
    profile_summary,
    profile_weak_chapters,
)
from study_modules.quality import build_audit_payload
from study_modules.settings import DEFAULT_PAPER_TOPIC


def due_items(limit: int, review_date_text: str | None = None) -> list[dict[str, Any]]:
    return due_review_items(limit, review_date_text)


def weakness_rows(limit: int) -> list[dict[str, Any]]:
    config = load_config()
    ability_chapters = set(config.get("ability_chapters", []))
    ability_weight = float(config.get("ability_weight", 1.5))
    progress = load_progress()
    archive = load_archive()
    by_chapter_progress = progress.get("stats", {}).get("by_chapter", {})
    by_chapter_archive = archive.get("stats", {}).get("by_chapter", {})
    rows = []
    for chapter_no in range(1, int(config.get("chapter_count", 24)) + 1):
        chapter = f"第{chapter_no}章"
        answered = int(by_chapter_progress.get(chapter, {}).get("answered", 0))
        correct = int(by_chapter_progress.get(chapter, {}).get("correct", 0))
        wrong_attempts = int(by_chapter_archive.get(chapter, {}).get("wrong_attempts", 0))
        weight = ability_weight if chapter_no in ability_chapters else 1.0
        accuracy = round(correct / answered, 4) if answered else None
        priority = (((1 - accuracy) * max(answered, 1)) if accuracy is not None else 0) + wrong_attempts
        rows.append(
            {
                "chapter": chapter,
                "answered": answered,
                "accuracy": accuracy,
                "wrong_attempts": wrong_attempts,
                "priority": round(priority * weight, 4),
            }
        )
    rows.sort(key=lambda item: item["priority"], reverse=True)
    return [row for row in rows if row["priority"] > 0][:limit]


def next_action(total_answered: int, due: list[dict[str, Any]], weak_rows: list[dict[str, Any]]) -> str:
    if due:
        return "先复习到期错题：python scripts/study.py review --format markdown"
    if weak_rows:
        chapter = weak_rows[0]["chapter"].replace("第", "").replace("章", "")
        return f"针对薄弱章节练习：python scripts/study.py start --chapters {chapter} --count 5 --format markdown"
    if total_answered == 0:
        return "从核心章节开始：python scripts/study.py start --chapters 12 --count 5 --format markdown"
    return "生成今日学习计划：python scripts/study.py plan --format markdown"


def command_status(args: argparse.Namespace) -> int:
    progress = load_progress()
    archive = load_archive()
    stats = progress.get("stats", {})
    total = int(stats.get("total_answered", 0))
    correct = int(stats.get("total_correct", 0))
    accuracy = round((correct / total) * 100, 2) if total else None
    due = due_items(args.limit)
    weak_rows = weakness_rows(args.limit)
    payload = {
        "answered": total,
        "correct": correct,
        "accuracy_percent": accuracy,
        "wrong_items": len(archive.get("archive", [])),
        "due_review_count": len(due),
        "weak_chapters": weak_rows,
        "next_action": next_action(total, due, weak_rows),
    }
    if args.format == "markdown":
        print(f"Answered: {total}, correct: {correct}, accuracy: {accuracy if accuracy is not None else '-'}%")
        print(f"Wrong items: {payload['wrong_items']}, due review: {len(due)}")
        print(f"Next: {payload['next_action']}")
        if weak_rows:
            print("\nWeak chapters:")
            for row in weak_rows:
                print(f"- {row['chapter']}: priority={row['priority']}, accuracy={row['accuracy']}, wrong_attempts={row['wrong_attempts']}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_plan_payload(args: argparse.Namespace) -> dict[str, Any]:
    profile = load_learner_profile()
    profile_info = profile_summary(profile)
    insights = profile_dynamic_insights(profile)
    dynamic_subjects = profile_dynamic_weak_subject_names(insights)
    practice_count = args.practice_count if args.practice_count != 5 else profile_practice_count(profile, args.practice_count)
    daily_minutes = profile_info["daily_minutes"]
    task_budget = 2 if daily_minutes < 45 else 4 if daily_minutes < 90 else 6
    due = due_items(args.review_limit)
    weak = weakness_rows(args.weak_limit)
    progress = load_progress()
    answered = int(progress.get("stats", {}).get("total_answered", 0))
    focus_chapters = exam_focus_chapters()
    tasks: list[dict[str, Any]] = []
    task_keys: set[str] = set()

    def add_task(task: dict[str, Any]) -> None:
        key = str(task.get("command"))
        if key in task_keys:
            return
        task_keys.add(key)
        tasks.append(task)

    if due:
        add_task(
            {
                "priority": 1,
                "type": "review",
                "title": "复习到期错题",
                "count": min(len(due), args.review_limit),
                "unit": "题",
                "command": "python scripts/study.py review --format markdown",
            }
        )

    if weak:
        for row in weak[:2]:
            chapter_no = row["chapter"].replace("第", "").replace("章", "")
            add_task(
                {
                    "priority": 2,
                    "type": "weak_practice",
                    "title": f"{row['chapter']}薄弱巩固",
                    "count": practice_count,
                    "unit": "题",
                    "command": f"python scripts/study.py start --chapters {chapter_no} --count {practice_count} --format markdown",
                }
            )

    for row in insights.get("weak_knowledge_points", [])[:2]:
        add_task(
            {
                "priority": 2.05,
                "type": "dynamic_weak_point",
                "title": f"动态错题知识点：{row['knowledge_point']}",
                "count": practice_count,
                "unit": "题",
                "command": row["command"],
                "source": insights.get("source"),
            }
        )

    for row in insights.get("weak_chapters", [])[:2]:
        add_task(
            {
                "priority": 2.1,
                "type": "dynamic_weak_chapter",
                "title": f"动态薄弱章节巩固：{row['chapter']}",
                "count": practice_count,
                "unit": "题",
                "command": f"python scripts/study.py start --chapters {row['chapter_no']} --count {practice_count} --format markdown",
                "source": insights.get("source"),
            }
        )

    for chapter_no in profile_weak_chapters(profile)[:2]:
        guide_row = chapter_guide_row(chapter_no)
        add_task(
            {
                "priority": 2.2,
                "type": "profile_weak_chapter",
                "title": f"画像薄弱章节巩固：第{chapter_no}章" + (f" {guide_row['title']}" if guide_row else ""),
                "count": practice_count,
                "unit": "题",
                "command": f"python scripts/study.py start --chapters {chapter_no} --count {practice_count} --format markdown",
                "source": "assets/profile/learner_profile.json",
            }
        )

    if profile_has_weak_subject(profile, "案例", "主观题") or "案例分析" in dynamic_subjects:
        case_count = profile_case_count(profile)
        add_task(
            {
                "priority": 2.8 if "案例分析" in dynamic_subjects else 3,
                "type": "profile_case",
                "title": "案例分析采分点训练",
                "count": case_count,
                "unit": "个",
                "command": f"python scripts/study.py case start --chapters {case_range_chapters_text()} --count {case_count} --format markdown",
                "source": insights.get("source") if "案例分析" in dynamic_subjects else "assets/profile/learner_profile.json",
            }
        )

    if profile_has_weak_subject(profile, "论文", "作文") or "论文" in dynamic_subjects:
        add_task(
            {
                "priority": 2.9 if "论文" in dynamic_subjects else 4,
                "type": "profile_paper",
                "title": "论文框架训练",
                "count": 1,
                "unit": "篇",
                "command": f"python scripts/study.py paper --topic {DEFAULT_PAPER_TOPIC} --format markdown",
                "source": insights.get("source") if "论文" in dynamic_subjects else "assets/profile/learner_profile.json",
            }
        )

    if profile_has_weak_subject(profile, "综合", "上午", "选择"):
        chapters_text = ",".join(str(chapter) for chapter in focus_chapters[:3])
        add_task(
            {
                "priority": 5,
                "type": "profile_comprehensive",
                "title": "综合知识高频章节训练",
                "count": practice_count,
                "unit": "题",
                "command": f"python scripts/study.py start --chapters {chapters_text} --count {practice_count} --format markdown",
                "source": "assets/profile/learner_profile.json",
            }
        )

    if not tasks:
        default_chapter = args.default_chapter if answered else (focus_chapters[0] if focus_chapters else 12)
        guide_row = chapter_guide_row(default_chapter)
        add_task(
            {
                "priority": 6,
                "type": "new_practice",
                "title": f"第{default_chapter}章核心练习" + (f"：{guide_row['title']}" if guide_row else ""),
                "count": practice_count,
                "unit": "题",
                "command": f"python scripts/study.py start --chapters {default_chapter} --count {practice_count} --format markdown",
                "source": "references/internal/guide/exam-guide.json",
            }
        )
    if answered < 50 and not due:
        chapters_text = ",".join(str(chapter) for chapter in focus_chapters[:3])
        add_task(
            {
                "priority": 6.5,
                "type": "exam_focus",
                "title": "新版大纲高优先级章节起步",
                "count": practice_count,
                "unit": "题",
                "command": f"python scripts/study.py start --chapters {chapters_text} --count {practice_count} --format markdown",
                "source": "references/internal/syllabus/syllabus-analysis.json",
            }
        )

    if args.include_mock:
        add_task(
            {
                "priority": 8,
                "type": "mock_exam",
                "title": "综合知识模拟卷",
                "count": 75,
                "unit": "题",
                "command": "python scripts/study.py start --mode mock --format markdown",
            }
        )
    tasks = sorted(tasks, key=lambda item: item.get("priority", 99))[:task_budget]

    return {
        "date": today().isoformat(),
        "answered": answered,
        "due_review_count": len(due),
        "focus_chapters": focus_chapters,
        "profile": profile_info,
        "dynamic_insights": insights,
        "practice_count": practice_count,
        "task_budget": task_budget,
        "tasks": tasks,
    }


def render_plan_markdown(payload: dict[str, Any]) -> str:
    insights = payload.get("dynamic_insights") or {}
    lines = [
        f"# 每日学习计划 {payload['date']}",
        "",
        f"- 已答题：{payload['answered']}",
        f"- 到期复习：{payload['due_review_count']}",
        f"- 新版大纲高优先级章节：{','.join(str(chapter) for chapter in payload['focus_chapters'])}",
        f"- 画像：每日 {payload['profile']['daily_minutes']} 分钟，{payload['profile']['study_load']}负荷，策略：{payload['profile'].get('strategy') or '待确认'}",
        f"- 今日自动题量：{payload['practice_count']} 题；任务上限：{payload['task_budget']} 项",
    ]
    if insights.get("weak_chapters") or insights.get("weak_knowledge_points") or insights.get("dynamic_weak_subjects"):
        recent = insights.get("recent_accuracy_percent") if insights.get("recent_accuracy_percent") is not None else "-"
        lines.append(f"- 动态校准：已答 {insights.get('choice_answered', 0)} 题，最近正确率 {recent}%，已参与今日任务排序")
    elif insights.get("calibration_gaps"):
        lines.append(f"- 动态校准：{'；'.join(insights['calibration_gaps'][:2])}")
    lines.extend(["", "## 今日任务"])
    for index, task in enumerate(payload["tasks"], start=1):
        lines.append(f"{index}. {task['title']} ({task['count']}{task.get('unit', '题')})")
        lines.append(f"   {display_command(task['command'])}")
    lines.append("")
    lines.append("画像入口：python scripts/study.py profile")
    return "\n".join(lines) + "\n"


def command_plan(args: argparse.Namespace) -> int:
    payload = build_plan_payload(args)
    if args.format == "markdown":
        print(render_plan_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_dashboard_payload(args: argparse.Namespace) -> dict[str, Any]:
    profile = load_learner_profile()
    profile_info = profile_summary(profile)
    insights = profile_dynamic_insights(profile)
    dynamic_subjects = profile_dynamic_weak_subject_names(insights)
    practice_count = profile_practice_count(profile)
    progress = load_progress()
    archive = load_archive()
    stats = progress.get("stats", {})
    total = int(stats.get("total_answered", 0))
    correct = int(stats.get("total_correct", 0))
    accuracy = round((correct / total) * 100, 2) if total else None
    due = due_items(args.limit)
    weak = weakness_rows(args.limit)
    coverage_args = argparse.Namespace(limit=args.limit, threshold=0.7, min_attempts=2)
    coverage = build_coverage_payload(coverage_args)
    mastery = build_mastery_payload(argparse.Namespace(limit=3, chapter=None))
    audit = build_audit_payload(argparse.Namespace(limit=5, min_explanation_length=30)) if args.include_audit else None
    guide = build_exam_guide_payload(argparse.Namespace(limit=5))
    focus_chapters = exam_focus_chapters()
    case_chapters = case_range_chapters_text()
    tasks = []
    task_keys: set[str] = set()

    def add_task(task: dict[str, Any]) -> None:
        key = str(task.get("command"))
        if key in task_keys:
            return
        task_keys.add(key)
        tasks.append(task)

    if due:
        add_task({"priority": 1, "type": "review", "title": "复习到期错题", "command": "python scripts/study.py review --format markdown"})
    if weak:
        chapter = weak[0]["chapter"].replace("第", "").replace("章", "")
        add_task({"priority": 2, "type": "weak_practice", "title": f"{weak[0]['chapter']}薄弱巩固", "command": f"python scripts/study.py start --chapters {chapter} --count {practice_count} --format markdown"})
    for row in insights.get("weak_knowledge_points", [])[:2]:
        add_task({"priority": 2.05, "type": "dynamic_weak_point", "title": f"动态错题知识点：{row['knowledge_point']}", "command": row["command"]})
    for row in insights.get("weak_chapters", [])[:2]:
        add_task({"priority": 2.1, "type": "dynamic_weak_chapter", "title": f"动态薄弱章节：{row['chapter']}", "command": f"python scripts/study.py start --chapters {row['chapter_no']} --count {practice_count} --format markdown"})
    for chapter in profile_weak_chapters(profile)[:2]:
        guide_row = chapter_guide_row(chapter)
        title = f"画像薄弱章节：第{chapter}章" + (f" {guide_row['title']}" if guide_row else "")
        add_task({"priority": 2.2, "type": "profile_weak_chapter", "title": title, "command": f"python scripts/study.py start --chapters {chapter} --count {practice_count} --format markdown"})
    if profile_has_weak_subject(profile, "案例", "主观题") or "案例分析" in dynamic_subjects:
        add_task({"priority": 2.8 if "案例分析" in dynamic_subjects else 3, "type": "profile_case", "title": "案例分析采分点训练", "command": f"python scripts/study.py case start --chapters {case_chapters} --count {profile_case_count(profile)} --format markdown"})
    if profile_has_weak_subject(profile, "论文", "作文") or "论文" in dynamic_subjects:
        add_task({"priority": 2.9 if "论文" in dynamic_subjects else 3.5, "type": "profile_paper", "title": "论文框架训练", "command": f"python scripts/study.py paper --topic {DEFAULT_PAPER_TOPIC} --format markdown"})
    for item in coverage.get("suggestions", [])[:2]:
        add_task({"priority": 3, "type": item["type"], "title": f"补练知识点：{item['knowledge_point']}", "command": item["command"]})
    for item in mastery.get("weak_points", [])[:2]:
        add_task({"priority": 3.5, "type": "mastery", "title": f"掌握度提升：{item['knowledge_point']}", "command": item["command"]})
    if not total:
        add_task({"priority": 2.5, "type": "exam_focus", "title": "新版大纲高优先级章节", "command": f"python scripts/study.py start --chapters {','.join(str(chapter) for chapter in focus_chapters[:3])} --count {practice_count} --format markdown"})
    add_task({"priority": 4, "type": "case", "title": "案例分析训练", "command": f"python scripts/study.py case start --chapters {case_chapters} --count 1 --format markdown"})
    add_task({"priority": 4.5, "type": "past_exam", "title": "历年真题选择训练", "command": f"python scripts/study.py past-exam start --count {practice_count} --format markdown"})
    add_task({"priority": 4.7, "type": "standards_training", "title": "标准规范专项训练", "command": f"python scripts/study.py standards start --count {practice_count} --format markdown"})
    add_task({"priority": 5, "type": "paper", "title": "论文训练", "command": f"python scripts/study.py paper --topic {DEFAULT_PAPER_TOPIC} --format markdown"})
    if audit and audit.get("issue_count"):
        add_task({"priority": 6, "type": "quality", "title": "题库质量修复预览", "command": "python scripts/study.py fix-quality --format markdown"})
    tasks = sorted(tasks, key=lambda item: item["priority"])[: args.limit]
    return {
        "date": today().isoformat(),
        "answered": total,
        "correct": correct,
        "accuracy_percent": accuracy,
        "wrong_items": len(archive.get("archive", [])),
        "due_review_count": len(due),
        "coverage_percent": coverage["coverage_percent"],
        "unpracticed_knowledge_points": coverage["unpracticed_knowledge_points"],
        "average_mastery_score": mastery["average_mastery_score"],
        "mastery_counts_by_level": mastery["counts_by_level"],
        "weak_chapters": weak,
        "quality_issues": audit["issue_count"] if audit else None,
        "quality_counts_by_code": audit["counts_by_code"] if audit else None,
        "exam_guide": guide,
        "focus_chapters": focus_chapters,
        "profile": profile_info,
        "dynamic_insights": insights,
        "practice_count": practice_count,
        "past_exam": past_exam_progress_stats(),
        "standards_training": standards_progress_stats(),
        "tasks": tasks,
    }


def render_dashboard_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# 学习驾驶舱 {payload['date']}",
        "",
        "## 总览",
        f"- 已答题：{payload['answered']}，正确：{payload['correct']}，正确率：{payload['accuracy_percent'] if payload['accuracy_percent'] is not None else '-'}%",
        f"- 错题归档：{payload['wrong_items']}，今日到期复习：{payload['due_review_count']}",
        f"- 知识点覆盖率：{payload['coverage_percent']}%，未练知识点：{payload['unpracticed_knowledge_points']}",
        f"- 平均掌握度：{payload['average_mastery_score']}/100",
    ]
    if payload["quality_issues"] is not None:
        lines.append(f"- 题库质量问题：{payload['quality_issues']}")
    if payload.get("focus_chapters"):
        lines.append(f"- 新版大纲高优先级章节：{','.join(str(chapter) for chapter in payload['focus_chapters'])}")
    profile = payload.get("profile") or {}
    lines.append(f"- 个人画像：每日 {profile.get('daily_minutes', '-')} 分钟，{profile.get('study_load', '标准')}负荷，建议题量 {payload.get('practice_count', 5)} 题")
    if profile.get("days_until_exam") is not None:
        lines.append(f"- 距离考试：{profile['days_until_exam']} 天")
    insights = payload.get("dynamic_insights") or {}
    if insights:
        recent = insights.get("recent_accuracy_percent") if insights.get("recent_accuracy_percent") is not None else "-"
        lines.append(f"- 动态校准：已答 {insights.get('choice_answered', 0)} 题，最近正确率 {recent}%")
    past_exam = payload.get("past_exam") or {}
    lines.append(
        f"- 历年真题：session {past_exam.get('sessions', 0)} 次，已答 {past_exam.get('answered', 0)} 题，正确率 {past_exam.get('accuracy_percent') if past_exam.get('accuracy_percent') is not None else '-'}%"
    )
    standards_training = payload.get("standards_training") or {}
    lines.append(
        f"- 标准规范：session {standards_training.get('sessions', 0)} 次，已答 {standards_training.get('answered', 0)} 题，正确率 {standards_training.get('accuracy_percent') if standards_training.get('accuracy_percent') is not None else '-'}%"
    )
    lines.append("")
    guide = payload.get("exam_guide") or {}
    if guide.get("subject_ranges"):
        ranges = guide["subject_ranges"]
        lines.append("## 考试导航")
        lines.append(f"- 综合知识范围：第{ranges.get('comprehensive', {}).get('chapters', '1-24')}章")
        lines.append(f"- 案例分析范围：第{ranges.get('case_analysis', {}).get('chapters', '4-24')}章")
        lines.append(f"- 论文范围：第{ranges.get('paper', {}).get('chapters', '4-17')}章")
        lines.append(f"- 资料：{guide.get('paths', {}).get('guide')} / {guide.get('paths', {}).get('syllabus')}")
        lines.append("")
    if profile:
        lines.append("## 个人画像")
        lines.append(f"- 目标：{profile.get('overall_goal') or profile.get('strategy') or '待确认'}")
        lines.append(f"- 阶段：{profile.get('stage') or '待确认'}")
        lines.append(f"- 薄弱科目：{', '.join(profile.get('weak_subjects') or []) or '待确认'}")
        lines.append(f"- 薄弱章节：{', '.join(str(chapter) for chapter in profile.get('weak_chapters') or []) or '待确认'}")
        lines.append(f"- 查看画像：python scripts/study.py profile")
        lines.append("")
    if insights:
        lines.append("## 动态校准")
        if insights.get("dynamic_weak_subjects"):
            for item in insights["dynamic_weak_subjects"]:
                lines.append(f"- {item['subject']}：{item['reason']}")
        elif insights.get("calibration_gaps"):
            lines.extend(f"- {item}" for item in insights["calibration_gaps"][:3])
        else:
            lines.append("- 暂无动态薄弱项，继续积累作答记录。")
        if insights.get("weak_knowledge_points"):
            lines.append("- 动态错题知识点：" + "、".join(str(item["knowledge_point"]) for item in insights["weak_knowledge_points"][:3]))
        if insights.get("weak_chapters"):
            lines.append("- 动态薄弱章节：" + "、".join(str(item["chapter"]) for item in insights["weak_chapters"][:3]))
        lines.append("")
    lines.append("## 掌握度分布")
    for level in ("未接触", "初学", "不稳定", "已掌握", "精通"):
        lines.append(f"- {level}: {payload['mastery_counts_by_level'].get(level, 0)}")
    lines.append("")
    lines.append("## 今日建议")
    for index, task in enumerate(payload["tasks"], start=1):
        lines.append(f"{index}. {task['title']}")
        lines.append(f"   {display_command(task['command'])}")
    lines.append("")
    lines.append("## 薄弱章节")
    if payload["weak_chapters"]:
        for row in payload["weak_chapters"]:
            lines.append(f"- {row['chapter']}: priority={row['priority']}, accuracy={row['accuracy']}, wrong_attempts={row['wrong_attempts']}")
    else:
        lines.append("- 暂无薄弱章节；当前更适合扩大知识点覆盖率。")
    if payload.get("quality_counts_by_code"):
        lines.append("")
        lines.append("## 题库质量")
        for code, count in sorted(payload["quality_counts_by_code"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {code}: {count}")
    return "\n".join(lines) + "\n"


def command_dashboard(args: argparse.Namespace) -> int:
    payload = build_dashboard_payload(args)
    if args.format == "markdown":
        print(render_dashboard_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def diagnose_wrong_result(item: dict[str, Any]) -> str:
    user_answer = str(item.get("user_answer") or "").strip()
    explanation = str(item.get("explanation") or "")
    if not user_answer:
        return "漏答或未形成判断"
    if any(term in explanation for term in ("不属于", "错误", "不是", "除")):
        return "审题方向偏差"
    if any(term in explanation for term in ("定义", "概念", "是指", "核心")):
        return "概念记忆不牢"
    if any(term in explanation for term in ("场景", "案例", "实践", "应用")):
        return "场景迁移不足"
    if any(term in explanation for term in ("流程", "步骤", "阶段", "过程")):
        return "流程顺序混淆"
    return "知识点辨析不足"


def build_root_cause_payload(args: argparse.Namespace) -> dict[str, Any]:
    progress = load_progress()
    records = progress.get("answers", [])
    if args.session:
        records = [record for record in records if record.get("session_id") == args.session]
    wrong_records = [record for record in records if not record.get("is_correct")]
    _, by_id, _ = load_all_questions()
    rows = []
    counts: Counter[str] = Counter()
    for record in wrong_records[-args.limit:]:
        question = by_id.get(record.get("question_id"), {})
        item = {
            "question_id": record.get("question_id"),
            "chapter": record.get("chapter"),
            "knowledge_point": record.get("knowledge_point"),
            "user_answer": record.get("user_answer"),
            "correct_answer": record.get("correct_answer"),
            "explanation": question.get("explanation"),
        }
        item["root_cause"] = diagnose_wrong_result(item)
        chapter_no = chapter_no_from_label(str(item.get("chapter") or ""))
        chapters = Counter({chapter_no: 1}) if chapter_no is not None else None
        item["command"] = chapter_command_for_point(str(item.get("knowledge_point") or ""), chapters)
        counts[item["root_cause"]] += 1
        rows.append(item)
    return {
        "wrong_count": len(wrong_records),
        "analyzed_count": len(rows),
        "counts_by_root_cause": dict(counts),
        "items": rows,
        "next_step": "python scripts/study.py drill --format markdown",
    }


def render_root_cause_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 错题根因分析",
        "",
        f"- 错题总数：{payload['wrong_count']}",
        f"- 本次分析：{payload['analyzed_count']}",
        "",
        "## 根因分布",
    ]
    if payload["counts_by_root_cause"]:
        for reason, count in sorted(payload["counts_by_root_cause"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- 暂无错题记录。")
    lines.append("")
    lines.append("## 代表错题")
    if payload["items"]:
        for item in payload["items"]:
            lines.append(f"- {item['question_id']} {item['knowledge_point']}: {item['root_cause']}")
            lines.append(f"  建议：{display_command(item['command'])}")
    else:
        lines.append("- 先完成一次练习并提交答案。")
    lines.append("")
    lines.append(f"Next: {display_command(payload['next_step'])}")
    return "\n".join(lines) + "\n"


def command_root_cause(args: argparse.Namespace) -> int:
    payload = build_root_cause_payload(args)
    if args.format == "markdown":
        print(render_root_cause_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_report_payload(args: argparse.Namespace) -> dict[str, Any]:
    progress = load_progress()
    archive = load_archive()
    dashboard = build_dashboard_payload(argparse.Namespace(limit=6, include_audit=True))
    readiness = build_readiness_payload(argparse.Namespace())
    mastery = build_mastery_payload(argparse.Namespace(limit=10, chapter=None))
    root_cause = build_root_cause_payload(argparse.Namespace(limit=10, session=None, format=args.format))
    sessions = progress.get("sessions", [])
    answers = progress.get("answers", [])
    period = args.period
    if period == "weekly":
        title = "学习周报"
        horizon_days = 7
    elif period == "monthly":
        title = "学习月报"
        horizon_days = 30
    else:
        title = "考前诊断报告"
        horizon_days = 30

    recent_answers = answers[-200:]
    by_point = Counter(str(item.get("knowledge_point") or "") for item in recent_answers if item.get("knowledge_point"))
    weak_points = mastery["weak_points"][:5]
    next_actions = dashboard["tasks"][:5]
    return {
        "title": title,
        "period": period,
        "horizon_days": horizon_days,
        "date": today().isoformat(),
        "answered": dashboard["answered"],
        "accuracy_percent": dashboard["accuracy_percent"],
        "wrong_items": len(archive.get("archive", [])),
        "due_review_count": dashboard["due_review_count"],
        "coverage_percent": dashboard["coverage_percent"],
        "average_mastery_score": dashboard["average_mastery_score"],
        "readiness": readiness,
        "sessions_count": len(sessions),
        "recent_top_points": by_point.most_common(8),
        "weak_points": weak_points,
        "root_cause": root_cause,
        "next_actions": next_actions,
        "quality_issues": dashboard.get("quality_issues"),
    }


def render_report_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload['title']} {payload['date']}",
        "",
        "## 总览",
        f"- 已答题：{payload['answered']}，正确率：{payload['accuracy_percent'] if payload['accuracy_percent'] is not None else '-'}%",
        f"- 知识点覆盖率：{payload['coverage_percent']}%，平均掌握度：{payload['average_mastery_score']}/100",
        f"- 错题：{payload['wrong_items']}，到期复习：{payload['due_review_count']}",
        f"- 备考成熟度：{payload['readiness']['readiness_score']}/100",
        f"- 题库质量问题：{payload['quality_issues']}",
        "",
        "## 主要短板",
    ]
    if payload["readiness"]["gaps"]:
        lines.extend(f"- {gap}" for gap in payload["readiness"]["gaps"])
    else:
        lines.append("- 当前短板较少，建议进入模拟考试和主观题稳定性训练。")
    lines.append("")
    lines.append("## 薄弱知识点")
    if payload["weak_points"]:
        for row in payload["weak_points"]:
            lines.append(f"- {row['knowledge_point']}: {row['score']}/100，{row['level']}，{row['action']}")
    else:
        lines.append("- 暂无薄弱知识点记录。")
    lines.append("")
    lines.append("## 错题根因")
    if payload["root_cause"]["counts_by_root_cause"]:
        for reason, count in sorted(payload["root_cause"]["counts_by_root_cause"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- 暂无错题根因数据。")
    lines.append("")
    lines.append("## 下一步行动")
    if payload["next_actions"]:
        for index, task in enumerate(payload["next_actions"], start=1):
            lines.append(f"{index}. {task['title']}")
            lines.append(f"   {task['command']}")
    else:
        lines.append("- python scripts/study.py dashboard --format markdown")
    return "\n".join(lines) + "\n"


def command_report(args: argparse.Namespace) -> int:
    payload = build_report_payload(args)
    if args.format == "markdown":
        print(render_report_markdown(payload))
    else:
        print(json.dumps(simplify_json(payload), ensure_ascii=False, indent=2))
    return 0


def past_exam_progress_stats() -> dict[str, Any]:
    progress = load_progress()
    sessions = progress.get("sessions", [])
    past_sessions = [session for session in sessions if str(session.get("type") or "").startswith("past_exam")]
    answers = [answer for answer in progress.get("answers", []) if str(answer.get("source") or "") == "past_exam"]
    total = len(answers)
    correct = sum(1 for answer in answers if answer.get("is_correct"))
    by_year: dict[str, dict[str, int]] = {}
    for answer in answers:
        year = str(answer.get("year") or "unknown")
        bucket = by_year.setdefault(year, {"answered": 0, "correct": 0})
        bucket["answered"] += 1
        if answer.get("is_correct"):
            bucket["correct"] += 1
    return {
        "sessions": len(past_sessions),
        "answered": total,
        "correct": correct,
        "accuracy_percent": round((correct / total) * 100, 2) if total else None,
        "by_year": by_year,
    }


def standards_progress_stats() -> dict[str, Any]:
    progress = load_progress()
    sessions = progress.get("sessions", [])
    standard_sessions = [session for session in sessions if str(session.get("type") or "") == "standards_training"]
    answers = [answer for answer in progress.get("answers", []) if str(answer.get("source") or "") == "standards_training"]
    total = len(answers)
    correct = sum(1 for answer in answers if answer.get("is_correct"))
    by_section: dict[str, dict[str, int]] = {}
    for answer in answers:
        section = str(answer.get("section") or "unknown")
        bucket = by_section.setdefault(section, {"answered": 0, "correct": 0})
        bucket["answered"] += 1
        if answer.get("is_correct"):
            bucket["correct"] += 1
    return {
        "sessions": len(standard_sessions),
        "answered": total,
        "correct": correct,
        "accuracy_percent": round((correct / total) * 100, 2) if total else None,
        "by_section": by_section,
    }


def build_readiness_payload(args: argparse.Namespace | None = None) -> dict[str, Any]:
    progress = load_progress()
    archive = load_archive()
    stats = progress.get("stats", {})
    answered = int(stats.get("total_answered", 0))
    correct = int(stats.get("total_correct", 0))
    accuracy = correct / answered if answered else 0
    coverage = build_coverage_payload(argparse.Namespace(limit=10, threshold=0.7, min_attempts=2))
    mastery = build_mastery_payload(argparse.Namespace(limit=10, chapter=None))
    due_count = len(due_items(50))
    wrong_items = len(archive.get("archive", []))
    sessions = progress.get("sessions", [])
    mock_count = sum(1 for session in sessions if session.get("type") == "mock_exam")
    case_count = len(progress.get("case_attempts", []))
    best_case_score = max((float(item.get("score_percent", 0)) for item in progress.get("case_attempts", [])), default=0)
    paper_attempts = progress.get("paper_attempts", [])
    best_paper_score = max((int(item.get("score", 0)) for item in paper_attempts), default=0)
    coverage_score = min(100, coverage["coverage_percent"])
    mastery_score = float(mastery["average_mastery_score"])
    accuracy_score = round(accuracy * 100, 2)
    volume_score = min(100, round(answered / 300 * 100, 2))
    review_score = max(0, 100 - due_count * 8 - wrong_items * 2)
    case_score = min(100, max(case_count * 25, best_case_score))
    paper_score = min(100, max(best_paper_score, 35 if paper_attempts else (20 if answered else 0)))
    mock_score = min(100, mock_count * 50)
    total = round(
        coverage_score * 0.18
        + mastery_score * 0.17
        + accuracy_score * 0.18
        + volume_score * 0.15
        + review_score * 0.15
        + case_score * 0.1
        + paper_score * 0.1
        + mock_score * 0.05,
        2,
    )
    gaps = []
    if coverage_score < 60:
        gaps.append("知识点覆盖率偏低")
    if mastery_score < 60:
        gaps.append("知识点掌握度偏低")
    if answered < 150:
        gaps.append("综合知识练习量不足")
    if case_score < 50:
        gaps.append("案例分析训练不足")
    if paper_score < 60:
        gaps.append("论文训练证据不足")
    if due_count:
        gaps.append("存在到期错题未复习")
    return {
        "readiness_score": total,
        "components": {
            "coverage": coverage_score,
            "mastery": mastery_score,
            "accuracy": accuracy_score if answered else None,
            "volume": volume_score,
            "review": review_score,
            "case": case_score,
            "paper": paper_score,
            "mock": mock_score,
        },
        "answered": answered,
        "accuracy_percent": round(accuracy * 100, 2) if answered else None,
        "coverage_percent": coverage["coverage_percent"],
        "average_mastery_score": mastery_score,
        "due_review_count": due_count,
        "wrong_items": wrong_items,
        "case_sessions": case_count,
        "paper_attempts": len(paper_attempts),
        "mock_sessions": mock_count,
        "gaps": gaps,
    }


def render_readiness_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 备考成熟度评分",
        "",
        f"- 总分：{payload['readiness_score']}/100",
        f"- 已答题：{payload['answered']}，正确率：{payload['accuracy_percent'] if payload['accuracy_percent'] is not None else '-'}%",
        f"- 知识点覆盖率：{payload['coverage_percent']}%",
        f"- 平均掌握度：{payload['average_mastery_score']}/100",
        f"- 错题：{payload['wrong_items']}，到期复习：{payload['due_review_count']}",
        f"- 案例训练次数：{payload['case_sessions']}，论文提交次数：{payload['paper_attempts']}，模拟考试次数：{payload['mock_sessions']}",
        "",
        "## 分项",
    ]
    for key, value in payload["components"].items():
        lines.append(f"- {key}: {value if value is not None else '-'}")
    lines.append("")
    lines.append("## 主要短板")
    if payload["gaps"]:
        lines.extend(f"- {gap}" for gap in payload["gaps"])
    else:
        lines.append("- 当前结构较均衡，建议进入模拟考试和论文冲刺。")
    return "\n".join(lines) + "\n"


def command_readiness(args: argparse.Namespace) -> int:
    payload = build_readiness_payload(args)
    if args.format == "markdown":
        print(render_readiness_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_sprint_payload(args: argparse.Namespace) -> dict[str, Any]:
    profile = load_learner_profile()
    profile_info = profile_summary(profile)
    practice_count = profile_practice_count(profile)
    daily_minutes = profile_info["daily_minutes"]
    compact_day = daily_minutes < 60
    expanded_day = daily_minutes >= 120
    readiness = build_readiness_payload(args)
    days = max(1, int(args.days))
    focus_chapters = exam_focus_chapters()
    method_chapters = load_syllabus_analysis().get("strategic_focus", {}).get("method_chapters", list(range(4, 11)))
    paper_chapters = paper_range_chapters()
    case_chapters = case_range_chapters_text()
    tasks = []
    for day in range(1, days + 1):
        day_tasks = []
        if day % 3 == 1:
            day_tasks.append({"type": "coverage", "title": "补齐高频知识点", "command": "python scripts/study.py coverage --format markdown"})
            target = ",".join(str(chapter) for chapter in focus_chapters[:4])
            day_tasks.append({"type": "practice", "title": "新版大纲核心章节练习", "command": f"python scripts/study.py start --chapters {target} --count {practice_count} --format markdown"})
            if expanded_day:
                day_tasks.append({"type": "sprint_cards", "title": "冲刺背诵卡", "command": "python scripts/study.py sprint-training cards --count 5 --format markdown"})
        elif day % 3 == 2:
            day_tasks.append({"type": "case", "title": "案例分析训练", "command": f"python scripts/study.py case start --chapters {case_chapters} --count {profile_case_count(profile)} --format markdown"})
            day_tasks.append({"type": "review", "title": "错题复习", "command": "python scripts/study.py review --format markdown"})
        else:
            topic = DEFAULT_PAPER_TOPIC if day % 6 == 3 else "技术与研发管理"
            day_tasks.append({"type": "paper", "title": "论文框架与草稿", "command": f"python scripts/study.py paper --topic {topic} --format markdown"})
            mock_command = "python scripts/study.py start --mode mock --format markdown" if expanded_day else f"python scripts/study.py past-exam start --count {practice_count} --format markdown"
            day_tasks.append({"type": "mock", "title": "综合知识模拟" if expanded_day else "历年真题选择训练", "command": mock_command})
        if args.include_audit and day == 1:
            day_tasks.append({"type": "quality", "title": "题库质量审计", "command": "python scripts/study.py audit --format markdown"})
        if compact_day:
            day_tasks = day_tasks[:2]
        tasks.append({"day": day, "focus": day_tasks[0]["title"], "tasks": day_tasks})
    return {
        "days": days,
        "readiness": readiness,
        "strategy": "依据内部学习指南和新版大纲：优先第11-17章，穿插第4-10章方法篇，案例覆盖第4-24章，论文聚焦第4-17章。",
        "focus_chapters": focus_chapters,
        "method_chapters": method_chapters,
        "paper_chapters": paper_chapters,
        "case_chapters": case_chapters,
        "profile": profile_info,
        "practice_count": practice_count,
        "plan": tasks,
    }


def render_sprint_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload['days']}天冲刺计划",
        "",
        f"- 当前成熟度：{payload['readiness']['readiness_score']}/100",
        f"- 策略：{payload['strategy']}",
        f"- 个人画像：每日 {payload['profile']['daily_minutes']} 分钟，{payload['profile']['study_load']}负荷，默认题量 {payload['practice_count']} 题",
        f"- 核心章节：{','.join(str(chapter) for chapter in payload['focus_chapters'])}",
        f"- 案例范围：第{payload['case_chapters']}章；论文范围：第{','.join(str(chapter) for chapter in payload['paper_chapters'])}章",
        "",
        "## 每日安排",
    ]
    for day in payload["plan"]:
        lines.append(f"{day['day']}. {day['focus']}")
        for task in day["tasks"]:
            lines.append(f"   - {task['title']}: {display_command(task['command'])}")
    lines.append("")
    lines.append("## 先处理短板")
    if payload["readiness"]["gaps"]:
        lines.extend(f"- {gap}" for gap in payload["readiness"]["gaps"])
    else:
        lines.append("- 当前短板较少，重点放在模拟考试和主观题稳定性。")
    return "\n".join(lines) + "\n"


def command_sprint(args: argparse.Namespace) -> int:
    payload = build_sprint_payload(args)
    if args.format == "markdown":
        print(render_sprint_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
