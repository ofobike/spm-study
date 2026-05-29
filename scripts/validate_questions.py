#!/usr/bin/env python3
"""Validate question assets for the spm-study skill."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_DIR = ROOT / "assets" / "questions"
CHAPTERS_DIR = QUESTIONS_DIR / "chapters"
EXPECTED_CHAPTERS = 24
MIN_QUESTIONS_PER_CHAPTER = 50
CHOICES = {"A", "B", "C", "D"}
DIFFICULTIES = {"easy", "medium", "hard"}
QUESTION_TYPES = {"single_choice"}
METADATA_FIELDS = ("question_type", "difficulty", "section", "knowledge_point", "source_ref", "tags")


def load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:  # noqa: BLE001 - keep validation output concise.
        raise ValueError(f"{path.relative_to(ROOT)} is not valid JSON: {exc}") from exc


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_chapter_questions(errors: list[str]) -> tuple[int, set[str], dict[str, int]]:
    total = 0
    seen_ids: set[str] = set()
    by_chapter_counts: dict[str, int] = {}
    files = sorted(CHAPTERS_DIR.glob("chapter_*.json"))

    require(
        len(files) == EXPECTED_CHAPTERS,
        f"expected {EXPECTED_CHAPTERS} chapter files, found {len(files)}",
        errors,
    )

    for chapter_no in range(1, EXPECTED_CHAPTERS + 1):
        path = CHAPTERS_DIR / f"chapter_{chapter_no:02d}.json"
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")
            continue

        data = load_json(path)
        rel = path.relative_to(ROOT)
        require(isinstance(data, list), f"{rel} root must be a list", errors)
        if not isinstance(data, list):
            continue

        total += len(data)
        by_chapter_counts[f"chapter_{chapter_no:02d}"] = len(data)
        require(
            len(data) >= MIN_QUESTIONS_PER_CHAPTER,
            f"{rel} expected at least {MIN_QUESTIONS_PER_CHAPTER} questions, found {len(data)}",
            errors,
        )

        expected_chapter = f"第{chapter_no}章"
        expected_prefix = f"ch{chapter_no:02d}_q"
        for index, question in enumerate(data, start=1):
            where = f"{rel}[{index}]"
            require(isinstance(question, dict), f"{where} must be an object", errors)
            if not isinstance(question, dict):
                continue

            for key in ("id", "question", "options", "answer", "explanation", "chapter", "source"):
                require(key in question, f"{where} missing field: {key}", errors)
            for key in METADATA_FIELDS:
                require(key in question, f"{where} missing metadata field: {key}", errors)

            qid = question.get("id")
            if isinstance(qid, str):
                require(qid.startswith(expected_prefix), f"{where} id should start with {expected_prefix}", errors)
                if qid in seen_ids:
                    errors.append(f"duplicate question id: {qid}")
                seen_ids.add(qid)
            else:
                errors.append(f"{where} id must be a string")

            options = question.get("options")
            require(isinstance(options, list) and len(options) == 4, f"{where} options must contain 4 choices", errors)
            answer = question.get("answer")
            require(answer in CHOICES, f"{where} answer must be one of A/B/C/D", errors)
            require(question.get("chapter") == expected_chapter, f"{where} chapter should be {expected_chapter}", errors)
            require(question.get("question_type") in QUESTION_TYPES, f"{where} question_type must be single_choice", errors)
            require(question.get("difficulty") in DIFFICULTIES, f"{where} difficulty must be easy/medium/hard", errors)
            require(isinstance(question.get("section"), str) and bool(question.get("section")), f"{where} section must be a non-empty string", errors)
            require(
                isinstance(question.get("knowledge_point"), str) and bool(question.get("knowledge_point")),
                f"{where} knowledge_point must be a non-empty string",
                errors,
            )
            source_ref = question.get("source_ref")
            require(
                isinstance(source_ref, str) and source_ref.startswith("references/") and ".md#" in source_ref,
                f"{where} source_ref must point to a references markdown anchor",
                errors,
            )
            tags = question.get("tags")
            require(isinstance(tags, list) and 1 <= len(tags) <= 5, f"{where} tags must contain 1-5 items", errors)
            if isinstance(tags, list):
                require(all(isinstance(tag, str) and tag for tag in tags), f"{where} tags must be non-empty strings", errors)
                require(len(tags) == len(set(tags)), f"{where} tags must not contain duplicates", errors)

    return total, seen_ids, by_chapter_counts


def validate_case_studies(errors: list[str]) -> tuple[int, int]:
    path = QUESTIONS_DIR / "case_studies.json"
    data = load_json(path)
    rel = path.relative_to(ROOT)
    require(isinstance(data, dict), f"{rel} root must be an object", errors)
    if not isinstance(data, dict):
        return 0, 0

    cases = data.get("case_studies")
    require(isinstance(cases, list), f"{rel} case_studies must be a list", errors)
    if not isinstance(cases, list):
        return 0, 0

    total_cases = len(cases)
    total_sub_questions = 0
    seen_ids: set[str] = set()

    for index, case in enumerate(cases, start=1):
        where = f"{rel}.case_studies[{index}]"
        require(isinstance(case, dict), f"{where} must be an object", errors)
        if not isinstance(case, dict):
            continue

        for key in ("id", "chapter", "title", "scenario", "questions"):
            require(key in case, f"{where} missing field: {key}", errors)

        case_id = case.get("id")
        if isinstance(case_id, str):
            if case_id in seen_ids:
                errors.append(f"duplicate case id: {case_id}")
            seen_ids.add(case_id)
        else:
            errors.append(f"{where} id must be a string")

        questions = case.get("questions")
        require(isinstance(questions, list) and len(questions) >= 1, f"{where} questions must be a non-empty list", errors)
        if not isinstance(questions, list):
            continue

        total_sub_questions += len(questions)
        for q_index, question in enumerate(questions, start=1):
            q_where = f"{where}.questions[{q_index}]"
            require(isinstance(question, dict), f"{q_where} must be an object", errors)
            if not isinstance(question, dict):
                continue
            for key in ("id", "question", "answer"):
                require(key in question, f"{q_where} missing field: {key}", errors)

    require(
        data.get("total_case_studies") == total_cases,
        f"{rel} total_case_studies should be {total_cases}, found {data.get('total_case_studies')}",
        errors,
    )
    require(
        data.get("total_sub_questions") == total_sub_questions,
        f"{rel} total_sub_questions should be {total_sub_questions}, found {data.get('total_sub_questions')}",
        errors,
    )

    return total_cases, total_sub_questions


def validate_index(total_questions: int, total_cases: int, total_sub_questions: int, by_chapter_counts: dict[str, int], errors: list[str]) -> None:
    path = QUESTIONS_DIR / "index.json"
    data = load_json(path)
    rel = path.relative_to(ROOT)
    require(isinstance(data, dict), f"{rel} root must be an object", errors)
    if not isinstance(data, dict):
        return

    require(
        data.get("total_questions") == total_questions,
        f"{rel} total_questions should be {total_questions}, found {data.get('total_questions')}",
        errors,
    )
    require(
        data.get("total_cases") == total_cases,
        f"{rel} total_cases should be {total_cases}, found {data.get('total_cases')}",
        errors,
    )
    require(
        data.get("total_sub_questions") == total_sub_questions,
        f"{rel} total_sub_questions should be {total_sub_questions}, found {data.get('total_sub_questions')}",
        errors,
    )

    by_chapter = data.get("by_chapter")
    require(isinstance(by_chapter, dict), f"{rel} by_chapter must be an object", errors)
    if isinstance(by_chapter, dict):
        for chapter_no in range(1, EXPECTED_CHAPTERS + 1):
            key = f"chapter_{chapter_no:02d}"
            expected = by_chapter_counts.get(key)
            require(by_chapter.get(key) == expected, f"{rel} {key} should be {expected}", errors)


def validate_other_json(errors: list[str]) -> None:
    for filename in ("archive.json", "mock_exam_config.json", "config.json", "progress.json"):
        load_json(QUESTIONS_DIR / filename)


def validate_past_exams(errors: list[str]) -> tuple[int, int, int]:
    path = QUESTIONS_DIR / "past_exams.json"
    data = load_json(path)
    rel = path.relative_to(ROOT)
    require(isinstance(data, dict), f"{rel} root must be an object", errors)
    if not isinstance(data, dict):
        return 0, 0, 0

    choices = data.get("choice_questions")
    cases = data.get("case_studies")
    papers = data.get("paper_topics")
    require(isinstance(choices, list), f"{rel} choice_questions must be a list", errors)
    require(isinstance(cases, list), f"{rel} case_studies must be a list", errors)
    require(isinstance(papers, list), f"{rel} paper_topics must be a list", errors)
    if not isinstance(choices, list) or not isinstance(cases, list) or not isinstance(papers, list):
        return 0, 0, 0

    seen_ids: set[str] = set()
    for index, question in enumerate(choices, start=1):
        where = f"{rel}.choice_questions[{index}]"
        require(isinstance(question, dict), f"{where} must be an object", errors)
        if not isinstance(question, dict):
            continue
        for key in ("id", "year", "subject", "number", "question", "options", "answer", "source_ref"):
            require(key in question, f"{where} missing field: {key}", errors)
        qid = str(question.get("id") or "")
        require(qid.startswith("pe_"), f"{where} id should start with pe_", errors)
        if qid in seen_ids:
            errors.append(f"duplicate past exam id: {qid}")
        seen_ids.add(qid)
        require(isinstance(question.get("options"), list) and len(question.get("options", [])) == 4, f"{where} options must contain 4 choices", errors)
        require(question.get("answer") in CHOICES, f"{where} answer must be one of A/B/C/D", errors)

    total_case_questions = 0
    for index, case in enumerate(cases, start=1):
        where = f"{rel}.case_studies[{index}]"
        require(isinstance(case, dict), f"{where} must be an object", errors)
        if not isinstance(case, dict):
            continue
        for key in ("id", "year", "subject", "title", "scenario", "questions", "source_ref"):
            require(key in case, f"{where} missing field: {key}", errors)
        case_id = str(case.get("id") or "")
        if case_id in seen_ids:
            errors.append(f"duplicate past exam id: {case_id}")
        seen_ids.add(case_id)
        questions = case.get("questions")
        require(isinstance(questions, list) and bool(questions), f"{where} questions must be a non-empty list", errors)
        if isinstance(questions, list):
            total_case_questions += len(questions)
            for q_index, question in enumerate(questions, start=1):
                q_where = f"{where}.questions[{q_index}]"
                require(isinstance(question, dict), f"{q_where} must be an object", errors)
                if not isinstance(question, dict):
                    continue
                for key in ("id", "question", "question_type", "score"):
                    require(key in question, f"{q_where} missing field: {key}", errors)

    for index, paper in enumerate(papers, start=1):
        where = f"{rel}.paper_topics[{index}]"
        require(isinstance(paper, dict), f"{where} must be an object", errors)
        if not isinstance(paper, dict):
            continue
        for key in ("id", "year", "subject", "title", "prompt", "source_ref"):
            require(key in paper, f"{where} missing field: {key}", errors)
        paper_id = str(paper.get("id") or "")
        if paper_id in seen_ids:
            errors.append(f"duplicate past exam id: {paper_id}")
        seen_ids.add(paper_id)

    stats = data.get("stats", {})
    if isinstance(stats, dict):
        require(stats.get("choice_questions") == len(choices), f"{rel} stats.choice_questions should be {len(choices)}", errors)
        require(stats.get("case_studies") == len(cases), f"{rel} stats.case_studies should be {len(cases)}", errors)
        require(stats.get("case_subquestions") == total_case_questions, f"{rel} stats.case_subquestions should be {total_case_questions}", errors)
        require(stats.get("paper_topics") == len(papers), f"{rel} stats.paper_topics should be {len(papers)}", errors)

    return len(choices), len(cases), len(papers)


def validate_standards_training(errors: list[str]) -> tuple[int, int, int]:
    path = QUESTIONS_DIR / "standards_training.json"
    data = load_json(path)
    rel = path.relative_to(ROOT)
    require(isinstance(data, dict), f"{rel} root must be an object", errors)
    if not isinstance(data, dict):
        return 0, 0, 0

    documents = data.get("documents")
    clauses = data.get("clauses")
    questions = data.get("questions")
    skipped = data.get("skipped_documents")
    require(isinstance(documents, list), f"{rel} documents must be a list", errors)
    require(isinstance(clauses, list), f"{rel} clauses must be a list", errors)
    require(isinstance(questions, list), f"{rel} questions must be a list", errors)
    require(isinstance(skipped, list), f"{rel} skipped_documents must be a list", errors)
    if not isinstance(documents, list) or not isinstance(clauses, list) or not isinstance(questions, list):
        return 0, 0, 0

    seen_doc_ids: set[str] = set()
    for index, doc in enumerate(documents, start=1):
        where = f"{rel}.documents[{index}]"
        require(isinstance(doc, dict), f"{where} must be an object", errors)
        if not isinstance(doc, dict):
            continue
        for key in ("id", "title", "document_type", "source_ref", "clause_count", "needs_ocr"):
            require(key in doc, f"{where} missing field: {key}", errors)
        doc_id = str(doc.get("id") or "")
        require(doc_id.startswith("std_doc_"), f"{where} id should start with std_doc_", errors)
        if doc_id in seen_doc_ids:
            errors.append(f"duplicate standards document id: {doc_id}")
        seen_doc_ids.add(doc_id)
        source_ref = doc.get("source_ref")
        require(isinstance(source_ref, str) and source_ref.startswith("references/") and source_ref.endswith(".md"), f"{where} source_ref must point to references markdown", errors)

    seen_clause_ids: set[str] = set()
    clause_doc_counts: dict[str, int] = {}
    for index, clause in enumerate(clauses, start=1):
        where = f"{rel}.clauses[{index}]"
        require(isinstance(clause, dict), f"{where} must be an object", errors)
        if not isinstance(clause, dict):
            continue
        for key in ("id", "document_id", "title", "text", "summary", "source_ref", "tags"):
            require(key in clause, f"{where} missing field: {key}", errors)
        clause_id = str(clause.get("id") or "")
        require(clause_id.startswith("std_clause_"), f"{where} id should start with std_clause_", errors)
        if clause_id in seen_clause_ids:
            errors.append(f"duplicate standards clause id: {clause_id}")
        seen_clause_ids.add(clause_id)
        doc_id = str(clause.get("document_id") or "")
        require(doc_id in seen_doc_ids, f"{where} document_id must reference a standards document", errors)
        clause_doc_counts[doc_id] = clause_doc_counts.get(doc_id, 0) + 1
        source_ref = clause.get("source_ref")
        require(isinstance(source_ref, str) and source_ref.startswith("references/") and source_ref.endswith(".md"), f"{where} source_ref must point to references markdown", errors)
        tags = clause.get("tags")
        require(isinstance(tags, list) and 1 <= len(tags) <= 5, f"{where} tags must contain 1-5 items", errors)

    for doc in documents:
        if isinstance(doc, dict):
            doc_id = str(doc.get("id") or "")
            require(doc.get("clause_count") == clause_doc_counts.get(doc_id, 0), f"{rel} {doc_id} clause_count should be {clause_doc_counts.get(doc_id, 0)}", errors)

    seen_question_ids: set[str] = set()
    for index, question in enumerate(questions, start=1):
        where = f"{rel}.questions[{index}]"
        require(isinstance(question, dict), f"{where} must be an object", errors)
        if not isinstance(question, dict):
            continue
        for key in ("id", "question", "options", "answer", "explanation", "document_id", "clause_id", "source_ref", "tags"):
            require(key in question, f"{where} missing field: {key}", errors)
        qid = str(question.get("id") or "")
        require(qid.startswith("std_q"), f"{where} id should start with std_q", errors)
        if qid in seen_question_ids:
            errors.append(f"duplicate standards question id: {qid}")
        seen_question_ids.add(qid)
        require(question.get("document_id") in seen_doc_ids, f"{where} document_id must reference a standards document", errors)
        require(question.get("clause_id") in seen_clause_ids, f"{where} clause_id must reference a standards clause", errors)
        require(isinstance(question.get("options"), list) and len(question.get("options", [])) == 4, f"{where} options must contain 4 choices", errors)
        require(question.get("answer") in CHOICES, f"{where} answer must be one of A/B/C/D", errors)
        require(question.get("question_type") == "single_choice", f"{where} question_type must be single_choice", errors)
        require(question.get("source") == "standards_training", f"{where} source must be standards_training", errors)
        source_ref = question.get("source_ref")
        require(isinstance(source_ref, str) and source_ref.startswith("references/") and source_ref.endswith(".md"), f"{where} source_ref must point to references markdown", errors)
        tags = question.get("tags")
        require(isinstance(tags, list) and 1 <= len(tags) <= 5, f"{where} tags must contain 1-5 items", errors)

    stats = data.get("stats", {})
    if isinstance(stats, dict):
        require(stats.get("structured_documents") == len(documents), f"{rel} stats.structured_documents should be {len(documents)}", errors)
        require(stats.get("clauses") == len(clauses), f"{rel} stats.clauses should be {len(clauses)}", errors)
        require(stats.get("questions") == len(questions), f"{rel} stats.questions should be {len(questions)}", errors)
        if isinstance(skipped, list):
            require(stats.get("skipped_documents") == len(skipped), f"{rel} stats.skipped_documents should be {len(skipped)}", errors)

    return len(documents), len(clauses), len(questions)


def validate_config(errors: list[str], by_chapter_counts: dict[str, int]) -> None:
    path = QUESTIONS_DIR / "config.json"
    data = load_json(path)
    rel = path.relative_to(ROOT)
    require(isinstance(data, dict), f"{rel} root must be an object", errors)
    if not isinstance(data, dict):
        return

    require(data.get("chapter_count") == EXPECTED_CHAPTERS, f"{rel} chapter_count should be {EXPECTED_CHAPTERS}", errors)
    min_questions = min(by_chapter_counts.values()) if by_chapter_counts else MIN_QUESTIONS_PER_CHAPTER
    require(
        isinstance(data.get("questions_per_chapter"), int) and data.get("questions_per_chapter") >= MIN_QUESTIONS_PER_CHAPTER,
        f"{rel} questions_per_chapter should be at least {MIN_QUESTIONS_PER_CHAPTER}",
        errors,
    )
    require(
        data.get("questions_per_chapter") == min_questions,
        f"{rel} questions_per_chapter should match the minimum chapter count {min_questions}",
        errors,
    )
    intervals = data.get("review_intervals_days")
    require(isinstance(intervals, list) and intervals == sorted(intervals), f"{rel} review_intervals_days should be sorted", errors)
    paths = data.get("paths")
    require(isinstance(paths, dict), f"{rel} paths must be an object", errors)
    if isinstance(paths, dict):
        for key in ("chapters_dir", "archive_file", "progress_file", "sessions_dir", "case_studies_file"):
            require(key in paths, f"{rel} paths missing {key}", errors)


def validate_automation_files(errors: list[str]) -> None:
    required = [
        ROOT / "scripts" / "study.py",
        ROOT / "scripts" / "study_utils.py",
        ROOT / "scripts" / "practice.py",
        ROOT / "scripts" / "mock_exam.py",
        ROOT / "scripts" / "grade_answers.py",
        ROOT / "scripts" / "due_review.py",
        ROOT / "scripts" / "analyze_weakness.py",
        ROOT / "scripts" / "enrich_question_metadata.py",
        ROOT / "agents" / "openai.yaml",
        QUESTIONS_DIR / "sessions",
    ]
    for path in required:
        require(path.exists(), f"missing automation asset: {path.relative_to(ROOT)}", errors)


def main() -> int:
    errors: list[str] = []

    try:
        total_questions, _, by_chapter_counts = validate_chapter_questions(errors)
        total_cases, total_sub_questions = validate_case_studies(errors)
        validate_index(total_questions, total_cases, total_sub_questions, by_chapter_counts, errors)
        validate_config(errors, by_chapter_counts)
        validate_automation_files(errors)
        validate_other_json(errors)
        past_choices, past_cases, past_papers = validate_past_exams(errors)
        standard_docs, standard_clauses, standard_questions = validate_standards_training(errors)
    except ValueError as exc:
        errors.append(str(exc))

    if errors:
        print("Question asset validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "Question asset validation passed: "
        f"{total_questions} chapter questions, {total_cases} case studies, "
        f"{total_sub_questions} case sub-questions, "
        f"{past_choices} past-exam choices, {past_cases} past-exam cases, "
        f"{past_papers} past-exam paper topics, "
        f"{standard_docs} standards docs, {standard_clauses} standards clauses, "
        f"{standard_questions} standards questions."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
