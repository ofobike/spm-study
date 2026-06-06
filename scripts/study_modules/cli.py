from __future__ import annotations

import argparse

from study_modules.ask import command_ask
from study_modules.case import command_case_start, command_case_submit
from study_modules.materials import (
    command_backup_pdfs,
    command_candidate_practice,
    command_exam_guide,
    command_internal_material,
    command_recitation,
    command_sprint_material,
    command_vip_material,
)
from study_modules.mastery import command_coverage, command_mastery
from study_modules.paper import command_paper, command_paper_reference, command_paper_submit
from study_modules.past_exam import command_past_exam_case, command_past_exam_paper, command_past_exam_start
from study_modules.profile import command_profile, command_profile_update
from study_modules.quality import command_audit, command_fix_quality
from study_modules.regression import command_regression
from study_modules.reports import (
    command_dashboard,
    command_plan,
    command_readiness,
    command_report,
    command_root_cause,
    command_sprint,
    command_status,
)
from study_modules.search_training import (
    command_search,
    command_sprint_training_cards,
    command_sprint_training_case,
    command_sprint_training_start,
)
from study_modules.session_flow import command_continue, command_drill, command_review, command_start, command_submit
from study_modules.settings import DEFAULT_OUTPUT_FORMAT, DEFAULT_PAPER_TOPIC, SEARCH_SOURCE_TYPES, SPRINT_KINDS
from study_modules.standards import command_standards_clauses, command_standards_list, command_standards_start


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a complete study loop.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    dry_run_help = "Preview the session without writing a file under assets/questions/sessions."

    start = subparsers.add_parser("start", help="Start a practice or mock-exam session.")
    start.add_argument("--mode", choices=["practice", "mock", "wrong"], default="practice")
    start.add_argument("--chapters", default=None)
    start.add_argument("--count", type=int, default=5)
    start.add_argument("--difficulty", choices=["easy", "medium", "hard"], default=None)
    start.add_argument("--knowledge-point", default=None)
    start.add_argument("--section", default=None)
    start.add_argument("--tag", default=None)
    start.add_argument("--seed", type=int, default=None)
    start.add_argument("--dry-run", "--no-write-session", dest="dry_run", action="store_true", help=dry_run_help)
    start.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    start.set_defaults(func=command_start)

    submit = subparsers.add_parser("submit", help="Submit answers, grade, and record progress.")
    submit.add_argument("--session", required=True)
    submit.add_argument("--answers", required=True, help='Answer text such as "A B C" or "ch01_q001=A,ch01_q002=B".')
    submit.add_argument("--no-record", action="store_true", help="Grade without writing progress/archive files.")
    submit.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    submit.set_defaults(func=command_submit)

    review = subparsers.add_parser("review", help="Show due reviews or mark reviewed questions.")
    review.add_argument("--date", default=None)
    review.add_argument("--limit", type=int, default=20)
    review.add_argument("--mark-reviewed", nargs="*", default=None)
    review.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    review.set_defaults(func=command_review)

    status = subparsers.add_parser("status", help="Show learning status and next action.")
    status.add_argument("--limit", type=int, default=10)
    status.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    status.set_defaults(func=command_status)

    plan = subparsers.add_parser("plan", help="Generate a daily study plan.")
    plan.add_argument("--review-limit", type=int, default=10)
    plan.add_argument("--weak-limit", type=int, default=5)
    plan.add_argument("--practice-count", type=int, default=5)
    plan.add_argument("--default-chapter", type=int, default=12)
    plan.add_argument("--include-mock", action="store_true")
    plan.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    plan.set_defaults(func=command_plan)

    profile = subparsers.add_parser("profile", help="Show learner profile and personalization settings.")
    profile.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    profile.set_defaults(func=command_profile)

    profile_update = subparsers.add_parser("profile-update", help="Preview or write learner profile updates from natural language.")
    profile_update.add_argument("text")
    profile_update.add_argument("--write", action="store_true", help="Write recognized non-sensitive fields into assets/profile/learner_profile.json.")
    profile_update.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    profile_update.set_defaults(func=command_profile_update)

    exam_guide = subparsers.add_parser("exam-guide", help="Show exam schedule, subject ranges, and chapter priorities from internal guide/syllabus.")
    exam_guide.add_argument("--limit", type=int, default=8)
    exam_guide.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    exam_guide.set_defaults(func=command_exam_guide)

    internal = subparsers.add_parser("internal", help="Read structured internal notes or mindmaps by chapter.")
    internal.add_argument("--kind", choices=["notes", "mindmap"], default="notes")
    internal.add_argument("--chapter", type=int, default=None)
    internal.add_argument("--preview-lines", type=int, default=10)
    internal.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    internal.set_defaults(func=command_internal_material)

    vip = subparsers.add_parser("vip", help="List or preview indexed VIP materials.")
    vip.add_argument("--kind", choices=["all", "comprehensive", "chapter-practice-answer", "chapter-practice-blank", "theory-core", "notes-summary", "other"], default="all")
    vip.add_argument("--keyword", default=None)
    vip.add_argument("--limit", type=int, default=10)
    vip.add_argument("--preview-lines", type=int, default=8)
    vip.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    vip.set_defaults(func=command_vip_material)

    sprint_materials = subparsers.add_parser("sprint-materials", help="List or preview indexed sprint/cram materials.")
    sprint_materials.add_argument("--kind", choices=["all", "mnemonic", "gold-points", "mock-exam", "csf-risk", "activities", "sprint-guide"], default="all")
    sprint_materials.add_argument("--keyword", default=None)
    sprint_materials.add_argument("--limit", type=int, default=10)
    sprint_materials.add_argument("--preview-lines", type=int, default=8)
    sprint_materials.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    sprint_materials.set_defaults(func=command_sprint_material)

    sprint_training = subparsers.add_parser("sprint-training", help="Run structured training generated from sprint/cram materials.")
    sprint_training_subparsers = sprint_training.add_subparsers(dest="sprint_training_command", required=True)
    sprint_cards = sprint_training_subparsers.add_parser("cards", help="Practice recall cards from sprint materials.")
    sprint_cards.add_argument("--kind", choices=list(SPRINT_KINDS), default="all")
    sprint_cards.add_argument("--keyword", default=None)
    sprint_cards.add_argument("--count", type=int, default=5)
    sprint_cards.add_argument("--seed", type=int, default=None)
    sprint_cards.add_argument("--show-answer", action="store_true")
    sprint_cards.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    sprint_cards.set_defaults(func=command_sprint_training_cards)
    sprint_start = sprint_training_subparsers.add_parser("start", help="Start a sprint mock candidate choice-question session.")
    sprint_start.add_argument("--kind", choices=list(SPRINT_KINDS), default="all")
    sprint_start.add_argument("--keyword", default=None)
    sprint_start.add_argument("--count", type=int, default=5)
    sprint_start.add_argument("--seed", type=int, default=None)
    sprint_start.add_argument("--dry-run", "--no-write-session", dest="dry_run", action="store_true", help=dry_run_help)
    sprint_start.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    sprint_start.set_defaults(func=command_sprint_training_start)
    sprint_case = sprint_training_subparsers.add_parser("case", help="Practice sprint case-analysis scoring points.")
    sprint_case.add_argument("--kind", choices=list(SPRINT_KINDS), default="all")
    sprint_case.add_argument("--keyword", default=None)
    sprint_case.add_argument("--count", type=int, default=3)
    sprint_case.add_argument("--seed", type=int, default=None)
    sprint_case.add_argument("--show-answer", action="store_true")
    sprint_case.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    sprint_case.set_defaults(func=command_sprint_training_case)

    search = subparsers.add_parser("search", help="Search across all indexed study materials with source citations.")
    search.add_argument("query")
    search.add_argument("--source-type", choices=list(SEARCH_SOURCE_TYPES), default=None)
    search.add_argument("--chapter", type=int, default=None)
    search.add_argument("--limit", type=int, default=8)
    search.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    search.set_defaults(func=command_search)

    backup_pdfs = subparsers.add_parser("backup-pdfs", help="List indexed PDFs imported from F:\\备份项目.")
    backup_pdfs.add_argument("--category", choices=["all", "past-exam", "standards", "mock"], default="all")
    backup_pdfs.add_argument("--year", type=int, default=None)
    backup_pdfs.add_argument("--subject", default=None)
    backup_pdfs.add_argument("--limit", type=int, default=20)
    backup_pdfs.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    backup_pdfs.set_defaults(func=command_backup_pdfs)

    past_exam = subparsers.add_parser("past-exam", help="Run structured 2017-2024 past-exam training.")
    past_exam_subparsers = past_exam.add_subparsers(dest="past_exam_command", required=True)
    past_exam_start = past_exam_subparsers.add_parser("start", help="Start a past-exam morning choice session.")
    past_exam_start.add_argument("--year", type=int, default=None)
    past_exam_start.add_argument("--period", choices=["上半年", "下半年"], default=None)
    past_exam_start.add_argument("--count", type=int, default=5)
    past_exam_start.add_argument("--seed", type=int, default=None)
    past_exam_start.add_argument("--dry-run", "--no-write-session", dest="dry_run", action="store_true", help=dry_run_help)
    past_exam_start.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    past_exam_start.set_defaults(func=command_past_exam_start)
    past_exam_case = past_exam_subparsers.add_parser("case", help="Start a past-exam case-analysis session.")
    past_exam_case.add_argument("--year", type=int, default=None)
    past_exam_case.add_argument("--period", choices=["上半年", "下半年"], default=None)
    past_exam_case.add_argument("--count", type=int, default=1)
    past_exam_case.add_argument("--seed", type=int, default=None)
    past_exam_case.add_argument("--show-answer", action="store_true")
    past_exam_case.add_argument("--dry-run", "--no-write-session", dest="dry_run", action="store_true", help=dry_run_help)
    past_exam_case.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    past_exam_case.set_defaults(func=command_past_exam_case)
    past_exam_paper = past_exam_subparsers.add_parser("paper", help="Show past-exam paper topics.")
    past_exam_paper.add_argument("--year", type=int, default=None)
    past_exam_paper.add_argument("--period", choices=["上半年", "下半年"], default=None)
    past_exam_paper.add_argument("--topic", default=None)
    past_exam_paper.add_argument("--count", type=int, default=5)
    past_exam_paper.add_argument("--seed", type=int, default=None)
    past_exam_paper.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    past_exam_paper.set_defaults(func=command_past_exam_paper)

    standards = subparsers.add_parser("standards", help="Run structured standards/laws training from 07-标准规范库.")
    standards_subparsers = standards.add_subparsers(dest="standards_command", required=True)
    standards_list = standards_subparsers.add_parser("list", help="List structured standards documents and OCR gaps.")
    standards_list.add_argument("--document", default=None)
    standards_list.add_argument("--tag", default=None)
    standards_list.add_argument("--limit", type=int, default=20)
    standards_list.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    standards_list.set_defaults(func=command_standards_list)
    standards_clauses = standards_subparsers.add_parser("clauses", help="Search structured standards clauses.")
    standards_clauses.add_argument("--document", default=None)
    standards_clauses.add_argument("--keyword", default=None)
    standards_clauses.add_argument("--tag", default=None)
    standards_clauses.add_argument("--limit", type=int, default=10)
    standards_clauses.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    standards_clauses.set_defaults(func=command_standards_clauses)
    standards_start = standards_subparsers.add_parser("start", help="Start a standards/laws single-choice training session.")
    standards_start.add_argument("--document", default=None)
    standards_start.add_argument("--keyword", default=None)
    standards_start.add_argument("--tag", default=None)
    standards_start.add_argument("--count", type=int, default=5)
    standards_start.add_argument("--seed", type=int, default=None)
    standards_start.add_argument("--dry-run", "--no-write-session", dest="dry_run", action="store_true", help=dry_run_help)
    standards_start.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    standards_start.set_defaults(func=command_standards_start)

    candidate = subparsers.add_parser("candidate", help="Preview internal chapter-practice candidate questions without recording progress.")
    candidate.add_argument("--chapter", type=int, default=None)
    candidate.add_argument("--count", type=int, default=5)
    candidate.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    candidate.set_defaults(func=command_candidate_practice)

    recite = subparsers.add_parser("recite", help="Preview internal case-recitation prompts and optional scoring points.")
    recite.add_argument("--chapter", type=int, default=None)
    recite.add_argument("--count", type=int, default=5)
    recite.add_argument("--show-answer", action="store_true")
    recite.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    recite.set_defaults(func=command_recitation)

    paper_ref = subparsers.add_parser("paper-ref", help="Show structured internal paper guidance, rubric, framework, and sample references.")
    paper_ref.add_argument("--topic", default=DEFAULT_PAPER_TOPIC)
    paper_ref.add_argument("--scenario", choices=["政务", "医院", "制造"], default=None)
    paper_ref.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    paper_ref.set_defaults(func=command_paper_reference)

    paper = subparsers.add_parser("paper", help="Run paper-writing practice.")
    paper.add_argument("--topic", default=DEFAULT_PAPER_TOPIC, help="Paper topic, default follows the new syllabus range: chapters 4-17.")
    paper.add_argument("--limit", type=int, default=12, help="Number of knowledge points to include.")
    paper.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    paper.set_defaults(func=command_paper)
    paper_subparsers = paper.add_subparsers(dest="paper_command")
    paper_start = paper_subparsers.add_parser("start", help="Generate a paper-writing practice loop.")
    paper_start.add_argument("--topic", default=DEFAULT_PAPER_TOPIC)
    paper_start.add_argument("--limit", type=int, default=12)
    paper_start.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    paper_start.set_defaults(func=command_paper)
    paper_submit = paper_subparsers.add_parser("submit", help="Score a paper draft and return revision advice.")
    paper_submit.add_argument("--topic", default=DEFAULT_PAPER_TOPIC)
    paper_submit.add_argument("--draft", default=None, help="Markdown/text file containing the draft.")
    paper_submit.add_argument("--text", default=None, help="Draft text passed directly on the command line.")
    paper_submit.add_argument("--min-chars", type=int, default=800)
    paper_submit.add_argument("--no-record", action="store_true", help="Score without writing paper attempt history.")
    paper_submit.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    paper_submit.set_defaults(func=command_paper_submit)

    coverage = subparsers.add_parser("coverage", help="Report knowledge-point coverage from question metadata and progress.")
    coverage.add_argument("--limit", type=int, default=10)
    coverage.add_argument("--threshold", type=float, default=0.7, help="Accuracy threshold for low-accuracy points, e.g. 0.7.")
    coverage.add_argument("--min-attempts", type=int, default=2)
    coverage.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    coverage.set_defaults(func=command_coverage)

    audit = subparsers.add_parser("audit", help="Audit question-bank quality without changing data.")
    audit.add_argument("--limit", type=int, default=30)
    audit.add_argument("--min-explanation-length", type=int, default=30)
    audit.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    audit.set_defaults(func=command_audit)

    fix_quality = subparsers.add_parser("fix-quality", help="Preview or apply safe question-bank quality fixes.")
    fix_quality.add_argument("--write", action="store_true", help="Write safe fixes to chapter question files.")
    fix_quality.add_argument("--fix-options", action="store_true", help="Also replace obvious template distractor words in question/options/explanation text.")
    fix_quality.add_argument("--rebalance-answers", action="store_true", help="Reorder options to reduce A/B/C/D answer skew without changing option content.")
    fix_quality.add_argument("--answer-max-ratio", type=float, default=0.44)
    fix_quality.add_argument("--rebalance-difficulty", action="store_true", help="Promote high-cognitive-load medium questions to hard until the hard ratio is healthier.")
    fix_quality.add_argument("--min-hard-ratio", type=float, default=0.06)
    fix_quality.add_argument("--min-explanation-length", type=int, default=30)
    fix_quality.add_argument("--audit-limit", type=int, default=30)
    fix_quality.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    fix_quality.set_defaults(func=command_fix_quality)

    dashboard = subparsers.add_parser("dashboard", help="Show a learning dashboard and next actions.")
    dashboard.add_argument("--limit", type=int, default=6)
    dashboard.add_argument("--include-audit", action="store_true", default=True)
    dashboard.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    dashboard.set_defaults(func=command_dashboard)

    mastery = subparsers.add_parser("mastery", help="Score mastery for each knowledge point.")
    mastery.add_argument("--chapter", type=int, default=None)
    mastery.add_argument("--limit", type=int, default=10)
    mastery.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    mastery.set_defaults(func=command_mastery)

    continue_cmd = subparsers.add_parser("continue", help="Resume the latest unfinished session.")
    continue_cmd.add_argument("--type", choices=["practice", "mock_exam", "wrong_retry", "drill", "case_study", "past_exam", "past_exam_case", "standards_training", "sprint_training"], default=None)
    continue_cmd.add_argument("--any", action="store_true", help="Allow completed sessions when no unfinished session is available.")
    continue_cmd.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    continue_cmd.set_defaults(func=command_continue)

    drill = subparsers.add_parser("drill", help="Create a personalized drill from weak mastery points.")
    drill.add_argument("--chapter", type=int, default=None)
    drill.add_argument("--count", type=int, default=5)
    drill.add_argument("--difficulty", choices=["easy", "medium", "hard"], default=None)
    drill.add_argument("--seed", type=int, default=None)
    drill.add_argument("--dry-run", "--no-write-session", dest="dry_run", action="store_true", help=dry_run_help)
    drill.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    drill.set_defaults(func=command_drill)

    root_cause = subparsers.add_parser("root-cause", help="Analyze wrong-answer root causes.")
    root_cause.add_argument("--session", default=None)
    root_cause.add_argument("--limit", type=int, default=10)
    root_cause.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    root_cause.set_defaults(func=command_root_cause)

    report = subparsers.add_parser("report", help="Export weekly/monthly/exam diagnostic study reports.")
    report.add_argument("--period", choices=["weekly", "monthly", "exam"], default="weekly")
    report.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    report.set_defaults(func=command_report)

    regression = subparsers.add_parser("regression", help="Run built-in smoke/regression tests for the skill.")
    regression.add_argument("--verbose", action="store_true")
    regression.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    regression.set_defaults(func=command_regression)

    readiness = subparsers.add_parser("readiness", help="Score exam readiness across knowledge, case, paper, review, and mock practice.")
    readiness.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    readiness.set_defaults(func=command_readiness)

    sprint = subparsers.add_parser("sprint", help="Generate a sprint study plan.")
    sprint.add_argument("--days", type=int, default=14)
    sprint.add_argument("--include-audit", action="store_true", default=True)
    sprint.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    sprint.set_defaults(func=command_sprint)

    ask = subparsers.add_parser("ask", help="Route a natural-language study request.")
    ask.add_argument("text")
    ask.add_argument("--execute", action="store_true", default=True)
    ask.add_argument("--no-record", action="store_true", help="When routing an answer submission, grade without writing progress/archive files.")
    ask.add_argument("--dry-run", "--no-write-session", dest="dry_run", action="store_true", help="When routing a start command or profile write, preview without writing session/profile files.")
    ask.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    ask.set_defaults(func=command_ask)

    case = subparsers.add_parser("case", help="Run case-study practice.")
    case_subparsers = case.add_subparsers(dest="case_command", required=True)
    case_start = case_subparsers.add_parser("start", help="Start case-study practice.")
    case_start.add_argument("--chapters", default=None)
    case_start.add_argument("--count", type=int, default=1)
    case_start.add_argument("--difficulty", choices=["easy", "medium", "hard"], default=None)
    case_start.add_argument("--source", choices=["all", "scenario", "recitation"], default="all", help="Filter formal cases: all, scenario cases, or promoted recitation cases.")
    case_start.add_argument("--seed", type=int, default=None)
    case_start.add_argument("--dry-run", "--no-write-session", dest="dry_run", action="store_true", help=dry_run_help)
    case_start.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    case_start.set_defaults(func=command_case_start)

    case_submit = case_subparsers.add_parser("submit", help="Submit case-study answers.")
    case_submit.add_argument("--session", required=True)
    case_submit.add_argument("--answers", required=True)
    case_submit.add_argument("--no-record", action="store_true", help="Grade without writing case attempt history.")
    case_submit.add_argument("--format", choices=["json", "markdown"], default=DEFAULT_OUTPUT_FORMAT)
    case_submit.set_defaults(func=command_case_submit)
    return parser
