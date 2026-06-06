from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from typing import Any

from study_modules.common import display_command, load_internal_json
from study_modules.materials import case_range_chapters_text
from study_modules.settings import DEFAULT_PAPER_TOPIC, PROFILE_FILE
from study_utils import ROOT, chapter_no_from_label, load_archive, load_progress, parse_date, save_json, today

def default_learner_profile() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "updated_at": None,
        "exam": {
            "name": "系统规划与管理师",
            "target_batch": "待确认",
            "target_date": None,
            "strategy": "保过优先",
        },
        "availability": {
            "daily_minutes": 60,
            "weekday_minutes": 60,
            "weekend_minutes": 90,
            "preferred_slots": [],
        },
        "baseline": {
            "stage": "待确认",
            "weak_subjects": [],
            "weak_chapters": [],
            "confidence": "待确认",
        },
        "preferences": {
            "interaction_style": "一问一答",
            "task_intensity": "normal",
            "preferred_modes": [],
        },
        "targets": {
            "comprehensive_score": 45,
            "case_score": 45,
            "paper_score": 45,
            "overall_goal": "三科过线",
        },
        "notes": {
            "missing_fields": [],
            "privacy": "不保存敏感信息",
        },
    }


def deep_merge_profile(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_profile(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_learner_profile() -> dict[str, Any]:
    profile = default_learner_profile()
    loaded = load_internal_json(PROFILE_FILE, {})
    if isinstance(loaded, dict):
        profile = deep_merge_profile(profile, loaded)
    profile["_path"] = str(PROFILE_FILE.relative_to(ROOT))
    profile["_exists"] = PROFILE_FILE.exists()
    return profile


def profile_daily_minutes(profile: dict[str, Any]) -> int:
    availability = profile.get("availability") or {}
    value = availability.get("daily_minutes")
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        minutes = 60
    return max(15, min(minutes, 360))


def profile_task_intensity(profile: dict[str, Any]) -> str:
    value = str((profile.get("preferences") or {}).get("task_intensity") or "normal").lower()
    return value if value in {"light", "normal", "intense"} else "normal"


def profile_study_load(profile: dict[str, Any]) -> str:
    minutes = profile_daily_minutes(profile)
    if minutes < 45:
        return "轻量"
    if minutes < 90:
        return "标准"
    return "加量"


def profile_practice_count(profile: dict[str, Any], default: int = 5) -> int:
    minutes = profile_daily_minutes(profile)
    intensity = profile_task_intensity(profile)
    if minutes < 45:
        count = 3
    elif minutes < 75:
        count = 5
    elif minutes < 120:
        count = 8
    else:
        count = 10
    if intensity == "light":
        count = max(3, count - 2)
    elif intensity == "intense":
        count = min(15, count + 3)
    return max(1, count or default)


def profile_case_count(profile: dict[str, Any]) -> int:
    return 2 if profile_daily_minutes(profile) >= 120 else 1


def profile_has_weak_subject(profile: dict[str, Any], *keywords: str) -> bool:
    subjects = [str(item) for item in (profile.get("baseline") or {}).get("weak_subjects", [])]
    text = " ".join(subjects)
    return any(keyword in text for keyword in keywords)


def profile_weak_chapters(profile: dict[str, Any]) -> list[int]:
    values = (profile.get("baseline") or {}).get("weak_chapters", [])
    chapters: list[int] = []
    iterable = values if isinstance(values, list) else []
    for value in iterable:
        try:
            chapter = int(value)
        except (TypeError, ValueError):
            continue
        if 1 <= chapter <= 24 and chapter not in chapters:
            chapters.append(chapter)
    return chapters


def profile_days_until_exam(profile: dict[str, Any]) -> int | None:
    target_date = (profile.get("exam") or {}).get("target_date")
    parsed = parse_date(str(target_date)) if target_date else None
    if not parsed:
        return None
    return (parsed - today()).days


def profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    exam = profile.get("exam") or {}
    availability = profile.get("availability") or {}
    baseline = profile.get("baseline") or {}
    preferences = profile.get("preferences") or {}
    targets = profile.get("targets") or {}
    notes = profile.get("notes") or {}
    return {
        "path": profile.get("_path"),
        "exists": profile.get("_exists"),
        "updated_at": profile.get("updated_at"),
        "exam_name": exam.get("name"),
        "target_batch": exam.get("target_batch"),
        "target_date": exam.get("target_date"),
        "strategy": exam.get("strategy"),
        "daily_minutes": profile_daily_minutes(profile),
        "study_load": profile_study_load(profile),
        "days_until_exam": profile_days_until_exam(profile),
        "weekday_minutes": availability.get("weekday_minutes"),
        "weekend_minutes": availability.get("weekend_minutes"),
        "preferred_slots": availability.get("preferred_slots", []),
        "stage": baseline.get("stage"),
        "weak_subjects": baseline.get("weak_subjects", []),
        "weak_chapters": profile_weak_chapters(profile),
        "confidence": baseline.get("confidence"),
        "task_intensity": profile_task_intensity(profile),
        "preferred_modes": preferences.get("preferred_modes", []),
        "target_scores": {
            "综合知识": targets.get("comprehensive_score"),
            "案例分析": targets.get("case_score"),
            "论文": targets.get("paper_score"),
        },
        "overall_goal": targets.get("overall_goal"),
        "missing_fields": notes.get("missing_fields", []),
    }



def _chapter_command_for_point(point: str, chapters: Counter[int] | dict[int, int] | None, count: int = 5) -> str:
    chapter_part = ""
    if chapters:
        chapter_no = max(chapters.items(), key=lambda item: item[1])[0]
        chapter_part = f" --chapters {chapter_no}"
    return f"python scripts/study.py start{chapter_part} --knowledge-point {point} --count {count} --format markdown"

def profile_dynamic_insights(
    profile: dict[str, Any] | None = None,
    progress: dict[str, Any] | None = None,
    archive: dict[str, Any] | None = None,
    recent_limit: int = 100,
) -> dict[str, Any]:
    progress = progress if progress is not None else load_progress()
    archive = archive if archive is not None else load_archive()
    answers = list(progress.get("answers", []))
    recent_answers = answers[-recent_limit:]
    stats = progress.get("stats", {})
    total_answered = int(stats.get("total_answered") or len(answers))
    total_correct = int(stats.get("total_correct") or sum(1 for item in answers if item.get("is_correct")))
    recent_correct = sum(1 for item in recent_answers if item.get("is_correct"))
    recent_accuracy = round(recent_correct / len(recent_answers) * 100, 2) if recent_answers else None
    total_accuracy = round(total_correct / total_answered * 100, 2) if total_answered else None

    chapter_rows: dict[int, dict[str, Any]] = {}
    point_rows: dict[str, dict[str, Any]] = {}
    for item in recent_answers:
        chapter_no = chapter_no_from_label(str(item.get("chapter") or ""))
        if chapter_no is not None:
            row = chapter_rows.setdefault(chapter_no, {"chapter_no": chapter_no, "chapter": f"第{chapter_no}章", "answered": 0, "correct": 0, "wrong": 0, "archive_wrong_attempts": 0})
            row["answered"] += 1
            row["correct"] += 1 if item.get("is_correct") else 0
            row["wrong"] += 0 if item.get("is_correct") else 1
        point = str(item.get("knowledge_point") or item.get("section") or "").strip()
        if point:
            point_row = point_rows.setdefault(point, {"knowledge_point": point, "answered": 0, "correct": 0, "wrong": 0, "chapters": Counter()})
            point_row["answered"] += 1
            point_row["correct"] += 1 if item.get("is_correct") else 0
            point_row["wrong"] += 0 if item.get("is_correct") else 1
            if chapter_no is not None:
                point_row["chapters"][chapter_no] += 1

    for chapter, item in (archive.get("stats", {}).get("by_chapter", {}) or {}).items():
        chapter_no = chapter_no_from_label(str(chapter))
        if chapter_no is None:
            continue
        row = chapter_rows.setdefault(chapter_no, {"chapter_no": chapter_no, "chapter": f"第{chapter_no}章", "answered": 0, "correct": 0, "wrong": 0, "archive_wrong_attempts": 0})
        row["archive_wrong_attempts"] = int(item.get("wrong_attempts") or item.get("wrong") or 0)

    weak_chapters = []
    for row in chapter_rows.values():
        answered = int(row["answered"])
        wrong = int(row["wrong"])
        archive_wrong_attempts = int(row.get("archive_wrong_attempts") or 0)
        accuracy = round(row["correct"] / answered * 100, 2) if answered else None
        priority = wrong * 2 + archive_wrong_attempts + ((100 - accuracy) / 25 if accuracy is not None else 0)
        if wrong or archive_wrong_attempts or (accuracy is not None and answered >= 3 and accuracy < 70):
            weak_chapters.append({**row, "accuracy_percent": accuracy, "priority": round(priority, 2), "command": f"python scripts/study.py start --chapters {row['chapter_no']} --count {profile_practice_count(profile or default_learner_profile())} --format markdown"})
    weak_chapters.sort(key=lambda item: (-float(item["priority"]), int(item["chapter_no"])))

    weak_points = []
    for row in point_rows.values():
        answered = int(row["answered"])
        wrong = int(row["wrong"])
        accuracy = round(row["correct"] / answered * 100, 2) if answered else None
        if wrong or (accuracy is not None and answered >= 2 and accuracy < 70):
            weak_points.append(
                {
                    "knowledge_point": row["knowledge_point"],
                    "answered": answered,
                    "wrong": wrong,
                    "accuracy_percent": accuracy,
                    "chapters": dict(row["chapters"]),
                    "command": _chapter_command_for_point(str(row["knowledge_point"]), row["chapters"]),
                }
            )
    weak_points.sort(key=lambda item: (-int(item["wrong"]), item["accuracy_percent"] if item["accuracy_percent"] is not None else 101, str(item["knowledge_point"])))

    dynamic_subjects = []
    if total_answered >= 5 and total_accuracy is not None and total_accuracy < 70:
        dynamic_subjects.append({"subject": "综合知识", "reason": f"累计选择题正确率 {total_accuracy}%，低于 70% 校准线。"})
    case_attempts = list(progress.get("case_attempts", []))
    if case_attempts:
        last_case = case_attempts[-1]
        case_score = float(last_case.get("score_percent") or 0)
        if case_score < 60:
            dynamic_subjects.append({"subject": "案例分析", "reason": f"最近案例估分 {case_score}%，优先补采分点。"})
    paper_attempts = list(progress.get("paper_attempts", []))
    if paper_attempts:
        last_paper = paper_attempts[-1]
        paper_score = int(last_paper.get("score") or 0)
        if paper_score < 60:
            dynamic_subjects.append({"subject": "论文", "reason": f"最近论文训练评分 {paper_score}/100，优先补结构和素材。"})

    calibration_gaps = []
    if total_answered < 20:
        calibration_gaps.append(f"综合知识至少答满 20 题后，动态薄弱章节会更稳定；当前 {total_answered} 题。")
    if not case_attempts:
        calibration_gaps.append("案例分析尚未提交评分，暂按静态画像安排。")
    if not paper_attempts:
        calibration_gaps.append("论文尚未提交评分，暂按静态画像安排。")

    actions = []
    for item in weak_points[:2]:
        actions.append({"type": "weak_point", "title": f"补练错题知识点：{item['knowledge_point']}", "command": item["command"]})
    for item in weak_chapters[:2]:
        actions.append({"type": "weak_chapter", "title": f"巩固动态薄弱章节：{item['chapter']}", "command": item["command"]})
    if any(item["subject"] == "案例分析" for item in dynamic_subjects):
        actions.append({"type": "case", "title": "案例采分点补强", "command": f"python scripts/study.py case start --chapters {case_range_chapters_text()} --count {profile_case_count(profile or default_learner_profile())} --format markdown"})
    if any(item["subject"] == "论文" for item in dynamic_subjects):
        actions.append({"type": "paper", "title": "论文结构补强", "command": f"python scripts/study.py paper --topic {DEFAULT_PAPER_TOPIC} --format markdown"})

    return {
        "source": "assets/questions/progress.json + assets/questions/archive.json",
        "choice_answered": total_answered,
        "choice_accuracy_percent": total_accuracy,
        "recent_answered": len(recent_answers),
        "recent_accuracy_percent": recent_accuracy,
        "weak_chapters": weak_chapters[:5],
        "weak_knowledge_points": weak_points[:5],
        "dynamic_weak_subjects": dynamic_subjects,
        "calibration_gaps": calibration_gaps,
        "actions": actions[:5],
    }


def profile_dynamic_weak_subject_names(insights: dict[str, Any]) -> set[str]:
    return {str(item.get("subject")) for item in insights.get("dynamic_weak_subjects", []) if item.get("subject")}


PROFILE_SENSITIVE_KEYWORDS = (
    "身份证",
    "准考证",
    "手机号",
    "手机号码",
    "电话",
    "微信",
    "QQ",
    "邮箱",
    "地址",
    "银行卡",
    "密码",
    "验证码",
    "cookie",
    "token",
    "api key",
    "apikey",
    "secret",
)


CHINESE_NUMBER_VALUES = {
    "半": 0.5,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


def contains_profile_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    found = [keyword for keyword in PROFILE_SENSITIVE_KEYWORDS if keyword.lower() in lowered]
    patterns = [
        ("疑似手机号", r"(?<!\d)1[3-9]\d{9}(?!\d)"),
        ("疑似身份证号", r"(?<!\d)\d{17}[\dXx](?!\d)"),
        ("疑似邮箱", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        ("疑似密钥", r"\b(?:sk|pk|ak|token|secret)[-_A-Za-z0-9]{12,}\b"),
    ]
    for label, pattern in patterns:
        if re.search(pattern, text) and label not in found:
            found.append(label)
    return found


def profile_write_requested(text: str) -> bool:
    return any(word in text for word in ("保存", "写入", "更新", "设置", "修改", "改成", "记录到画像", "加入画像", "记到画像", "接入画像"))


def parse_duration_value(value: str, half_suffix: str | None, unit: str) -> int | None:
    raw = value.strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", raw):
        number = float(raw)
    else:
        number = CHINESE_NUMBER_VALUES.get(raw)
    if number is None:
        return None
    if half_suffix:
        number += 0.5
    if unit in ("分钟", "分"):
        minutes = number
    else:
        minutes = number * 60
    return max(15, min(int(round(minutes)), 360))


def extract_profile_minutes(text: str) -> dict[str, int]:
    fields: dict[str, int] = {}
    pattern = re.compile(r"(?P<num>\d+(?:\.\d+)?|半|一|二|两|三|四|五|六|七|八|九|十)(?:个)?(?P<half>半)?\s*(?P<unit>小时|钟头|分钟|分)")
    matches = list(pattern.finditer(text))
    for match in matches:
        minutes = parse_duration_value(match.group("num"), match.group("half"), match.group("unit"))
        if minutes is None:
            continue
        prefix = text[max(0, match.start() - 18) : match.start()]
        suffix = text[match.end() : match.end() + 8]
        context = prefix + suffix
        if any(word in context for word in ("工作日", "周一", "周五", "平时")):
            fields["availability.weekday_minutes"] = minutes
        elif any(word in context for word in ("周末", "周六", "周日")):
            fields["availability.weekend_minutes"] = minutes
        elif any(word in context for word in ("每天", "每日", "一天", "日均", "平均", "能学", "学习")) or len(matches) == 1:
            fields["availability.daily_minutes"] = minutes
    return fields


def extract_profile_slots(text: str) -> list[str]:
    slots = []
    for slot in ("清晨", "早上", "上午", "中午", "下午", "晚上", "夜里", "周末"):
        if slot in text and slot not in slots:
            slots.append(slot)
    return slots


def extract_profile_weak_subjects(text: str) -> list[str]:
    weak_terms = ("弱", "薄弱", "担心", "最怕", "最难", "不会", "短板", "差")
    if not any(term in text for term in weak_terms):
        return []
    mapping = [
        (("论文", "作文"), "论文"),
        (("案例", "主观题"), "案例分析"),
        (("上午", "综合", "选择题", "选择"), "综合知识"),
    ]
    subjects = []
    for aliases, subject in mapping:
        if any(alias in text for alias in aliases) and subject not in subjects:
            subjects.append(subject)
    return subjects


def extract_profile_stage(text: str) -> str | None:
    if "零基础" in text or "刚开始" in text:
        return "零基础/刚开始"
    if "学过一轮" in text or "过了一轮" in text or "一轮" in text:
        return "学过一轮"
    if "冲刺阶段" in text or "临考" in text:
        return "冲刺阶段"
    if "系统化训练" in text:
        return "系统化训练阶段"
    return None


def extract_profile_strategy(text: str) -> str | None:
    if "保过" in text or "先过" in text or "及格" in text:
        return "保过优先"
    if "高分" in text or "冲高" in text:
        return "冲高分"
    if "冲刺" in text:
        return "冲刺提分"
    return None


def extract_profile_intensity(text: str) -> str | None:
    if any(word in text for word in ("轻量", "少一点", "别太多", "低强度")):
        return "light"
    if any(word in text for word in ("加量", "高强度", "多安排", "强度高", "狠狠练")):
        return "intense"
    if any(word in text for word in ("正常", "适中", "标准强度")):
        return "normal"
    return None


def extract_profile_target_date(text: str) -> str | None:
    match = re.search(r"(20\d{2})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if not match:
        return None
    year, month, day = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
    try:
        return f"{year:04d}-{month:02d}-{day:02d}"
    except ValueError:
        return None


def extract_profile_target_batch(text: str) -> str | None:
    match = re.search(r"(20\d{2})年\s*(上半年|下半年)", text)
    if match:
        return f"{match.group(1)}年{match.group(2)}"
    return None


def extract_profile_target_scores(text: str) -> dict[str, int]:
    score_fields: dict[str, int] = {}
    patterns = [
        (r"综合知识?\D{0,6}(\d{2})\s*分?", "targets.comprehensive_score"),
        (r"上午\D{0,6}(\d{2})\s*分?", "targets.comprehensive_score"),
        (r"案例\D{0,6}(\d{2})\s*分?", "targets.case_score"),
        (r"论文\D{0,6}(\d{2})\s*分?", "targets.paper_score"),
    ]
    for pattern, field in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        score = int(match.group(1))
        if 0 <= score <= 75:
            score_fields[field] = score
    return score_fields


def extract_profile_weak_chapters_from_text(text: str) -> list[int]:
    chapters = []
    if not any(word in text for word in ("弱", "薄弱", "担心", "最怕", "不会", "短板")):
        return chapters
    for match in re.finditer(r"第\s*(\d{1,2})\s*章", text):
        chapter = int(match.group(1))
        if 1 <= chapter <= 24 and chapter not in chapters:
            chapters.append(chapter)
    return chapters


def get_profile_path_value(profile: dict[str, Any], path: str) -> Any:
    current: Any = profile
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def set_profile_path_value(profile: dict[str, Any], path: str, value: Any) -> None:
    current = profile
    parts = path.split(".")
    for part in parts[:-1]:
        current = current.setdefault(part, {})
    current[parts[-1]] = value


def add_profile_update(updates: list[dict[str, Any]], profile: dict[str, Any], path: str, value: Any, reason: str) -> None:
    old_value = get_profile_path_value(profile, path)
    if old_value == value:
        return
    updates.append({"field": path, "old": old_value, "new": value, "reason": reason})


def infer_profile_updates_from_text(text: str, profile: dict[str, Any]) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    for field, minutes in extract_profile_minutes(text).items():
        add_profile_update(updates, profile, field, minutes, "学习时长")
    slots = extract_profile_slots(text)
    if slots:
        old_slots = get_profile_path_value(profile, "availability.preferred_slots") or []
        merged_slots = list(old_slots) if isinstance(old_slots, list) else []
        for slot in slots:
            if slot not in merged_slots:
                merged_slots.append(slot)
        add_profile_update(updates, profile, "availability.preferred_slots", merged_slots, "偏好学习时段")
    weak_subjects = extract_profile_weak_subjects(text)
    if weak_subjects:
        old_subjects = get_profile_path_value(profile, "baseline.weak_subjects") or []
        merged_subjects = list(old_subjects) if isinstance(old_subjects, list) else []
        for subject in weak_subjects:
            if subject not in merged_subjects:
                merged_subjects.append(subject)
        add_profile_update(updates, profile, "baseline.weak_subjects", merged_subjects, "薄弱科目")
    weak_chapters = extract_profile_weak_chapters_from_text(text)
    if weak_chapters:
        old_chapters = profile_weak_chapters(profile)
        merged_chapters = list(old_chapters)
        for chapter in weak_chapters:
            if chapter not in merged_chapters:
                merged_chapters.append(chapter)
        add_profile_update(updates, profile, "baseline.weak_chapters", merged_chapters, "薄弱章节")
    stage = extract_profile_stage(text)
    if stage:
        add_profile_update(updates, profile, "baseline.stage", stage, "学习阶段")
    strategy = extract_profile_strategy(text)
    if strategy:
        add_profile_update(updates, profile, "exam.strategy", strategy, "备考策略")
        add_profile_update(updates, profile, "targets.overall_goal", "三科稳定过线" if strategy == "保过优先" else strategy, "总目标")
    intensity = extract_profile_intensity(text)
    if intensity:
        add_profile_update(updates, profile, "preferences.task_intensity", intensity, "任务强度")
    target_date = extract_profile_target_date(text)
    if target_date:
        add_profile_update(updates, profile, "exam.target_date", target_date, "考试日期")
    target_batch = extract_profile_target_batch(text)
    if target_batch:
        add_profile_update(updates, profile, "exam.target_batch", target_batch, "考试批次")
    for field, score in extract_profile_target_scores(text).items():
        add_profile_update(updates, profile, field, score, "目标分数")
    return updates


def is_profile_update_request(text: str) -> bool:
    if any(word in text for word in ("按薄弱点", "针对薄弱", "薄弱点练习", "薄弱点出题", "定向练习")):
        return False
    if any(word in text for word in ("个人画像", "备考画像", "学习画像")) and profile_write_requested(text):
        return True
    patterns = (
        "每天能学",
        "每日能学",
        "每天学习",
        "每日学习",
        "工作日",
        "周末",
        "最弱",
        "最担心",
        "薄弱",
        "优先保过",
        "保过",
        "零基础",
        "学过一轮",
        "冲刺阶段",
        "目标分",
        "目标批次",
        "考试日期",
        "学习强度",
    )
    return any(pattern in text for pattern in patterns)


def profile_clean_for_save(profile: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in profile.items() if not str(key).startswith("_")}


def apply_profile_updates(profile: dict[str, Any], updates: list[dict[str, Any]]) -> dict[str, Any]:
    proposed = json.loads(json.dumps(profile_clean_for_save(profile), ensure_ascii=False))
    for update in updates:
        set_profile_path_value(proposed, update["field"], update["new"])
    proposed["updated_at"] = today().isoformat()
    missing = ((proposed.get("notes") or {}).get("missing_fields") or [])
    if isinstance(missing, list):
        remove_by_field = {
            "availability.daily_minutes": "真实每日可学习时间",
            "exam.target_date": "准确考试日期",
            "baseline.weak_subjects": "最担心科目排序",
        }
        clear_labels = {remove_by_field[update["field"]] for update in updates if update["field"] in remove_by_field}
        if clear_labels:
            proposed.setdefault("notes", {})["missing_fields"] = [item for item in missing if item not in clear_labels]
    return proposed


def build_profile_update_payload(args: argparse.Namespace) -> dict[str, Any]:
    text = str(getattr(args, "text", "") or "")
    write = bool(getattr(args, "write", False))
    profile = load_learner_profile()
    updates = infer_profile_updates_from_text(text, profile)
    sensitive_terms = contains_profile_sensitive_text(text)
    proposed = apply_profile_updates(profile, updates) if updates else profile_clean_for_save(profile)
    blocked = bool(sensitive_terms and write)
    wrote = False
    if write and updates and not blocked:
        save_json(PROFILE_FILE, proposed)
        wrote = True
    return {
        "text": text,
        "profile_file": str(PROFILE_FILE.relative_to(ROOT)),
        "write_requested": write,
        "wrote": wrote,
        "blocked": blocked,
        "sensitive_terms": sensitive_terms,
        "updates": updates,
        "proposed_summary": profile_summary(deep_merge_profile(default_learner_profile(), proposed)),
        "next_step": "如果确认写入，请直接说：保存到画像：<你的偏好描述>",
    }


def render_profile_update_markdown(payload: dict[str, Any]) -> str:
    mode = "已写入" if payload.get("wrote") else "已拦截" if payload.get("blocked") else "预览"
    lines = [
        "# 画像自然语言更新",
        "",
        f"- 模式：{mode}",
        f"- 画像文件：{payload['profile_file']}",
    ]
    if payload.get("sensitive_terms"):
        lines.append(f"- 敏感信息拦截：{', '.join(payload['sensitive_terms'])}")
    if not payload.get("updates"):
        lines.append("- 识别字段：暂无。请描述每日可学时间、薄弱科目、考试批次、目标分数或学习强度。")
    else:
        lines.append("")
        lines.append("## 识别字段")
        for update in payload["updates"]:
            lines.append(f"- {update['field']}: {update.get('old')} -> {update.get('new')}（{update['reason']}）")
    if payload.get("blocked"):
        lines.append("")
        lines.append("写入被拦截：请去掉身份证、账号、密码、联系方式等敏感信息后再保存。")
    elif payload.get("wrote"):
        summary = payload.get("proposed_summary") or {}
        lines.append("")
        lines.append("## 写入后摘要")
        lines.append(f"- 每日可学：{summary.get('daily_minutes')} 分钟")
        lines.append(f"- 薄弱科目：{', '.join(summary.get('weak_subjects') or []) or '待确认'}")
        lines.append(f"- 策略：{summary.get('strategy') or '待确认'}")
    elif payload.get("updates"):
        lines.append("")
        lines.append(f"Next: {display_command(payload['next_step'])}")
    return "\n".join(lines) + "\n"

def build_profile_payload(args: argparse.Namespace | None = None) -> dict[str, Any]:
    profile = load_learner_profile()
    summary = profile_summary(profile)
    insights = profile_dynamic_insights(profile)
    return {
        "profile": profile,
        "summary": summary,
        "dynamic_insights": insights,
        "suggested_practice_count": profile_practice_count(profile),
        "suggested_case_count": profile_case_count(profile),
        "suggested_daily_minutes": summary["daily_minutes"],
    }


def render_profile_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    scores = summary.get("target_scores") or {}
    missing_fields = summary.get("missing_fields") or []
    weak_chapters = summary.get("weak_chapters") or []
    lines = [
        "# 个人备考画像",
        "",
        f"- 画像文件：{summary.get('path')}",
        f"- 最近更新：{summary.get('updated_at') or '待确认'}",
        f"- 考试目标：{summary.get('exam_name')}，{summary.get('target_batch') or '批次待确认'}",
        f"- 考试日期：{summary.get('target_date') or '待确认'}",
    ]
    if summary.get("days_until_exam") is not None:
        lines.append(f"- 距离考试：{summary['days_until_exam']} 天")
    lines.extend(
        [
            f"- 策略：{summary.get('strategy') or '待确认'}",
            f"- 每日可学：{summary.get('daily_minutes')} 分钟（{summary.get('study_load')}负荷）",
            f"- 学习时段：{', '.join(summary.get('preferred_slots') or []) or '待确认'}",
            f"- 当前阶段：{summary.get('stage') or '待确认'}",
            f"- 薄弱科目：{', '.join(summary.get('weak_subjects') or []) or '待确认'}",
            f"- 薄弱章节：{', '.join(str(chapter) for chapter in weak_chapters) or '待确认'}",
            f"- 目标分数：综合知识 {scores.get('综合知识') or '-'}，案例分析 {scores.get('案例分析') or '-'}，论文 {scores.get('论文') or '-'}",
            f"- 总目标：{summary.get('overall_goal') or '待确认'}",
            "",
            "## 个性化默认值",
            f"- 选择题每日建议题量：{payload['suggested_practice_count']} 题",
            f"- 案例每日建议数量：{payload['suggested_case_count']} 个",
            f"- 任务强度：{summary.get('task_intensity')}",
            f"- 偏好模式：{', '.join(summary.get('preferred_modes') or []) or '待确认'}",
        ]
    )
    if missing_fields:
        lines.append("")
        lines.append("## 待补充")
        lines.extend(f"- {item}" for item in missing_fields)
    insights = payload.get("dynamic_insights") or {}
    lines.append("")
    lines.append("## 动态校准")
    lines.append(f"- 来源：{insights.get('source')}")
    lines.append(f"- 综合知识：已答 {insights.get('choice_answered', 0)} 题，累计正确率 {insights.get('choice_accuracy_percent') if insights.get('choice_accuracy_percent') is not None else '-'}%，最近正确率 {insights.get('recent_accuracy_percent') if insights.get('recent_accuracy_percent') is not None else '-'}%")
    if insights.get("dynamic_weak_subjects"):
        lines.append("- 动态薄弱科目：")
        for item in insights["dynamic_weak_subjects"]:
            lines.append(f"  - {item['subject']}：{item['reason']}")
    if insights.get("weak_chapters"):
        lines.append("- 动态薄弱章节：")
        for item in insights["weak_chapters"][:3]:
            accuracy = item.get("accuracy_percent") if item.get("accuracy_percent") is not None else "-"
            lines.append(f"  - {item['chapter']}：错 {item['wrong']} 次，正确率 {accuracy}%，建议 {display_command(item['command'])}")
    if insights.get("weak_knowledge_points"):
        lines.append("- 动态薄弱知识点：")
        for item in insights["weak_knowledge_points"][:3]:
            accuracy = item.get("accuracy_percent") if item.get("accuracy_percent") is not None else "-"
            lines.append(f"  - {item['knowledge_point']}：错 {item['wrong']} 次，正确率 {accuracy}%，建议 {display_command(item['command'])}")
    if insights.get("calibration_gaps"):
        lines.append("- 待校准：")
        for item in insights["calibration_gaps"]:
            lines.append(f"  - {item}")
    lines.append("")
    lines.append("Next: 直接说“保存到画像：我每天能学1小时，论文最弱，优先保过”，即可用自然语言更新画像。")
    return "\n".join(lines) + "\n"


def command_profile(args: argparse.Namespace) -> int:
    payload = build_profile_payload(args)
    if args.format == "markdown":
        print(render_profile_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_profile_update(args: argparse.Namespace) -> int:
    payload = build_profile_update_payload(args)
    if args.format == "markdown":
        print(render_profile_update_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0
