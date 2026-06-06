from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
from typing import Any

from study_utils import ROOT, choose_questions, load_json, make_session, parse_answer_text

from study_modules.ask import build_ask_payload, command_ask
from study_modules.case import (
    build_case_submit_payload,
    command_case_submit,
    filter_cases_by_source,
    load_case_studies,
    render_case_markdown,
)
from study_modules.materials import (
    command_backup_pdfs,
    command_candidate_practice,
    command_exam_guide,
    command_internal_material,
    command_recitation,
    command_sprint_material,
)
from study_modules.mastery import command_mastery
from study_modules.paper import (
    build_paper_review_payload,
    command_paper,
    command_paper_reference,
    render_paper_review_markdown,
)
from study_modules.past_exam import (
    command_past_exam_paper,
    command_past_exam_start,
    filter_year_period,
    load_past_exam_cases,
    load_past_exam_choices,
    public_past_exam_case,
    public_past_exam_question,
    render_past_exam_case_markdown,
    render_past_exam_choice_markdown,
)
from study_modules.profile import (
    command_profile,
    command_profile_update,
    default_learner_profile,
    profile_dynamic_insights,
    profile_dynamic_weak_subject_names,
)
from study_modules.quality import command_audit
from study_modules.reports import command_dashboard, command_readiness, command_report
from study_modules.search_training import (
    command_search,
    command_sprint_training_cards,
    command_sprint_training_case,
    command_sprint_training_start,
    build_sprint_training_start_payload,
    render_sprint_training_start_markdown,
)
from study_modules.session_flow import (
    command_start,
    grade_session,
    render_grade_markdown,
    session_records,
)
from study_modules.settings import (
    DEFAULT_OUTPUT_FORMAT,
    ROUTER_EXAMPLES_FILE,
    SKILL_FILE,
    SKILL_SUMMARY_SCRIPT,
    STANDARDS_TRAINING_FILE,
)
from study_modules.standards import (
    build_standards_start_payload,
    command_standards_clauses,
    command_standards_list,
    command_standards_start,
    load_standard_questions,
    render_standards_start_markdown,
)


def run_regression_case(name: str, func: Any, args: argparse.Namespace, expect: dict[str, Any] | None = None) -> dict[str, Any]:
    buffer = io.StringIO()
    status = "passed"
    error = None
    try:
        with redirect_stdout(buffer):
            code = func(args)
        if code not in (0, None):
            status = "failed"
            error = f"exit_code={code}"
    except Exception as exc:  # noqa: BLE001 - regression should report any command failure.
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"
    output = buffer.getvalue()
    if expect and status == "passed":
        contains = expect.get("contains")
        if contains and contains not in output:
            status = "failed"
            error = f"missing expected text: {contains}"
        checker = expect.get("check")
        if checker and status == "passed":
            check_error = checker(output)
            if check_error:
                status = "failed"
                error = check_error
    return {"name": name, "status": status, "error": error, "output_preview": output[:300]}


def load_router_examples() -> dict[str, Any]:
    return load_json(ROUTER_EXAMPLES_FILE, {"defaults": {}, "examples": []})


def make_router_example_checker(example: dict[str, Any]) -> Any:
    expected_intent = example.get("expected_intent")
    expected_command = example.get("expected_command_contains")

    def check(_: str) -> str | None:
        payload = build_ask_payload(
            argparse.Namespace(
                text=example.get("text", ""),
                execute=bool(example.get("execute", True)),
                no_record=bool(example.get("no_record", True)),
                dry_run=bool(example.get("dry_run", False)),
                format=example.get("format", "markdown"),
            )
        )
        route = payload.get("route") or {}
        if expected_intent and route.get("intent") != expected_intent:
            return f"route intent mismatch: expected {expected_intent}, got {route.get('intent')}"
        if expected_command and expected_command not in str(route.get("command") or ""):
            return f"route command mismatch: missing {expected_command}"
        return None

    return check


def router_regression_cases() -> list[tuple[str, Any, argparse.Namespace, dict[str, Any]]]:
    data = load_router_examples()
    defaults = data.get("defaults") if isinstance(data.get("defaults"), dict) else {}
    cases = []
    for index, example in enumerate(data.get("examples", []), start=1):
        if not isinstance(example, dict):
            continue
        text = str(example.get("text") or "")
        if not text:
            continue
        name = str(example.get("name") or f"router_example_{index}")
        args = argparse.Namespace(
            text=text,
            execute=bool(example.get("execute", defaults.get("execute", True))),
            no_record=bool(example.get("no_record", defaults.get("no_record", True))),
            dry_run=bool(example.get("dry_run", defaults.get("dry_run", False))),
            format=str(example.get("format", defaults.get("format", "markdown"))),
        )
        expect: dict[str, Any] = {"check": make_router_example_checker({**defaults, **example})}
        if example.get("expected_output_contains"):
            expect["contains"] = str(example["expected_output_contains"])
        cases.append((f"router_{name}", command_ask, args, expect))
    return cases


def regression_fixture_case_args() -> argparse.Namespace | None:
    for record in session_records():
        session = record["session"]
        if session.get("type") != "case_study":
            continue
        question_ids = list(session.get("answers_template", {}).keys())
        if question_ids:
            return argparse.Namespace(session=session["id"], answers=" ".join("A" for _ in question_ids), no_record=True, format="markdown")
    return None


def command_regression_paper_no_record(args: argparse.Namespace) -> int:
    sample = (
        "摘要：本文围绕企业数字化转型项目，说明建设背景、目标和效果。"
        "本人担任系统规划师，负责数字化蓝图、数据治理、业务流程优化和平台建设。"
        "首先分析现状痛点和流程瓶颈，其次制定总体架构、数据标准、安全合规和实施路线图，"
        "再次建立组织保障、培训机制、风险控制和持续改进闭环。"
        "项目上线后以效率、质量、成本、满意度、覆盖率等指标验收，支撑经营决策和服务提升。"
    )
    payload = build_paper_review_payload(
        argparse.Namespace(topic="企业数字化转型", draft=None, text=sample, min_chars=80, no_record=True, format=getattr(args, "format", "markdown"))
    )
    if getattr(args, "format", "markdown") == "markdown":
        print(render_paper_review_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload.get("error") else 0


def command_regression_case_recitation_start(args: argparse.Namespace) -> int:
    cases = filter_cases_by_source(load_case_studies(), "recitation")
    cases = [case for case in cases if 12 in set(case.get("chapters") or [case.get("chapter")])]
    selected = choose_questions(cases, 1, seed=None)
    if not selected:
        print("No promoted recitation case matched chapter 12.")
        return 1
    print(render_case_markdown(selected[0]))
    return 0


def command_regression_past_exam_choices(args: argparse.Namespace) -> int:
    choices = filter_year_period(load_past_exam_choices(), getattr(args, "year", None), getattr(args, "period", None))
    selected = choose_questions(choices, int(args.count), seed=getattr(args, "seed", None))
    payload = {
        "session": {"id": "regression_past_exam", "type": "past_exam"},
        "session_file": "<no-write>",
        "year": getattr(args, "year", None),
        "period": getattr(args, "period", None),
        "available": len(choices),
        "questions": [public_past_exam_question(question) for question in selected],
        "next_step": "python scripts/study.py submit --session <past_exam_session> --answers \"A B C ...\" --format markdown",
    }
    print(render_past_exam_choice_markdown(payload))
    return 0


def command_regression_past_exam_case(args: argparse.Namespace) -> int:
    cases = filter_year_period(load_past_exam_cases(), getattr(args, "year", None), getattr(args, "period", None))
    selected = choose_questions(cases, int(args.count), seed=getattr(args, "seed", None))
    payload = {
        "session": {"id": "regression_past_exam_case", "type": "past_exam_case"},
        "session_file": "<no-write>",
        "year": getattr(args, "year", None),
        "period": getattr(args, "period", None),
        "available": len(cases),
        "cases": [public_past_exam_case(case) for case in selected],
        "next_step": "python scripts/study.py case submit --session <past_exam_case_session> --answers \"...\" --format markdown",
    }
    print(render_past_exam_case_markdown(payload))
    return 0


def command_regression_standards_start(args: argparse.Namespace) -> int:
    payload = build_standards_start_payload(args, write=False)
    print(render_standards_start_markdown(payload))
    return 0


def command_regression_standards_submit(args: argparse.Namespace) -> int:
    questions = choose_questions(load_standard_questions(), 2, seed=1)
    if not questions:
        print("No standards questions available.")
        return 1
    session = make_session("standards_training", [question["id"] for question in questions], {"source": str(STANDARDS_TRAINING_FILE.relative_to(ROOT))})
    payload = grade_session(session, parse_answer_text("A B", session["question_ids"]), record=False)
    payload["session_id"] = session.get("id")
    print(render_grade_markdown(payload))
    return 0


def command_regression_sprint_training_start(args: argparse.Namespace) -> int:
    payload = build_sprint_training_start_payload(args, write=False)
    print(render_sprint_training_start_markdown(payload))
    return 0


def command_regression_skill_summary(args: argparse.Namespace) -> int:
    spec = importlib.util.spec_from_file_location("update_skill_summary", SKILL_SUMMARY_SCRIPT)
    if spec is None or spec.loader is None:
        print("Could not load scripts/update_skill_summary.py")
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    current = SKILL_FILE.read_text(encoding="utf-8")
    expected = module.update_skill_summary(current, module.build_asset_summary())
    if current != expected:
        print("SKILL.md asset summary is stale. Run: python scripts/update_skill_summary.py")
        return 1
    print("SKILL.md asset summary is current.")
    return 0


def command_regression_profile_insights(args: argparse.Namespace) -> int:
    profile = default_learner_profile()
    answers = [
        {"chapter": "第12章", "knowledge_point": "服务目录设计", "is_correct": False},
        {"chapter": "第12章", "knowledge_point": "服务目录设计", "is_correct": False},
        {"chapter": "第12章", "knowledge_point": "服务级别管理", "is_correct": True},
        {"chapter": "第17章", "knowledge_point": "项目风险管理", "is_correct": False},
        {"chapter": "第17章", "knowledge_point": "项目风险管理", "is_correct": True},
    ]
    progress = {
        "answers": answers,
        "stats": {"total_answered": len(answers), "total_correct": sum(1 for item in answers if item["is_correct"])},
        "case_attempts": [{"score_percent": 48}],
        "paper_attempts": [{"score": 52}],
    }
    archive = {"stats": {"by_chapter": {"第12章": {"wrong_attempts": 2}}}}
    insights = profile_dynamic_insights(profile, progress=progress, archive=archive, recent_limit=20)
    subjects = profile_dynamic_weak_subject_names(insights)
    if 12 not in [item.get("chapter_no") for item in insights.get("weak_chapters", [])]:
        print("Missing dynamic weak chapter 12.")
        return 1
    if "服务目录设计" not in [item.get("knowledge_point") for item in insights.get("weak_knowledge_points", [])]:
        print("Missing dynamic weak knowledge point 服务目录设计.")
        return 1
    if not {"综合知识", "案例分析", "论文"}.issubset(subjects):
        print(f"Missing dynamic weak subjects: {subjects}")
        return 1
    if not insights.get("actions"):
        print("Missing dynamic actions.")
        return 1
    print("Profile dynamic insights: weak chapter 12, 服务目录设计, 综合知识/案例分析/论文.")
    return 0


def command_regression_default_format(args: argparse.Namespace) -> int:
    from study_modules.cli import build_parser

    parser = build_parser()
    examples = [
        ("ask", ["ask", "今天我该学什么"]),
        ("profile", ["profile"]),
        ("plan", ["plan"]),
        ("dashboard", ["dashboard"]),
        ("search", ["search", "服务目录设计"]),
        ("start", ["start", "--chapters", "12", "--count", "1"]),
        ("past-exam start", ["past-exam", "start", "--count", "1"]),
        ("standards list", ["standards", "list"]),
        ("case start", ["case", "start", "--count", "1"]),
    ]
    mismatches = []
    for name, argv in examples:
        parsed = parser.parse_args(argv)
        if getattr(parsed, "format", None) != DEFAULT_OUTPUT_FORMAT:
            mismatches.append(f"{name}={getattr(parsed, 'format', None)}")
    if mismatches:
        print("Default format mismatch: " + ", ".join(mismatches))
        return 1
    explicit = parser.parse_args(["ask", "今天我该学什么", "--format", "json"])
    if explicit.format != "json":
        print("Explicit --format json is not preserved.")
        return 1
    print(f"Default CLI format: {DEFAULT_OUTPUT_FORMAT}; explicit --format json preserved.")
    return 0


def build_regression_payload(args: argparse.Namespace) -> dict[str, Any]:
    cases = [
        ("default_markdown_format", command_regression_default_format, argparse.Namespace(format="markdown"), {"contains": "Default CLI format: markdown"}),
        ("audit", command_audit, argparse.Namespace(limit=5, min_explanation_length=30, format="markdown"), {"contains": "问题数量：0"}),
        ("dashboard", command_dashboard, argparse.Namespace(limit=4, include_audit=True, format="markdown"), {"contains": "学习驾驶舱"}),
        ("profile", command_profile, argparse.Namespace(format="markdown"), {"contains": "个人备考画像"}),
        ("profile_dynamic_insights", command_regression_profile_insights, argparse.Namespace(format="markdown"), {"contains": "Profile dynamic insights"}),
        ("profile_update_preview", command_profile_update, argparse.Namespace(text="我每天能学1小时，论文最弱，优先保过", write=False, format="markdown"), {"contains": "availability.daily_minutes"}),
        ("profile_update_sensitive_block", command_profile_update, argparse.Namespace(text="保存到画像：我每天能学1小时，手机号13800000000", write=True, format="markdown"), {"contains": "写入被拦截"}),
        ("mastery", command_mastery, argparse.Namespace(limit=5, chapter=None, format="markdown"), {"contains": "知识点掌握度"}),
        ("readiness", command_readiness, argparse.Namespace(format="markdown"), {"contains": "备考成熟度评分"}),
        ("report", command_report, argparse.Namespace(period="weekly", format="markdown"), {"contains": "学习周报"}),
        ("exam_guide", command_exam_guide, argparse.Namespace(limit=5, format="markdown"), {"contains": "论文：第4-17章"}),
        ("internal_notes", command_internal_material, argparse.Namespace(kind="notes", chapter=12, preview_lines=3, format="markdown"), {"contains": "第12章 信息系统服务管理"}),
        ("internal_mindmap", command_internal_material, argparse.Namespace(kind="mindmap", chapter=12, preview_lines=3, format="markdown"), {"contains": "服务战略规划"}),
        ("backup_past_exams", command_backup_pdfs, argparse.Namespace(category="past-exam", year=None, subject=None, limit=5, format="markdown"), {"contains": "历年真题"}),
        ("start_dry_run", command_start, argparse.Namespace(mode="practice", chapters="12", count=2, difficulty=None, knowledge_point=None, section=None, tag=None, seed=1, dry_run=True, format="markdown"), {"contains": "<dry-run>"}),
        ("past_exam_choices", command_regression_past_exam_choices, argparse.Namespace(year=2022, period=None, count=2, seed=1, format="markdown"), {"contains": "历年真题选择题"}),
        ("past_exam_choices_dry_run", command_past_exam_start, argparse.Namespace(year=2022, period=None, count=2, seed=1, dry_run=True, format="markdown"), {"contains": "<dry-run>"}),
        ("past_exam_case", command_regression_past_exam_case, argparse.Namespace(year=2021, period=None, count=1, seed=1, show_answer=False, format="markdown"), {"contains": "历年案例真题"}),
        ("past_exam_paper", command_past_exam_paper, argparse.Namespace(year=2022, period=None, topic=None, count=2, seed=1, format="markdown"), {"contains": "历年论文真题"}),
        ("backup_standards", command_backup_pdfs, argparse.Namespace(category="standards", year=None, subject=None, limit=5, format="markdown"), {"contains": "标准规范库"}),
        ("standards_list", command_standards_list, argparse.Namespace(document=None, tag=None, limit=5, format="markdown"), {"contains": "标准规范结构化训练库"}),
        ("standards_clauses", command_standards_clauses, argparse.Namespace(document="网络安全法", keyword=None, tag=None, limit=3, format="markdown"), {"contains": "标准规范条款检索"}),
        ("standards_start", command_regression_standards_start, argparse.Namespace(document="网络安全法", keyword=None, tag=None, count=2, seed=1, format="markdown"), {"contains": "标准规范专项训练"}),
        ("standards_start_dry_run", command_standards_start, argparse.Namespace(document="网络安全法", keyword=None, tag=None, count=2, seed=1, dry_run=True, format="markdown"), {"contains": "<dry-run>"}),
        ("standards_submit_no_record", command_regression_standards_submit, argparse.Namespace(format="markdown"), {"contains": "Recorded: False"}),
        ("sprint_materials", command_sprint_material, argparse.Namespace(kind="sprint-guide", keyword=None, limit=5, preview_lines=3, format="markdown"), {"contains": "规划冲刺资料"}),
        ("search_materials", command_search, argparse.Namespace(query="服务目录设计", source_type=None, chapter=None, limit=3, format="markdown"), {"contains": "全资料检索"}),
        ("sprint_training_cards", command_sprint_training_cards, argparse.Namespace(kind="activities", keyword=None, count=2, seed=1, show_answer=False, format="markdown"), {"contains": "冲刺背诵卡"}),
        ("sprint_training_start", command_regression_sprint_training_start, argparse.Namespace(kind="mock-exam", keyword=None, count=2, seed=1, format="markdown"), {"contains": "冲刺模拟候选题训练"}),
        ("sprint_training_start_dry_run", command_sprint_training_start, argparse.Namespace(kind="mock-exam", keyword=None, count=2, seed=1, dry_run=True, format="markdown"), {"contains": "<dry-run>"}),
        ("sprint_training_case", command_sprint_training_case, argparse.Namespace(kind="csf-risk", keyword=None, count=2, seed=1, show_answer=False, format="markdown"), {"contains": "冲刺案例采分点训练"}),
        ("candidate_practice", command_candidate_practice, argparse.Namespace(chapter=12, count=2, format="markdown"), {"contains": "候选题源仅用于预览"}),
        ("recitation", command_recitation, argparse.Namespace(chapter=12, count=2, show_answer=True, format="markdown"), {"contains": "参考答案/采分点"}),
        ("case_recitation_start", command_regression_case_recitation_start, argparse.Namespace(format="markdown"), {"contains": "cs_recite_ch12"}),
        ("paper_reference", command_paper_reference, argparse.Namespace(topic="信息系统规划", scenario="政务", format="markdown"), {"contains": "内部论文专题参考"}),
        ("paper_start_refs", command_paper, argparse.Namespace(topic="信息系统规划", limit=8, format="markdown"), {"contains": "内部论文专题参考"}),
        ("paper_no_record", command_regression_paper_no_record, argparse.Namespace(format="markdown"), {"contains": "记录写入：否"}),
        ("skill_summary_current", command_regression_skill_summary, argparse.Namespace(format="markdown"), {"contains": "SKILL.md asset summary is current."}),
    ]
    cases.extend(router_regression_cases())
    case_args = regression_fixture_case_args()
    if case_args is not None:
        cases.append(("case_no_record", command_case_submit, case_args, {"contains": "Recorded: False"}))
    results = [run_regression_case(name, func, case_args, expect) for name, func, case_args, expect in cases]
    failed = [item for item in results if item["status"] != "passed"]
    return {
        "status": "failed" if failed else "passed",
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": results if args.verbose or failed else [{"name": item["name"], "status": item["status"]} for item in results],
    }


def render_regression_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 自动回归测试",
        "",
        f"- 状态：{payload['status']}",
        f"- 通过：{payload['passed']}",
        f"- 失败：{payload['failed']}",
        "",
        "## 用例",
    ]
    for item in payload["results"]:
        lines.append(f"- {item['status']} {item['name']}")
        if item.get("error"):
            lines.append(f"  {item['error']}")
    return "\n".join(lines) + "\n"


def command_regression(args: argparse.Namespace) -> int:
    payload = build_regression_payload(args)
    if args.format == "markdown":
        print(render_regression_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 1 if payload["status"] != "passed" else 0
