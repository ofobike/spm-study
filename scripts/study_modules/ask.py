from __future__ import annotations

import argparse
import json
from typing import Any

from study_utils import ROOT, parse_answer_text, public_question, render_questions_markdown

from study_modules.case import (
    build_case_start_payload,
    build_case_submit_payload,
    render_case_markdown,
    render_case_submit_markdown,
)
from study_modules.common import display_command, session_file_value, session_next_step
from study_modules.materials import (
    build_backup_pdf_payload,
    build_candidate_practice_payload,
    build_exam_guide_payload,
    build_internal_material_payload,
    build_recitation_payload,
    build_sprint_material_payload,
    build_vip_material_payload,
    case_range_chapters_text,
    render_backup_pdf_markdown,
    render_candidate_practice_markdown,
    render_exam_guide_markdown,
    render_internal_material_markdown,
    render_recitation_markdown,
    render_sprint_material_markdown,
    render_vip_material_markdown,
)
from study_modules.mastery import (
    build_coverage_payload,
    build_mastery_payload,
    render_coverage_markdown,
    render_mastery_markdown,
)
from study_modules.paper import (
    build_paper_payload,
    build_paper_reference_payload,
    render_paper_markdown,
    render_paper_reference_markdown,
)
from study_modules.past_exam import (
    build_past_exam_case_payload,
    build_past_exam_choice_payload,
    build_past_exam_paper_payload,
    render_past_exam_case_markdown,
    render_past_exam_choice_markdown,
    render_past_exam_paper_markdown,
)
from study_modules.profile import (
    build_profile_payload,
    build_profile_update_payload,
    render_profile_markdown,
    render_profile_update_markdown,
)
from study_modules.quality import (
    build_audit_payload,
    build_quality_fix_payload,
    render_audit_markdown,
    render_quality_fix_markdown,
)
from study_modules.reports import (
    build_dashboard_payload,
    build_plan_payload,
    build_readiness_payload,
    build_report_payload,
    build_root_cause_payload,
    build_sprint_payload,
    render_dashboard_markdown,
    render_plan_markdown,
    render_readiness_markdown,
    render_report_markdown,
    render_root_cause_markdown,
    render_sprint_markdown,
)
from study_modules.router import answer_payload_from_text, route_intent
from study_modules.search_training import (
    build_search_payload,
    build_sprint_training_cards_payload,
    build_sprint_training_case_payload,
    build_sprint_training_start_payload,
    render_search_markdown,
    render_sprint_training_cards_markdown,
    render_sprint_training_case_markdown,
    render_sprint_training_start_markdown,
)
from study_modules.session_flow import (
    build_continue_payload,
    build_drill_payload,
    build_practice,
    build_start_payload,
    build_wrong,
    due_items,
    grade_session,
    is_session_completed,
    latest_session,
    render_continue_markdown,
    render_drill_markdown,
    render_grade_markdown,
    session_records,
)
from study_modules.standards import (
    build_standards_clauses_payload,
    build_standards_start_payload,
    render_standards_clauses_markdown,
    render_standards_start_markdown,
)


def build_submit_latest_payload(args: argparse.Namespace) -> dict[str, Any]:
    answer_info = answer_payload_from_text(args.text)
    if not answer_info:
        return {"error": "没有识别到可提交的答案，请使用“我的答案是 A B C D”或“我的答案是 q1=A;q2=B”。"}
    normal_record = latest_session(open_only=True)
    if normal_record and normal_record["session"].get("type") in {"case_study", "past_exam_case"} and answer_info.get("choices"):
        later_normal = next(
            (
                record
                for record in session_records()
                if record["session"].get("type") not in {"case_study", "past_exam_case"} and not is_session_completed(record["session"])
            ),
            None,
        )
        if later_normal:
            normal_record = later_normal
    if not normal_record:
        return {"error": "没有找到未完成 session，请先让 Skill 出题或案例训练。"}
    session = normal_record["session"]
    if session.get("type") in {"case_study", "past_exam_case"}:
        case_args = argparse.Namespace(session=session["id"], answers=answer_info["raw"] or args.text, no_record=getattr(args, "no_record", False), format=args.format)
        payload = build_case_submit_payload(case_args)
        payload["submitted_via"] = "ask"
        payload["route_type"] = "case_submit"
        return payload
    answers = parse_answer_text(answer_info["choices"] or answer_info["raw"], session.get("question_ids", []))
    payload = grade_session(session, answers, record=not args.no_record)
    payload["session_id"] = session.get("id")
    payload["session_file"] = str(normal_record["path"].relative_to(ROOT))
    payload["submitted_via"] = "ask"
    payload["route_type"] = "submit"
    return payload


def render_submit_latest_markdown(payload: dict[str, Any]) -> str:
    if payload.get("error"):
        return f"{payload['error']}\n"
    if payload.get("route_type") == "case_submit":
        return render_case_submit_markdown(payload)
    return render_grade_markdown(payload)


def build_ask_payload(args: argparse.Namespace) -> dict[str, Any]:
    route = route_intent(args.text)
    payload = {"text": args.text, "route": route}
    if not args.execute or route.get("needs_input"):
        return payload
    intent = route.get("execute")
    write_session_on_execute = not (bool(getattr(args, "no_record", False)) or bool(getattr(args, "dry_run", False)))
    if intent == "dashboard":
        payload["result"] = build_dashboard_payload(argparse.Namespace(limit=6, include_audit=True))
    elif intent == "continue":
        payload["result"] = build_continue_payload(argparse.Namespace(type=None, any=False, format=args.format))
    elif intent == "submit_latest":
        payload["result"] = build_submit_latest_payload(argparse.Namespace(text=args.text, no_record=getattr(args, "no_record", False), format=args.format))
    elif intent == "sprint":
        payload["result"] = build_sprint_payload(argparse.Namespace(days=route.get("days", 14), include_audit=True))
    elif intent == "readiness":
        payload["result"] = build_readiness_payload(argparse.Namespace())
    elif intent == "mastery":
        payload["result"] = build_mastery_payload(argparse.Namespace(limit=10, chapter=None))
    elif intent == "plan":
        payload["result"] = build_plan_payload(argparse.Namespace(review_limit=10, weak_limit=5, practice_count=5, default_chapter=12, include_mock=False, format=args.format))
    elif intent == "drill":
        payload["result"] = build_drill_payload(argparse.Namespace(count=route.get("count", 5), chapter=route.get("chapter"), difficulty=None, seed=None, dry_run=not write_session_on_execute, format=args.format))
    elif intent == "root_cause":
        payload["result"] = build_root_cause_payload(argparse.Namespace(limit=10, session=None, format=args.format))
    elif intent == "report":
        payload["result"] = build_report_payload(argparse.Namespace(period=route.get("period", "weekly"), format=args.format))
    elif intent == "regression":
        from study_modules.regression import build_regression_payload

        payload["result"] = build_regression_payload(argparse.Namespace(verbose=False, format=args.format))
    elif intent == "profile":
        payload["result"] = build_profile_payload(argparse.Namespace(format=args.format))
    elif intent == "profile_update":
        write_profile = bool(route.get("write", False)) and write_session_on_execute
        payload["result"] = build_profile_update_payload(argparse.Namespace(text=args.text, write=write_profile, format=args.format))
    elif intent == "exam_guide":
        payload["result"] = build_exam_guide_payload(argparse.Namespace(limit=8, format=args.format))
    elif intent == "internal_material":
        payload["result"] = build_internal_material_payload(argparse.Namespace(kind=route.get("kind", "notes"), chapter=route.get("chapter"), preview_lines=8, format=args.format))
    elif intent == "vip_material":
        payload["result"] = build_vip_material_payload(argparse.Namespace(kind=route.get("kind", "all"), keyword=None, limit=10, preview_lines=8, format=args.format))
    elif intent == "sprint_material":
        payload["result"] = build_sprint_material_payload(argparse.Namespace(kind=route.get("kind", "all"), keyword=None, limit=10, preview_lines=8, format=args.format))
    elif intent == "sprint_training_cards":
        payload["result"] = build_sprint_training_cards_payload(argparse.Namespace(kind=route.get("kind", "all"), keyword=None, count=route.get("count", 5), seed=None, show_answer=False, format=args.format))
    elif intent == "sprint_training_start":
        payload["result"] = build_sprint_training_start_payload(argparse.Namespace(kind=route.get("kind", "all"), keyword=None, count=route.get("count", 5), seed=None, dry_run=not write_session_on_execute, format=args.format))
    elif intent == "sprint_training_case":
        payload["result"] = build_sprint_training_case_payload(argparse.Namespace(kind=route.get("kind", "all"), keyword=None, count=route.get("count", 5), seed=None, show_answer=False, format=args.format))
    elif intent == "search":
        payload["result"] = build_search_payload(argparse.Namespace(query=route.get("query") or args.text, source_type=route.get("source_type"), chapter=route.get("chapter"), limit=8, format=args.format))
    elif intent == "backup_pdfs":
        payload["result"] = build_backup_pdf_payload(argparse.Namespace(category=route.get("category", "all"), year=route.get("year"), subject=route.get("subject"), limit=10, format=args.format))
    elif intent == "candidate_practice":
        payload["result"] = build_candidate_practice_payload(argparse.Namespace(chapter=route.get("chapter"), count=route.get("count", 5), format=args.format))
    elif intent == "recitation":
        payload["result"] = build_recitation_payload(argparse.Namespace(chapter=route.get("chapter"), count=route.get("count", 5), show_answer=route.get("show_answer", False), format=args.format))
    elif intent == "past_exam_choice":
        payload["result"] = build_past_exam_choice_payload(
            argparse.Namespace(year=route.get("year"), period=route.get("period"), count=route.get("count", 5), seed=None, dry_run=not write_session_on_execute, format=args.format)
        )
    elif intent == "past_exam_case":
        payload["result"] = build_past_exam_case_payload(
            argparse.Namespace(year=route.get("year"), period=route.get("period"), count=route.get("count", 1), seed=None, show_answer=False, dry_run=not write_session_on_execute, format=args.format)
        )
    elif intent == "past_exam_paper":
        payload["result"] = build_past_exam_paper_payload(
            argparse.Namespace(year=route.get("year"), period=route.get("period"), count=route.get("count", 5), topic=None, seed=None, format=args.format)
        )
    elif intent == "standards_training":
        payload["result"] = build_standards_start_payload(
            argparse.Namespace(document=route.get("document"), keyword=None, tag=None, count=route.get("count", 5), seed=None, dry_run=not write_session_on_execute, format=args.format)
        )
    elif intent == "standards_clauses":
        payload["result"] = build_standards_clauses_payload(
            argparse.Namespace(document=route.get("document"), keyword=None, tag=None, limit=10, format=args.format)
        )
    elif intent == "coverage":
        payload["result"] = build_coverage_payload(argparse.Namespace(limit=10, threshold=0.7, min_attempts=2))
    elif intent == "audit":
        payload["result"] = build_audit_payload(argparse.Namespace(limit=10, min_explanation_length=30))
    elif intent == "fix_quality":
        payload["result"] = build_quality_fix_payload(argparse.Namespace(write=False, fix_options=True, rebalance_answers=True, answer_max_ratio=0.44, rebalance_difficulty=True, min_hard_ratio=0.06, min_explanation_length=30, audit_limit=10, format=args.format))
    elif intent == "paper_reference":
        payload["result"] = build_paper_reference_payload(argparse.Namespace(topic=route.get("topic"), scenario=route.get("scenario"), format=args.format))
    elif intent == "paper_start":
        payload["result"] = build_paper_payload(argparse.Namespace(topic=route.get("topic"), limit=12, format=args.format))
    elif intent == "start":
        mode = route.get("mode", "practice")
        start_args = argparse.Namespace(mode=mode, chapters=route.get("chapters"), count=route.get("count", 5), difficulty=None, knowledge_point=None, section=None, tag=route.get("tag"), seed=None, dry_run=not write_session_on_execute, format=args.format)
        if mode == "mock":
            payload["result"] = build_start_payload(start_args, write=write_session_on_execute)
        else:
            session, selected = build_wrong(start_args) if mode == "wrong" else build_practice(start_args)
            next_step = f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown"
            payload["result"] = {"session": session, "session_file": session_file_value(session, write_session_on_execute), "questions": [public_question(question) for question in selected], "next_step": session_next_step(next_step, write_session_on_execute)}
    elif intent == "case_start":
        case_args = argparse.Namespace(chapters=route.get("chapters") or case_range_chapters_text(), count=1, difficulty=None, seed=None, source=route.get("source"), dry_run=not write_session_on_execute, format=args.format)
        payload["result"] = build_case_start_payload(case_args, write=write_session_on_execute)
    elif intent == "review":
        payload["result"] = {"due": due_items(20)}
    return payload


def render_ask_markdown(payload: dict[str, Any]) -> str:
    route = payload["route"]
    lines = ["# 自然语言路由", "", f"- 识别意图：{route['intent']}", f"- 建议命令：{display_command(route['command'])}"]
    if route.get("needs_input"):
        lines.append(f"- 需要补充：{route['needs_input']}")
        return "\n".join(lines) + "\n"
    result = payload.get("result")
    if result is None:
        return "\n".join(lines) + "\n"
    lines.append("")
    if route["intent"] == "dashboard":
        lines.append(render_dashboard_markdown(result).rstrip())
    elif route["intent"] == "continue":
        lines.append(render_continue_markdown(result).rstrip())
    elif route["intent"] == "submit_latest":
        lines.append(render_submit_latest_markdown(result).rstrip())
    elif route["intent"] == "sprint":
        lines.append(render_sprint_markdown(result).rstrip())
    elif route["intent"] == "readiness":
        lines.append(render_readiness_markdown(result).rstrip())
    elif route["intent"] == "mastery":
        lines.append(render_mastery_markdown(result).rstrip())
    elif route["intent"] == "plan":
        lines.append(render_plan_markdown(result).rstrip())
    elif route["intent"] == "drill":
        lines.append(render_drill_markdown(result).rstrip())
    elif route["intent"] == "root_cause":
        lines.append(render_root_cause_markdown(result).rstrip())
    elif route["intent"] == "report":
        lines.append(render_report_markdown(result).rstrip())
    elif route["intent"] == "regression":
        from study_modules.regression import render_regression_markdown

        lines.append(render_regression_markdown(result).rstrip())
    elif route["intent"] == "profile":
        lines.append(render_profile_markdown(result).rstrip())
    elif route["intent"] == "profile_update":
        lines.append(render_profile_update_markdown(result).rstrip())
    elif route["intent"] == "exam_guide":
        lines.append(render_exam_guide_markdown(result).rstrip())
    elif route["intent"] == "internal_material":
        lines.append(render_internal_material_markdown(result).rstrip())
    elif route["intent"] == "vip_material":
        lines.append(render_vip_material_markdown(result).rstrip())
    elif route["intent"] == "sprint_material":
        lines.append(render_sprint_material_markdown(result).rstrip())
    elif route["intent"] == "sprint_training_cards":
        lines.append(render_sprint_training_cards_markdown(result).rstrip())
    elif route["intent"] == "sprint_training_start":
        lines.append(render_sprint_training_start_markdown(result).rstrip())
    elif route["intent"] == "sprint_training_case":
        lines.append(render_sprint_training_case_markdown(result).rstrip())
    elif route["intent"] == "search":
        lines.append(render_search_markdown(result).rstrip())
    elif route["intent"] == "backup_pdfs":
        lines.append(render_backup_pdf_markdown(result).rstrip())
    elif route["intent"] == "candidate_practice":
        lines.append(render_candidate_practice_markdown(result).rstrip())
    elif route["intent"] == "recitation":
        lines.append(render_recitation_markdown(result).rstrip())
    elif route["intent"] == "past_exam_choice":
        lines.append(render_past_exam_choice_markdown(result).rstrip())
    elif route["intent"] == "past_exam_case":
        lines.append(render_past_exam_case_markdown(result).rstrip())
    elif route["intent"] == "past_exam_paper":
        lines.append(render_past_exam_paper_markdown(result).rstrip())
    elif route["intent"] == "standards_training":
        lines.append(render_standards_start_markdown(result).rstrip())
    elif route["intent"] == "standards_clauses":
        lines.append(render_standards_clauses_markdown(result).rstrip())
    elif route["intent"] == "coverage":
        lines.append(render_coverage_markdown(result).rstrip())
    elif route["intent"] == "audit":
        lines.append(render_audit_markdown(result).rstrip())
    elif route["intent"] == "fix_quality":
        lines.append(render_quality_fix_markdown(result).rstrip())
    elif route["intent"] == "paper_reference":
        lines.append(render_paper_reference_markdown(result).rstrip())
    elif route["intent"] == "paper_start":
        lines.append(render_paper_markdown(result).rstrip())
    elif route["intent"] in {"practice", "wrong_retry"}:
        lines.append(f"Session: {result['session']['id']}")
        lines.append(f"File: {result['session_file']}")
        lines.append("")
        lines.append(render_questions_markdown(result["questions"]).rstrip())
        lines.append(f"Next: {display_command(result['next_step'])}")
    elif route["intent"] == "case_start":
        lines.append(f"Session: {result['session']['id']}")
        lines.append(f"File: {result['session_file']}")
        for case in result["cases"]:
            lines.append("")
            lines.append(render_case_markdown(case).rstrip())
        lines.append(f"Next: {display_command(result['next_step'])}")
    elif route["intent"] == "review":
        due = result["due"]
        lines.append(f"到期复习：{len(due)}题")
        for item in due:
            archive_item = item["archive"]
            question = item.get("question") or {}
            lines.append(f"- {archive_item.get('question_id')}: {question.get('question')}")
    return "\n".join(lines) + "\n"


def command_ask(args: argparse.Namespace) -> int:
    payload = build_ask_payload(args)
    if args.format == "markdown":
        print(render_ask_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
