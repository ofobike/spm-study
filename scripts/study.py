#!/usr/bin/env python3
"""One-command learning loop for the spm-study skill."""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stdout
import io
import json
import re
import uuid
from pathlib import Path
from typing import Any

from study_utils import (
    CHAPTERS_DIR,
    ROOT,
    SESSIONS_DIR,
    append_progress,
    chapter_no_from_label,
    choose_questions,
    load_all_questions,
    load_archive,
    load_config,
    load_json,
    load_progress,
    make_session,
    mark_reviewed,
    now_iso,
    parse_answer_text,
    parse_chapters,
    parse_date,
    public_question,
    record_wrong_answer,
    render_questions_markdown,
    save_json,
    today,
    write_session,
)


INTERNAL_DIR = ROOT / "references" / "internal"
EXAM_GUIDE_FILE = INTERNAL_DIR / "guide" / "exam-guide.json"
SYLLABUS_ANALYSIS_FILE = INTERNAL_DIR / "syllabus" / "syllabus-analysis.json"
PAPER_SPECIAL_DIR = INTERNAL_DIR / "paper-special"
PAPER_SPECIAL_INDEX = PAPER_SPECIAL_DIR / "index.json"
CHAPTER_PRACTICE_STRUCTURED_DIR = INTERNAL_DIR / "chapter-practice" / "structured"
CASE_RECITATION_STRUCTURED_DIR = INTERNAL_DIR / "case-special" / "structured"
VIP_MATERIALS_DIR = INTERNAL_DIR / "vip-materials"
VIP_MATERIALS_MANIFEST = VIP_MATERIALS_DIR / "manifest.json"
SPRINT_MATERIALS_DIR = INTERNAL_DIR / "sprint-materials"
SPRINT_MATERIALS_MANIFEST = SPRINT_MATERIALS_DIR / "manifest.json"
BACKUP_PDFS_DIR = ROOT / "references" / "backup-pdfs"
BACKUP_PDFS_MANIFEST = BACKUP_PDFS_DIR / "manifest.json"
PAST_EXAMS_FILE = ROOT / "assets" / "questions" / "past_exams.json"
STANDARDS_TRAINING_FILE = ROOT / "assets" / "questions" / "standards_training.json"
SPRINT_TRAINING_FILE = ROOT / "assets" / "questions" / "sprint_training.json"
SEARCH_INDEX_FILE = ROOT / "assets" / "search" / "index.json"
PROFILE_FILE = ROOT / "assets" / "profile" / "learner_profile.json"
DEFAULT_FOCUS_CHAPTERS = [12, 15, 11, 13, 14, 16, 17, 5, 6, 8, 9, 10, 4, 7]
DEFAULT_CASE_CHAPTERS = "4-24"
DEFAULT_PAPER_TOPIC = "信息系统服务管理"
SPRINT_KINDS = ("all", "mnemonic", "gold-points", "mock-exam", "csf-risk", "activities", "sprint-guide")
SEARCH_SOURCE_TYPES = (
    "case_special",
    "case_study",
    "chapter_practice",
    "chapter_question",
    "chapter_reference",
    "exam_guide",
    "mindmap",
    "mock_bank",
    "paper_special",
    "past_exam",
    "past_exam_pdf",
    "sprint_material",
    "sprint_training",
    "standards_pdf",
    "standards_training",
    "syllabus",
    "three_color_notes",
    "vip_material",
    "zfx_material",
)


PAPER_TOPICS: dict[str, dict[str, Any]] = {
    "信息系统规划": {
        "chapter": 4,
        "chapter_title": "信息系统规划",
        "scenario": "组织战略落地、信息化蓝图设计、系统规划治理和路线图实施",
        "focus": ["战略目标识别", "现状诊断", "业务与应用蓝图", "数据与技术架构", "实施路线图"],
        "paper_points": ["信息系统规划原则", "战略目标集转移", "关键成功因素", "企业架构", "实施保障体系"],
    },
    "应用系统规划": {
        "chapter": 5,
        "chapter_title": "应用系统规划",
        "scenario": "业务应用整合、应用架构规划、系统集成和应用组合优化",
        "focus": ["业务过程分析", "应用架构设计", "系统集成", "应用组合治理", "实施迁移路径"],
        "paper_points": ["应用系统规划内容", "业务抽象", "过程抽象", "数据抽象", "技术抽象"],
    },
    "云资源规划": {
        "chapter": 6,
        "chapter_title": "云资源规划",
        "scenario": "云平台建设、计算存储资源规划、云迁移和云资源治理",
        "focus": ["云资源需求评估", "计算资源规划", "存储资源规划", "云数据中心", "迁移和运维治理"],
        "paper_points": ["云计算架构", "计算资源规划", "存储资源规划", "云数据中心规划", "云迁移策略"],
    },
    "网络环境规划": {
        "chapter": 7,
        "chapter_title": "网络环境规划",
        "scenario": "组织网络架构升级、广域网/局域网规划、网络安全与可靠性保障",
        "focus": ["网络现状评估", "整体网络架构", "广域网与局域网", "无线与移动通信", "网络安全保障"],
        "paper_points": ["网络整体规划", "广域网规划", "局域网规划", "无线网络规划", "网络安全规划"],
    },
    "数据资源规划": {
        "chapter": 8,
        "chapter_title": "数据资源规划",
        "scenario": "数据资源盘点、数据架构设计、数据治理和数据价值释放",
        "focus": ["数据资源目录", "数据架构", "数据标准", "数据治理", "数据质量和主数据"],
        "paper_points": ["数据资源规划方法", "数据架构规划", "数据标准化", "数据治理", "主数据和元数据管理"],
    },
    "信息安全规划": {
        "chapter": 9,
        "chapter_title": "信息安全规划",
        "scenario": "组织信息安全体系建设、等级保护、风险评估和安全治理",
        "focus": ["安全现状评估", "安全体系架构", "等级保护", "访问控制与审计", "应急和持续改进"],
        "paper_points": ["信息安全规划内容", "安全架构", "等级保护", "风险评估", "安全审计"],
    },
    "云原生系统规划": {
        "chapter": 10,
        "chapter_title": "云原生系统规划",
        "scenario": "云原生平台建设、微服务改造、DevOps和容器化治理",
        "focus": ["云原生架构", "容器与微服务", "DevOps流程", "服务治理", "可观测性和安全"],
        "paper_points": ["云原生技术架构", "容器规划", "微服务规划", "DevOps建设", "云原生建设规划"],
    },
    "信息系统治理": {
        "chapter": 11,
        "chapter_title": "信息系统治理",
        "scenario": "IT治理体系建设、组织决策机制、风险合规和价值交付",
        "focus": ["治理目标", "治理组织", "治理流程", "绩效评价", "风险与合规"],
        "paper_points": ["IT治理框架", "治理机制", "COBIT", "IT审计", "风险管理"],
    },
    "信息系统服务管理": {
        "chapter": 12,
        "chapter_title": "信息系统服务管理",
        "scenario": "IT服务体系建设、服务目录、SLA、事件问题变更和持续改进",
        "focus": ["服务战略规划", "服务目录", "SLA管理", "服务运营", "持续改进"],
        "paper_points": ["服务战略规划", "服务目录管理", "服务级别管理", "事件管理", "问题管理"],
    },
    "人员管理": {
        "chapter": 13,
        "chapter_title": "人员管理",
        "scenario": "信息系统团队建设、岗位能力、培训绩效和组织协同",
        "focus": ["岗位设计", "能力模型", "招聘与培养", "绩效管理", "团队协作"],
        "paper_points": ["工作分析", "岗位设计", "能力模型", "人员培训", "绩效管理"],
    },
    "规范与过程管理": {
        "chapter": 14,
        "chapter_title": "规范与过程管理",
        "scenario": "流程标准化、过程改进、规范体系建设和服务过程治理",
        "focus": ["标准化体系", "流程识别", "流程优化", "过程度量", "持续改进"],
        "paper_points": ["标准化", "流程规划", "流程设计", "流程优化", "过程改进"],
    },
    "技术与研发管理": {
        "chapter": 15,
        "chapter_title": "技术与研发管理",
        "scenario": "技术研发体系建设、研发流程、质量管理和知识产权治理",
        "focus": ["技术路线", "研发组织", "质量管理", "配置与评审", "知识产权"],
        "paper_points": ["技术管理", "研发管理", "质量管理", "技术评审", "知识产权管理"],
    },
    "资源与工具管理": {
        "chapter": 16,
        "chapter_title": "资源与工具管理",
        "scenario": "研发测试运维工具链建设、资源统筹、监控和自动化运维",
        "focus": ["资源规划", "研发工具", "测试工具", "运维工具", "监控和自动化"],
        "paper_points": ["资源管理", "研发工具", "测试管理", "运维工具", "监控管理"],
    },
    "信息系统项目管理": {
        "chapter": 17,
        "chapter_title": "信息系统项目管理",
        "scenario": "信息系统项目启动、计划、执行、监控和收尾全过程管理",
        "focus": ["项目目标", "范围进度成本", "质量资源沟通", "风险采购干系人", "配置和变更"],
        "paper_points": ["项目管理知识体系", "WBS", "进度管理", "风险管理", "变更管理"],
    },
    "智慧城市": {
        "chapter": 18,
        "chapter_title": "智慧城市发展规划",
        "scenario": "城市运行一网统管、公共服务协同和城市治理现代化",
        "focus": ["顶层设计", "数据资源整合", "城市运行治理", "公共服务协同", "安全与标准"],
        "paper_points": ["智慧城市顶层设计", "城市数据资源整合", "城市运行一网统管", "智慧政务与惠民服务", "城市安全与标准体系"],
    },
    "智慧园区": {
        "chapter": 19,
        "chapter_title": "智慧园区发展规划",
        "scenario": "园区数字底座、企业服务、运营管理和产业协同",
        "focus": ["园区数字底座", "招商与企业服务", "运营管理", "产业协同", "绿色低碳"],
        "paper_points": ["智慧园区总体规划", "园区数字底座", "企业服务平台", "园区运营管理", "产业协同与绿色低碳"],
    },
    "数字乡村": {
        "chapter": 20,
        "chapter_title": "数字乡村发展规划",
        "scenario": "乡村治理、产业振兴、公共服务和数据惠农",
        "focus": ["乡村治理", "农业农村数据资源", "产业振兴", "公共服务", "数字基础设施"],
        "paper_points": ["数字乡村总体规划", "农业农村数据资源", "乡村治理数字化", "数字惠农公共服务", "产业振兴与基础设施"],
    },
    "企业数字化转型": {
        "chapter": 21,
        "chapter_title": "企业数字化转型发展规划",
        "scenario": "企业战略重塑、流程再造、数据驱动和能力成熟度提升",
        "focus": ["数字化蓝图", "数据驱动", "业务流程优化", "组织能力建设", "成熟度评估"],
        "paper_points": ["数字化转型蓝图", "数据驱动经营", "业务流程优化", "敏捷组织与数字文化", "成熟度评估与持续改进"],
    },
    "智能制造": {
        "chapter": 22,
        "chapter_title": "智能制造发展规划",
        "scenario": "制造企业生产、质量、设备、供应链和工业数据协同",
        "focus": ["智能制造能力成熟度", "生产过程优化", "工业数据采集", "设备与质量管理", "供应链协同"],
        "paper_points": ["智能制造能力成熟度", "生产过程数字化", "工业数据采集与分析", "设备质量协同管理", "供应链协同优化"],
    },
    "新型消费": {
        "chapter": 23,
        "chapter_title": "新型消费系统规划",
        "scenario": "线上线下融合、消费场景创新、平台运营和用户体验提升",
        "focus": ["消费场景创新", "平台化运营", "用户体验", "数据分析", "服务保障"],
        "paper_points": ["新型消费场景创新", "线上线下融合", "平台化运营", "用户体验提升", "消费数据分析与服务保障"],
    },
}

PAPER_TOPIC_ALIASES = {
    "系统规划": "信息系统规划",
    "应用规划": "应用系统规划",
    "云规划": "云资源规划",
    "网络规划": "网络环境规划",
    "数据规划": "数据资源规划",
    "安全规划": "信息安全规划",
    "服务管理": "信息系统服务管理",
    "IT服务管理": "信息系统服务管理",
    "研发管理": "技术与研发管理",
    "工具管理": "资源与工具管理",
    "项目管理": "信息系统项目管理",
    "数字化转型": "企业数字化转型",
    "企业转型": "企业数字化转型",
    "数字企业": "企业数字化转型",
    "消费系统": "新型消费",
    "智慧制造": "智能制造",
}

SUSPICIOUS_DISTRACTOR_REPLACEMENTS = {
    "军事安全": "信息安全",
    "军事训练": "人员培训",
    "军事基地": "基础设施",
    "军事政策": "政策规范",
    "军事服务": "公共服务",
    "军事生产": "生产管理",
    "军事技术": "信息技术",
    "军事化管理": "集中化管理",
    "军事防御体系": "独立防御体系",
    "军事安全防御": "独立安全防御",
    "军事指挥调度": "独立指挥调度",
    "军事指挥": "独立指挥",
    "军事架构": "独立指挥架构",
    "军事设施": "专用设施",
    "军事侦察": "专用侦察",
    "军事通信": "专用通信",
    "军事演练": "专用演练",
    "军事战略": "专用战略",
    "军事纪律": "专用纪律",
    "军事数据": "专用数据",
    "军事威胁": "外部威胁",
    "军事优先": "成本优先",
    "军事防御": "独立防御",
    "军事化": "集中化",
    "军事": "业务",
    "军队": "组织",
    "作战": "运营",
}

STRONG_KNOWLEDGE_POINT_OVERRIDES = {
    "ch03_q034": "系统规划主要矛盾分析",
    "ch08_q005": "CAP理论",
    "ch08_q010": "数据资源化",
    "ch08_q044": "AP模型",
    "ch08_q049": "数据资源规划对象",
    "ch09_q015": "网闸技术",
    "ch09_q016": "对称加密算法",
    "ch09_q017": "VPN技术",
    "ch09_q020": "非对称加密应用",
    "ch09_q026": "网络层加密",
    "ch09_q035": "密钥管理",
    "ch09_q044": "哈希函数",
    "ch11_q036": "ISO/IEC 38500合规原则",
}

STOP_KNOWLEDGE_POINTS = {
    "不属于",
    "据预测",
    "在生态宜居领域",
    "在产业发展领域",
    "智慧政务服务的中",
}

PAPER_RUBRIC = [
    ("abstract", "摘要与中心论点", 10),
    ("background", "项目背景与本人职责", 15),
    ("planning", "规划方法与总体架构", 20),
    ("implementation", "实施过程与工程治理", 25),
    ("domain", "主题知识点运用", 15),
    ("outcome", "效果量化与持续改进", 15),
]

GENERIC_CASE_TERMS = {
    "包括",
    "需要",
    "进行",
    "建立",
    "制定",
    "分析",
    "方案",
    "措施",
    "管理",
    "体系",
    "方面",
    "内容",
    "计划",
    "风险",
    "项目",
    "服务",
}

WEAK_KNOWLEDGE_POINT_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"^据",
        r"^在",
        r"^不属于$",
        r".*包含$",
        r".*包括$",
        r".*表$",
        r".*不包括$",
        r".*核心$",
        r".*的核心.*",
        r".*的中$",
        r".*信息基础设施$",
    )
]


def resolve_session(session_value: str) -> Path:
    path = Path(session_value)
    if path.is_absolute():
        return path
    if path.exists():
        return ROOT / path
    if session_value.endswith(".json"):
        return ROOT / session_value
    return SESSIONS_DIR / f"{session_value}.json"


def simplify_json(value: Any) -> Any:
    if isinstance(value, Counter):
        return dict(value)
    if isinstance(value, dict):
        return {key: simplify_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [simplify_json(item) for item in value]
    return value


def load_internal_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_exam_guide() -> dict[str, Any]:
    return load_internal_json(EXAM_GUIDE_FILE, {})


def load_syllabus_analysis() -> dict[str, Any]:
    return load_internal_json(SYLLABUS_ANALYSIS_FILE, {})


def load_paper_special_index() -> dict[str, Any]:
    return load_internal_json(PAPER_SPECIAL_INDEX, {"documents": [], "rubric": {}, "framework": {}, "samples": []})


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
        lines.append(f"Next: {payload['next_step']}")
    return "\n".join(lines) + "\n"


def exam_focus_chapters() -> list[int]:
    syllabus = load_syllabus_analysis()
    focus = syllabus.get("strategic_focus", {}).get("highest_priority_chapters")
    if isinstance(focus, list) and focus:
        return [int(item) for item in focus]
    return DEFAULT_FOCUS_CHAPTERS[:7]


def paper_range_chapters() -> list[int]:
    syllabus = load_syllabus_analysis()
    chapters = syllabus.get("strategic_focus", {}).get("paper_range_chapters")
    if isinstance(chapters, list) and chapters:
        return [int(item) for item in chapters]
    return list(range(4, 18))


def case_range_chapters_text() -> str:
    syllabus = load_syllabus_analysis()
    chapters = syllabus.get("strategic_focus", {}).get("case_range_chapters")
    if isinstance(chapters, list) and chapters:
        values = [int(item) for item in chapters]
        if values == list(range(min(values), max(values) + 1)):
            return f"{min(values)}-{max(values)}"
        return ",".join(str(item) for item in values)
    return DEFAULT_CASE_CHAPTERS


def guide_chapter_rows() -> list[dict[str, Any]]:
    guide = load_exam_guide()
    rows = guide.get("chapter_priorities", [])
    return rows if isinstance(rows, list) else []


def chapter_guide_row(chapter_no: int) -> dict[str, Any] | None:
    for row in guide_chapter_rows():
        if int(row.get("chapter", 0) or 0) == chapter_no:
            return row
    return None


def top_exam_priority_chapters(limit: int = 5) -> list[dict[str, Any]]:
    rows = [row for row in guide_chapter_rows() if int(row.get("importance", 0) or 0) >= 3]
    if not rows:
        return [{"chapter": chapter, "title": f"第{chapter}章", "importance": 3, "advice": "新版大纲重点章节。"} for chapter in DEFAULT_FOCUS_CHAPTERS[:limit]]
    return sorted(rows, key=lambda row: (-int(row.get("importance", 0) or 0), int(row.get("chapter", 0) or 0)))[:limit]


def build_exam_guide_payload(args: argparse.Namespace | None = None) -> dict[str, Any]:
    limit = int(getattr(args, "limit", 8) if args is not None else 8)
    guide = load_exam_guide()
    syllabus = load_syllabus_analysis()
    subjects = guide.get("exam_schedule", {}).get("subjects", [])
    return {
        "guide_source": guide.get("source"),
        "syllabus_source": syllabus.get("source"),
        "note": guide.get("note") or syllabus.get("note"),
        "exam_schedule": guide.get("exam_schedule", {}),
        "subject_ranges": syllabus.get("subject_ranges", {}),
        "strategic_focus": syllabus.get("strategic_focus", {}),
        "top_chapters": top_exam_priority_chapters(limit),
        "subjects": subjects,
        "paths": {
            "guide": str(EXAM_GUIDE_FILE.relative_to(ROOT)),
            "syllabus": str(SYLLABUS_ANALYSIS_FILE.relative_to(ROOT)),
        },
    }


def load_candidate_questions(chapter: int | None = None) -> list[dict[str, Any]]:
    if chapter:
        path = CHAPTER_PRACTICE_STRUCTURED_DIR / f"chapter_{int(chapter):02d}.json"
    else:
        path = CHAPTER_PRACTICE_STRUCTURED_DIR / "candidate_questions.json"
    return load_internal_json(path, [])


def build_candidate_practice_payload(args: argparse.Namespace) -> dict[str, Any]:
    questions = load_candidate_questions(args.chapter)
    limit = max(1, int(args.count))
    selected = questions[:limit]
    report = load_internal_json(CHAPTER_PRACTICE_STRUCTURED_DIR / "quality_report.json", {})
    return {
        "source": "2025新版系规千题闯关-解析版",
        "status": "candidate_only",
        "note": "候选题源仅用于预览和人工筛选，不写入正式题库、不记录学习进度。",
        "chapter": args.chapter,
        "total_available": len(questions),
        "quality_report": {
            "total": report.get("total"),
            "answer_distribution": report.get("answer_distribution"),
            "issue_counts": report.get("issue_counts"),
        },
        "questions": selected,
        "index_file": str((CHAPTER_PRACTICE_STRUCTURED_DIR / "index.md").relative_to(ROOT)),
    }


def load_vip_manifest() -> dict[str, Any]:
    return load_internal_json(VIP_MATERIALS_MANIFEST, {"files": []})


def load_sprint_materials_manifest() -> dict[str, Any]:
    return load_internal_json(SPRINT_MATERIALS_MANIFEST, {"files": []})


def build_vip_material_payload(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_vip_manifest()
    files = list(manifest.get("files", []))
    kind = getattr(args, "kind", "all") or "all"
    if kind != "all":
        files = [item for item in files if item.get("kind") == kind]
    keyword = str(getattr(args, "keyword", "") or "").strip()
    if keyword:
        files = [
            item
            for item in files
            if keyword in str(item.get("title") or "")
            or keyword in str(item.get("relative_path") or "")
            or keyword in str(item.get("kind_label") or "")
            or keyword in str(item.get("description") or "")
        ]
    limit = max(1, int(getattr(args, "limit", 10) or 10))
    rows = []
    for item in files[:limit]:
        preview: list[str] = []
        markdown = item.get("markdown")
        if markdown:
            md_path = ROOT / markdown
            if md_path.exists():
                text_lines = [
                    line.strip()
                    for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.startswith(">") and not line.startswith("#") and line != "---"
                ]
                preview = text_lines[: max(0, int(getattr(args, "preview_lines", 8) or 8))]
        rows.append({**item, "preview": preview})
    return {
        "source": str(VIP_MATERIALS_MANIFEST.relative_to(ROOT)),
        "index_file": str((VIP_MATERIALS_DIR / "index.md").relative_to(ROOT)),
        "base_path": manifest.get("base_path"),
        "kind": kind,
        "keyword": keyword,
        "total_files": manifest.get("file_count", len(manifest.get("files", []))),
        "total_size_mb": round(float(manifest.get("total_size_bytes", 0)) / 1024 / 1024, 2),
        "extracted_count": manifest.get("extracted_count", 0),
        "matched_count": len(files),
        "files": rows,
    }


def build_sprint_material_payload(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_sprint_materials_manifest()
    files = list(manifest.get("files", []))
    kind = getattr(args, "kind", "all") or "all"
    if kind != "all":
        files = [item for item in files if item.get("kind") == kind]
    keyword = str(getattr(args, "keyword", "") or "").strip()
    if keyword:
        files = [
            item
            for item in files
            if keyword in str(item.get("title") or "")
            or keyword in str(item.get("relative_path") or "")
            or keyword in str(item.get("kind_label") or "")
            or keyword in str(item.get("description") or "")
        ]
    limit = max(1, int(getattr(args, "limit", 10) or 10))
    rows = []
    for item in files[:limit]:
        preview: list[str] = []
        markdown = item.get("markdown")
        if markdown:
            md_path = ROOT / markdown
            if md_path.exists():
                text_lines = [
                    line.strip()
                    for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.startswith(">") and not line.startswith("#") and line != "---"
                ]
                preview = text_lines[: max(0, int(getattr(args, "preview_lines", 8) or 8))]
        rows.append({**item, "preview": preview})
    return {
        "source": str(SPRINT_MATERIALS_MANIFEST.relative_to(ROOT)),
        "index_file": str((SPRINT_MATERIALS_DIR / "index.md").relative_to(ROOT)),
        "base_path": manifest.get("base_path"),
        "kind": kind,
        "keyword": keyword,
        "total_files": manifest.get("file_count", len(manifest.get("files", []))),
        "existing_count": manifest.get("existing_count", 0),
        "total_size_mb": round(float(manifest.get("total_size_bytes", 0)) / 1024 / 1024, 2),
        "extracted_count": manifest.get("extracted_count", 0),
        "needs_ocr_count": manifest.get("needs_ocr_count", 0),
        "matched_count": len(files),
        "files": rows,
    }


def load_recitation_items(chapter: int | None = None) -> list[dict[str, Any]]:
    if chapter:
        path = CASE_RECITATION_STRUCTURED_DIR / f"chapter_{int(chapter):02d}.json"
    else:
        path = CASE_RECITATION_STRUCTURED_DIR / "recitation_items.json"
    return load_internal_json(path, [])


def build_recitation_payload(args: argparse.Namespace) -> dict[str, Any]:
    items = load_recitation_items(args.chapter)
    limit = max(1, int(args.count))
    selected = items[:limit]
    report = load_internal_json(CASE_RECITATION_STRUCTURED_DIR / "quality_report.json", {})
    return {
        "source": "有答案版/无答案版-系规案例背诵",
        "status": "candidate_only",
        "note": "用于案例默写和采分点候选预览；其中部分内容已正式入库，继续提升前需先做质量门禁和回归测试。",
        "chapter": args.chapter,
        "total_available": len(items),
        "quality_report": {
            "total": report.get("total"),
            "issue_counts": report.get("issue_counts"),
        },
        "items": selected,
        "show_answer": bool(args.show_answer),
        "index_file": str((CASE_RECITATION_STRUCTURED_DIR / "index.md").relative_to(ROOT)),
    }


BACKUP_CATEGORY_LABELS = {
    "past-exam": "历年真题",
    "standards": "标准规范库",
    "mock": "模拟题库",
    "all": "全部",
}


def load_backup_pdf_manifest() -> dict[str, Any]:
    return load_internal_json(BACKUP_PDFS_MANIFEST, {"files": []})


def backup_category_from_text(text: str) -> str:
    if any(word in text for word in ("真题", "历年", "上午", "案例真题", "论文真题")):
        return "past-exam"
    if any(word in text for word in ("标准", "规范", "法规", "ISO", "GB", "法律")):
        return "standards"
    if any(word in text for word in ("模拟", "押题", "冲刺")):
        return "mock"
    return "all"


def build_backup_pdf_payload(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_backup_pdf_manifest()
    files = list(manifest.get("files", []))
    category = getattr(args, "category", "all") or "all"
    if category != "all":
        files = [item for item in files if item.get("category") == category]
    if getattr(args, "year", None):
        files = [item for item in files if int(item.get("year") or 0) == int(args.year)]
    if getattr(args, "subject", None):
        files = [item for item in files if str(args.subject) in str(item.get("subject") or "")]
    rows = sorted(files, key=lambda item: (str(item.get("category") or ""), int(item.get("year") or 0), str(item.get("title") or "")))
    limit = max(1, int(getattr(args, "limit", 20) or 20))
    return {
        "source": str(BACKUP_PDFS_MANIFEST.relative_to(ROOT)),
        "index_file": str((BACKUP_PDFS_DIR / "index.md").relative_to(ROOT)),
        "base_path": manifest.get("base_path"),
        "category": category,
        "category_label": BACKUP_CATEGORY_LABELS.get(category, category),
        "total_files": manifest.get("file_count", len(manifest.get("files", []))),
        "total_size_mb": round(float(manifest.get("total_size_bytes", 0)) / 1024 / 1024, 2),
        "extracted_count": manifest.get("extracted_count", 0),
        "needs_ocr_count": manifest.get("needs_ocr_count", 0),
        "matched_count": len(rows),
        "files": rows[:limit],
    }


def session_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not SESSIONS_DIR.exists():
        return records
    for path in sorted(SESSIONS_DIR.glob("*.json")):
        try:
            session = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(session, dict):
            continue
        records.append({"path": path, "session": session, "created_at": session.get("created_at") or ""})
    records.sort(key=lambda item: (str(item["created_at"]), str(item["path"])), reverse=True)
    return records


def completed_session_ids() -> set[str]:
    progress = load_progress()
    return {str(session.get("id")) for session in progress.get("sessions", []) if session.get("id")}


def is_session_completed(session: dict[str, Any], completed_ids: set[str] | None = None) -> bool:
    completed_ids = completed_ids if completed_ids is not None else completed_session_ids()
    session_id = str(session.get("id") or "")
    if session.get("type") in {"case_study", "past_exam_case"}:
        return bool(session.get("case_attempts"))
    return session_id in completed_ids


def latest_session(kind: str | None = None, open_only: bool = False) -> dict[str, Any] | None:
    completed_ids = completed_session_ids()
    for record in session_records():
        session = record["session"]
        if kind and session.get("type") != kind:
            continue
        if open_only and is_session_completed(session, completed_ids):
            continue
        return record
    return None


def answer_payload_from_text(text: str) -> dict[str, str] | None:
    raw = text.strip()
    if not raw:
        return None
    marker = re.search(r"(?:答案|作答|我选|选择|提交|答题|我的答案)\s*(?:是|为|:|：)?\s*(.+)$", raw, re.IGNORECASE)
    candidate = marker.group(1).strip() if marker else raw
    compact = re.sub(r"[\s,，;；、。\.]+", "", candidate).upper()
    numbered = re.findall(r"(?:第?\s*\d+\s*(?:题)?\s*[:：.、-]?\s*)([A-Da-d])", candidate)
    compact_numbered = re.findall(r"\d+([A-D])", compact)
    separated = re.findall(r"(?<![A-Za-z])[A-Da-d](?![A-Za-z])", candidate)
    if compact and re.fullmatch(r"[A-D]+", compact) and (marker or len(compact) >= 2):
        return {"raw": candidate, "choices": " ".join(compact)}
    if numbered and (marker or len(numbered) >= 2):
        return {"raw": candidate, "choices": " ".join(value.upper() for value in numbered)}
    if compact_numbered and (marker or len(compact_numbered) >= 2):
        return {"raw": candidate, "choices": " ".join(value.upper() for value in compact_numbered)}
    if separated and (marker or re.fullmatch(r"[A-Da-d\s,，;；、。\.]+", candidate)):
        return {"raw": candidate, "choices": " ".join(value.upper() for value in separated)}
    if marker and len(candidate) >= 8:
        return {"raw": candidate, "choices": ""}
    return None


def inline_text_after_marker(text: str, markers: tuple[str, ...]) -> str | None:
    for marker in markers:
        if marker in text:
            value = text.split(marker, 1)[1].strip(" ：:\n\t")
            if value:
                return value
    return None


def filter_questions(questions: list[dict[str, Any]], args: argparse.Namespace) -> list[dict[str, Any]]:
    result = list(questions)
    if getattr(args, "knowledge_point", None):
        result = [question for question in result if args.knowledge_point in str(question.get("knowledge_point", ""))]
    if getattr(args, "section", None):
        result = [question for question in result if args.section in str(question.get("section", ""))]
    if getattr(args, "tag", None):
        result = [question for question in result if any(args.tag in str(tag) for tag in question.get("tags", []))]
    return result


def difficulty_plan(total: int, distribution: dict[str, float]) -> dict[str, int]:
    raw = {difficulty: total * ratio for difficulty, ratio in distribution.items()}
    counts = {difficulty: int(value) for difficulty, value in raw.items()}
    remaining = total - sum(counts.values())
    for difficulty, _ in sorted(raw.items(), key=lambda item: item[1] - int(item[1]), reverse=True):
        if remaining <= 0:
            break
        counts[difficulty] += 1
        remaining -= 1
    return counts


def choose_with_difficulty(pool: list[dict[str, Any]], count: int, distribution: dict[str, float], seed: int | None) -> list[dict[str, Any]]:
    if not distribution or not all("difficulty" in question for question in pool):
        return choose_questions(pool, count, seed=seed)
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for offset, (difficulty, target) in enumerate(difficulty_plan(count, distribution).items()):
        picked = choose_questions(pool, target, seed=None if seed is None else seed + offset, exclude_ids=selected_ids, difficulty=difficulty)
        selected.extend(picked)
        selected_ids.update(question["id"] for question in picked)
    if len(selected) < count:
        selected.extend(choose_questions(pool, count - len(selected), seed=seed, exclude_ids=selected_ids))
    return selected[:count]


def load_case_studies() -> list[dict[str, Any]]:
    data = load_json(ROOT / "assets" / "questions" / "case_studies.json")
    return data.get("case_studies", [])


def load_past_exams() -> dict[str, Any]:
    return load_json(
        PAST_EXAMS_FILE,
        {
            "stats": {},
            "choice_questions": [],
            "case_studies": [],
            "paper_topics": [],
        },
    )


def load_past_exam_choices() -> list[dict[str, Any]]:
    data = load_past_exams()
    rows = data.get("choice_questions", [])
    return rows if isinstance(rows, list) else []


def load_past_exam_cases() -> list[dict[str, Any]]:
    data = load_past_exams()
    rows = data.get("case_studies", [])
    return rows if isinstance(rows, list) else []


def load_past_exam_papers() -> list[dict[str, Any]]:
    data = load_past_exams()
    rows = data.get("paper_topics", [])
    return rows if isinstance(rows, list) else []


def load_standards_training() -> dict[str, Any]:
    return load_json(
        STANDARDS_TRAINING_FILE,
        {
            "stats": {},
            "documents": [],
            "clauses": [],
            "questions": [],
            "skipped_documents": [],
        },
    )


def load_standard_documents() -> list[dict[str, Any]]:
    rows = load_standards_training().get("documents", [])
    return rows if isinstance(rows, list) else []


def load_standard_clauses() -> list[dict[str, Any]]:
    rows = load_standards_training().get("clauses", [])
    return rows if isinstance(rows, list) else []


def load_standard_questions() -> list[dict[str, Any]]:
    rows = load_standards_training().get("questions", [])
    return rows if isinstance(rows, list) else []


def standards_question_lookup() -> dict[str, dict[str, Any]]:
    return {str(question.get("id")): question for question in load_standard_questions() if question.get("id")}


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


def clean_text_for_preview(text: str) -> str:
    value = str(text or "").replace("\u3000", " ")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", value)
    return value.strip()


def filter_year_period(rows: list[dict[str, Any]], year: int | None = None, period: str | None = None) -> list[dict[str, Any]]:
    result = list(rows)
    if year is not None:
        result = [row for row in result if int(row.get("year") or 0) == int(year)]
    if period:
        result = [row for row in result if str(row.get("period") or "") == period]
    return result


def normalize_search_text(value: str | None) -> str:
    text = str(value or "").lower()
    return re.sub(r"[\s_\-—:：/\\（）()《》“”\"'，,。.;；]+", "", text)


def match_document_text(row: dict[str, Any], keyword: str | None) -> bool:
    if not keyword:
        return True
    needle = normalize_search_text(keyword)
    if not needle:
        return True
    values = [
        row.get("title"),
        row.get("id"),
        row.get("document_id"),
        row.get("section"),
        row.get("source_ref"),
    ]
    values.extend(row.get("tags") or [])
    return any(needle in normalize_search_text(str(value)) for value in values if value)


def standard_doc_by_id() -> dict[str, dict[str, Any]]:
    return {str(doc.get("id")): doc for doc in load_standard_documents() if doc.get("id")}


def filter_standard_rows(rows: list[dict[str, Any]], document: str | None = None, tag: str | None = None) -> list[dict[str, Any]]:
    result = [row for row in rows if match_document_text(row, document)]
    if tag:
        result = [row for row in result if any(tag in str(item) for item in row.get("tags", []))]
    return result


def public_past_exam_question(question: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    result = public_question(question, include_answer=include_answer)
    for key in ("year", "period", "subject", "number", "source_pdf"):
        if key in question:
            result[key] = question[key]
    return result


def past_exam_choice_lookup() -> dict[str, dict[str, Any]]:
    return {str(question.get("id")): question for question in load_past_exam_choices() if question.get("id")}


def build_past_exam_choice_payload(args: argparse.Namespace) -> dict[str, Any]:
    choices = filter_year_period(load_past_exam_choices(), getattr(args, "year", None), getattr(args, "period", None))
    available = len(choices)
    selected = choose_questions(choices, int(args.count), seed=getattr(args, "seed", None))
    session = make_session(
        "past_exam",
        [question["id"] for question in selected],
        {
            "year": getattr(args, "year", None),
            "period": getattr(args, "period", None),
            "count": int(args.count),
            "seed": getattr(args, "seed", None),
            "source": str(PAST_EXAMS_FILE.relative_to(ROOT)),
        },
    )
    session_path = write_session(session)
    return {
        "title": "历年真题选择题",
        "session": session,
        "session_file": str(session_path.relative_to(ROOT)),
        "year": getattr(args, "year", None),
        "period": getattr(args, "period", None),
        "available": available,
        "questions": [public_past_exam_question(question) for question in selected],
        "next_step": f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown",
    }


def render_past_exam_choice_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 历年真题选择题",
        "",
        f"- Session: {payload['session']['id']}",
        f"- File: {payload['session_file']}",
        f"- 筛选：{payload.get('year') or '全部年份'} {payload.get('period') or ''}".rstrip(),
        f"- 可用题数：{payload['available']}",
        "",
    ]
    questions = payload.get("questions") or []
    if questions:
        lines.append(render_questions_markdown(questions).rstrip())
        lines.append("")
        lines.append(f"Next: {payload['next_step']}")
    else:
        lines.append("没有匹配到可训练的历年真题选择题。")
    return "\n".join(lines) + "\n"


def command_past_exam_start(args: argparse.Namespace) -> int:
    payload = build_past_exam_choice_payload(args)
    if args.format == "markdown":
        print(render_past_exam_choice_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def public_past_exam_case(case: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    result = public_case(case, include_answer=include_answer)
    for key in ("year", "period", "subject", "number", "source_ref", "source_pdf", "tags", "source"):
        if key in case:
            result[key] = case[key]
    return result


def build_past_exam_case_payload(args: argparse.Namespace) -> dict[str, Any]:
    cases = filter_year_period(load_past_exam_cases(), getattr(args, "year", None), getattr(args, "period", None))
    available = len(cases)
    selected = choose_questions(cases, int(args.count), seed=getattr(args, "seed", None))
    session = make_session(
        "past_exam_case",
        [case["id"] for case in selected],
        {
            "year": getattr(args, "year", None),
            "period": getattr(args, "period", None),
            "count": int(args.count),
            "seed": getattr(args, "seed", None),
            "source": str(PAST_EXAMS_FILE.relative_to(ROOT)),
        },
    )
    session["case_ids"] = session.pop("question_ids")
    session["answers_template"] = {question["id"]: "" for case in selected for question in case.get("questions", [])}
    session_path = write_session(session)
    return {
        "title": "历年案例真题",
        "session": session,
        "session_file": str(session_path.relative_to(ROOT)),
        "year": getattr(args, "year", None),
        "period": getattr(args, "period", None),
        "available": available,
        "cases": [public_past_exam_case(case, include_answer=getattr(args, "show_answer", False)) for case in selected],
        "next_step": f"python scripts/study.py case submit --session {session['id']} --answers \"...\" --format markdown",
    }


def render_past_exam_case_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 历年案例真题",
        "",
        f"- Session: {payload['session']['id']}",
        f"- File: {payload['session_file']}",
        f"- 筛选：{payload.get('year') or '全部年份'} {payload.get('period') or ''}".rstrip(),
        f"- 可用案例：{payload['available']}",
    ]
    if not payload.get("cases"):
        lines.append("")
        lines.append("没有匹配到可训练的案例真题。")
        return "\n".join(lines) + "\n"
    for case in payload["cases"]:
        lines.append("")
        lines.append(render_case_markdown(case, include_answer=False).rstrip())
    lines.append("")
    lines.append(f"Next: {payload['next_step']}")
    return "\n".join(lines) + "\n"


def command_past_exam_case(args: argparse.Namespace) -> int:
    payload = build_past_exam_case_payload(args)
    if args.format == "markdown":
        print(render_past_exam_case_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_past_exam_paper_payload(args: argparse.Namespace) -> dict[str, Any]:
    topics = filter_year_period(load_past_exam_papers(), getattr(args, "year", None), getattr(args, "period", None))
    if getattr(args, "topic", None):
        topic_text = str(args.topic)
        topics = [topic for topic in topics if topic_text in str(topic.get("title") or "") or topic_text in str(topic.get("prompt") or "")]
    available = len(topics)
    limit = max(1, int(getattr(args, "count", 5) or 5))
    selected = choose_questions(topics, limit, seed=getattr(args, "seed", None))
    return {
        "title": "历年论文真题",
        "year": getattr(args, "year", None),
        "period": getattr(args, "period", None),
        "available": available,
        "topics": selected,
        "source": str(PAST_EXAMS_FILE.relative_to(ROOT)),
    }


def render_past_exam_paper_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 历年论文真题",
        "",
        f"- 筛选：{payload.get('year') or '全部年份'} {payload.get('period') or ''}".rstrip(),
        f"- 可用题目：{payload['available']}",
        f"- 来源：{payload['source']}",
        "",
    ]
    if not payload.get("topics"):
        lines.append("没有匹配到论文真题。")
        return "\n".join(lines) + "\n"
    for index, topic in enumerate(payload["topics"], start=1):
        lines.append(f"{index}. [{topic.get('id')}] {topic.get('year')}{topic.get('period') or ''} {topic.get('title')}")
        lines.append(f"   Source: {topic.get('source_ref')}")
        prompt = str(topic.get("prompt") or "").strip()
        if prompt:
            lines.append("   " + re.sub(r"\s+", " ", prompt[:260]).strip())
        lines.append(f"   训练命令：python scripts/study.py paper --topic \"{topic.get('title')}\" --format markdown")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_past_exam_paper(args: argparse.Namespace) -> int:
    payload = build_past_exam_paper_payload(args)
    if args.format == "markdown":
        print(render_past_exam_paper_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def public_standard_question(question: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    result = public_question(question, include_answer=include_answer)
    for key in ("document_id", "clause_id", "source_pdf"):
        if key in question:
            result[key] = question[key]
    return result


def build_standards_list_payload(args: argparse.Namespace) -> dict[str, Any]:
    data = load_standards_training()
    documents = filter_standard_rows(load_standard_documents(), getattr(args, "document", None), getattr(args, "tag", None))
    skipped = data.get("skipped_documents", [])
    limit = max(1, int(getattr(args, "limit", 20) or 20))
    return {
        "title": "标准规范结构化训练库",
        "source": str(STANDARDS_TRAINING_FILE.relative_to(ROOT)),
        "summary_file": str((BACKUP_PDFS_DIR / "standards" / "structured-summary.md").relative_to(ROOT)),
        "stats": data.get("stats", {}),
        "documents": documents[:limit],
        "matched_count": len(documents),
        "skipped_documents": skipped,
    }


def render_standards_list_markdown(payload: dict[str, Any]) -> str:
    stats = payload.get("stats") or {}
    lines = [
        "# 标准规范结构化训练库",
        "",
        f"- 资产：`{payload['source']}`",
        f"- 摘要：`{payload['summary_file']}`",
        f"- 已结构化文档：{stats.get('structured_documents', 0)}/{stats.get('source_documents', 0)}",
        f"- 条款：{stats.get('clauses', 0)}，训练题：{stats.get('questions', 0)}",
        f"- 匹配文档：{payload['matched_count']}",
        "",
        "## 可训练文档",
    ]
    if not payload.get("documents"):
        lines.append("- 暂无匹配文档。")
    for doc in payload.get("documents") or []:
        lines.append(f"- [{doc.get('id')}] {doc.get('title')}：{doc.get('clause_count', 0)} 条款，类型 {doc.get('document_type')}")
        lines.append(f"  `{doc.get('source_ref')}`")
    skipped = payload.get("skipped_documents") or []
    if skipped:
        lines.extend(["", "## 待 OCR / 未结构化"])
        for item in skipped[:10]:
            lines.append(f"- {item.get('title')}：{item.get('reason')}，文本 {item.get('text_chars', 0)} 字")
    lines.extend(
        [
            "",
            "Next: python scripts/study.py standards start --document 网络安全法 --count 5 --format markdown",
        ]
    )
    return "\n".join(lines) + "\n"


def command_standards_list(args: argparse.Namespace) -> int:
    payload = build_standards_list_payload(args)
    if args.format == "markdown":
        print(render_standards_list_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_standards_clauses_payload(args: argparse.Namespace) -> dict[str, Any]:
    clauses = filter_standard_rows(load_standard_clauses(), getattr(args, "document", None), getattr(args, "tag", None))
    if getattr(args, "keyword", None):
        keyword = str(args.keyword)
        clauses = [
            clause for clause in clauses
            if keyword in str(clause.get("title") or "") or keyword in str(clause.get("text") or "") or keyword in str(clause.get("summary") or "")
        ]
    docs = standard_doc_by_id()
    limit = max(1, int(getattr(args, "limit", 10) or 10))
    rows = []
    for clause in clauses[:limit]:
        doc = docs.get(str(clause.get("document_id")), {})
        rows.append({**clause, "document_title": doc.get("title")})
    return {
        "title": "标准规范条款检索",
        "source": str(STANDARDS_TRAINING_FILE.relative_to(ROOT)),
        "document": getattr(args, "document", None),
        "keyword": getattr(args, "keyword", None),
        "matched_count": len(clauses),
        "clauses": rows,
    }


def render_standards_clauses_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 标准规范条款检索",
        "",
        f"- 来源：`{payload['source']}`",
        f"- 文档筛选：{payload.get('document') or '全部'}",
        f"- 关键词：{payload.get('keyword') or '-'}",
        f"- 匹配条款：{payload['matched_count']}",
        "",
    ]
    if not payload.get("clauses"):
        lines.append("暂无匹配条款。")
        return "\n".join(lines) + "\n"
    for index, clause in enumerate(payload["clauses"], start=1):
        summary = re.sub(r"\s+", " ", str(clause.get("summary") or clause.get("text") or "")).strip()
        summary = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", summary)
        summary = re.sub(r"(?<=[，、；：。])\s+(?=[\u4e00-\u9fff])", "", summary)
        clause_no = str(clause.get("clause_no") or "")
        clause_title = str(clause.get("title") or "")
        title_part = clause_title if clause_title and clause_title != clause_no else ""
        lines.append(f"{index}. [{clause.get('id')}] {clause.get('document_title')} {clause_no} {title_part}".rstrip())
        lines.append(f"   {summary[:220]}")
        lines.append(f"   Source: {clause.get('source_ref')}")
    return "\n".join(lines).rstrip() + "\n"


def command_standards_clauses(args: argparse.Namespace) -> int:
    payload = build_standards_clauses_payload(args)
    if args.format == "markdown":
        print(render_standards_clauses_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_standards_start_payload(args: argparse.Namespace, write: bool = True) -> dict[str, Any]:
    questions = filter_standard_rows(load_standard_questions(), getattr(args, "document", None), getattr(args, "tag", None))
    if getattr(args, "keyword", None):
        keyword = str(args.keyword)
        questions = [
            question for question in questions
            if keyword in str(question.get("question") or "")
            or keyword in str(question.get("knowledge_point") or "")
            or keyword in str(question.get("explanation") or "")
            or any(keyword in str(tag) for tag in question.get("tags", []))
        ]
    available = len(questions)
    selected = choose_questions(questions, int(args.count), seed=getattr(args, "seed", None))
    session = make_session(
        "standards_training",
        [question["id"] for question in selected],
        {
            "document": getattr(args, "document", None),
            "keyword": getattr(args, "keyword", None),
            "tag": getattr(args, "tag", None),
            "count": int(args.count),
            "seed": getattr(args, "seed", None),
            "source": str(STANDARDS_TRAINING_FILE.relative_to(ROOT)),
        },
    )
    session_file = "<no-write>"
    if write:
        session_path = write_session(session)
        session_file = str(session_path.relative_to(ROOT))
    return {
        "title": "标准规范专项训练",
        "session": session,
        "session_file": session_file,
        "document": getattr(args, "document", None),
        "keyword": getattr(args, "keyword", None),
        "tag": getattr(args, "tag", None),
        "available": available,
        "questions": [public_standard_question(question) for question in selected],
        "next_step": f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown",
        "note": "本训练题由标准规范/法律法规条款结构化生成，不是历年真题。",
    }


def render_standards_start_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 标准规范专项训练",
        "",
        f"- Session: {payload['session']['id']}",
        f"- File: {payload['session_file']}",
        f"- 筛选：{payload.get('document') or '全部文档'} {payload.get('keyword') or ''}".rstrip(),
        f"- 可用题数：{payload['available']}",
        f"- 说明：{payload['note']}",
        "",
    ]
    if payload.get("questions"):
        lines.append(render_questions_markdown(payload["questions"]).rstrip())
        lines.append("")
        lines.append(f"Next: {payload['next_step']}")
    else:
        lines.append("没有匹配到可训练的标准规范题。")
        lines.append("Next: python scripts/study.py standards list --format markdown")
    return "\n".join(lines) + "\n"


def command_standards_start(args: argparse.Namespace) -> int:
    payload = build_standards_start_payload(args)
    if args.format == "markdown":
        print(render_standards_start_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def filter_cases_by_source(cases: list[dict[str, Any]], source: str | None) -> list[dict[str, Any]]:
    if not source or source == "all":
        return cases
    if source == "recitation":
        return [case for case in cases if str(case.get("source") or "") == "2025新版系规案例背诵-正式入库"]
    if source == "scenario":
        return [case for case in cases if str(case.get("source") or "") != "2025新版系规案例背诵-正式入库"]
    return cases


def build_practice(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _, _, by_chapter = load_all_questions()
    chapters = parse_chapters(args.chapters)
    candidates = [question for chapter in chapters for question in by_chapter.get(chapter, [])]
    candidates = filter_questions(candidates, args)
    selected = choose_questions(candidates, args.count, seed=args.seed, difficulty=args.difficulty)
    session = make_session(
        "practice",
        [question["id"] for question in selected],
        {
            "chapters": chapters,
            "count": args.count,
            "difficulty": args.difficulty,
            "knowledge_point": args.knowledge_point,
            "section": args.section,
            "tag": args.tag,
            "seed": args.seed,
        },
    )
    return session, selected


def build_mock(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    config = load_config()
    _, _, by_chapter = load_all_questions()
    exam_config = config["mock_exam"]["single_choice"]
    selected: list[dict[str, Any]] = []
    for index, block in enumerate(exam_config["distribution"]):
        for chapter in block["chapters"]:
            selected.extend(
                choose_with_difficulty(
                    by_chapter.get(chapter, []),
                    int(block["questions_each"]),
                    exam_config.get("difficulty_distribution", {}),
                    None if args.seed is None else args.seed + chapter + index,
                )
            )
    session = make_session("mock_exam", [question["id"] for question in selected], {"seed": args.seed, "distribution": exam_config["distribution"]})
    return session, selected


def build_wrong(args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    archive = load_archive()
    _, by_id, _ = load_all_questions()
    archived_ids = [item.get("question_id") for item in archive.get("archive", []) if item.get("question_id")]
    archived_questions = [by_id[qid] for qid in archived_ids if qid in by_id]
    archived_questions = filter_questions(archived_questions, args)
    selected = choose_questions(archived_questions, args.count, seed=args.seed, difficulty=args.difficulty)
    session = make_session(
        "wrong_retry",
        [question["id"] for question in selected],
        {
            "count": args.count,
            "difficulty": args.difficulty,
            "knowledge_point": args.knowledge_point,
            "section": args.section,
            "tag": args.tag,
            "seed": args.seed,
        },
    )
    return session, selected


def command_start(args: argparse.Namespace) -> int:
    if args.mode == "mock":
        session, selected = build_mock(args)
    elif args.mode == "wrong":
        session, selected = build_wrong(args)
    else:
        session, selected = build_practice(args)
    session_path = write_session(session)
    payload = {
        "session": session,
        "session_file": str(session_path.relative_to(ROOT)),
        "questions": [public_question(question, include_answer=False) for question in selected],
        "next_step": f"Submit answers with: python scripts/study.py submit --session {session['id']} --answers \"A B C ...\"",
    }
    if args.format == "markdown":
        print(f"Session: {session['id']}")
        print(f"File: {session_path.relative_to(ROOT)}\n")
        if selected:
            print(render_questions_markdown(selected))
            print(payload["next_step"])
        else:
            print("No questions matched this request.")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def grade_session(session: dict[str, Any], answers: dict[str, str], record: bool) -> dict[str, Any]:
    _, by_id, _ = load_all_questions()
    if session.get("type") == "past_exam":
        by_id = {**by_id, **past_exam_choice_lookup()}
    if session.get("type") == "standards_training":
        by_id = {**by_id, **standards_question_lookup()}
    if session.get("type") == "sprint_training":
        by_id = {**by_id, **sprint_training_question_lookup()}
    results: list[dict[str, Any]] = []
    answer_records: list[dict[str, Any]] = []
    correct_count = 0
    wrong_questions: list[dict[str, Any]] = []

    for qid in session.get("question_ids", []):
        question = by_id.get(qid)
        if not question:
            continue
        user_answer = answers.get(qid, "")
        correct_answer = question.get("answer")
        is_correct = user_answer == correct_answer
        correct_count += 1 if is_correct else 0
        result = {
            "question_id": qid,
            "chapter": question.get("chapter"),
            "knowledge_point": question.get("knowledge_point"),
            "section": question.get("section"),
            "source": question.get("source"),
            "year": question.get("year"),
            "period": question.get("period"),
            "user_answer": user_answer,
            "correct_answer": correct_answer,
            "is_correct": is_correct,
            "explanation": question.get("explanation"),
        }
        results.append(result)
        answer_records.append(
            {
                "session_id": session.get("id"),
                "question_id": qid,
                "chapter": question.get("chapter"),
                "knowledge_point": question.get("knowledge_point"),
                "section": question.get("section"),
                "user_answer": user_answer,
                "correct_answer": correct_answer,
                "is_correct": is_correct,
                "answered_at": session.get("created_at"),
            }
        )
        if not is_correct:
            wrong_questions.append(question)
            if record:
                record_wrong_answer(question, user_answer)
        elif record and session.get("type") == "wrong_retry":
            mark_reviewed(qid)

    total = len(results)
    summary = {
        "session_id": session.get("id"),
        "total": total,
        "correct": correct_count,
        "wrong": total - correct_count,
        "score_percent": round((correct_count / total) * 100, 2) if total else 0,
    }
    if record:
        append_progress(session, answer_records, summary)
    return {"summary": summary, "results": results, "recorded": record, "recommendation": recommendation(summary, results)}


def recommendation(summary: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    wrong = [item for item in results if not item["is_correct"]]
    if not wrong:
        return {"message": "本次全对。建议提高难度或进入下一章。", "focus": []}
    focus_counts: dict[str, int] = {}
    for item in wrong:
        key = item.get("knowledge_point") or item.get("section") or item.get("chapter")
        focus_counts[key] = focus_counts.get(key, 0) + 1
    focus = sorted(focus_counts.items(), key=lambda item: item[1], reverse=True)
    return {
        "message": "优先复习本次错题对应知识点，并在到期复习中再次检查。",
        "focus": [{"knowledge_point": key, "wrong": count} for key, count in focus[:5]],
    }


def render_grade_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"Score: {summary['correct']}/{summary['total']} ({summary['score_percent']}%)",
        f"Recorded: {payload['recorded']}",
    ]
    if payload.get("session_id"):
        lines.append(f"Session: {payload['session_id']}")
    for item in payload["results"]:
        mark = "OK" if item["is_correct"] else "WRONG"
        lines.append(f"- {mark} {item['question_id']}: your {item['user_answer'] or '-'}, answer {item['correct_answer']}")
        if not item["is_correct"]:
            lines.append(f"  {item['explanation']}")
    lines.append("")
    lines.append(f"Next: {payload['recommendation']['message']}")
    return "\n".join(lines) + "\n"


def command_submit(args: argparse.Namespace) -> int:
    session_path = resolve_session(args.session)
    session = load_json(session_path)
    answers = parse_answer_text(args.answers, session.get("question_ids", []))
    payload = grade_session(session, answers, record=not args.no_record)
    payload["session_id"] = session.get("id")
    if args.format == "markdown":
        print(render_grade_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def due_items(limit: int, review_date_text: str | None = None) -> list[dict[str, Any]]:
    review_date = parse_date(review_date_text) or today()
    archive = load_archive()
    _, by_id, _ = load_all_questions()
    due: list[dict[str, Any]] = []
    for item in archive.get("archive", []):
        next_review = parse_date(item.get("next_review"))
        if next_review and next_review <= review_date:
            question = by_id.get(item.get("question_id"))
            due.append({"archive": item, "question": public_question(question, include_answer=True) if question else None})
    return due[:limit]


def command_review(args: argparse.Namespace) -> int:
    if args.mark_reviewed:
        updated = [mark_reviewed(qid) for qid in args.mark_reviewed]
        print(json.dumps({"updated": [item for item in updated if item]}, ensure_ascii=False, indent=2))
        return 0
    due = due_items(args.limit, args.date)
    payload = {"date": (parse_date(args.date) or today()).isoformat(), "count": len(due), "due": due}
    if args.format == "markdown":
        print(f"Due review on {payload['date']}: {len(due)} item(s)")
        for item in due:
            archive_item = item["archive"]
            question = item.get("question") or {}
            print(f"- {archive_item.get('question_id')} {archive_item.get('chapter')} wrong_count={archive_item.get('wrong_count')}")
            print(f"  {question.get('question')}")
            print(f"  Answer: {question.get('answer')}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


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

    if profile_has_weak_subject(profile, "案例", "主观题"):
        case_count = profile_case_count(profile)
        add_task(
            {
                "priority": 3,
                "type": "profile_case",
                "title": "案例分析采分点训练",
                "count": case_count,
                "unit": "个",
                "command": f"python scripts/study.py case start --chapters {case_range_chapters_text()} --count {case_count} --format markdown",
                "source": "assets/profile/learner_profile.json",
            }
        )

    if profile_has_weak_subject(profile, "论文", "作文"):
        add_task(
            {
                "priority": 4,
                "type": "profile_paper",
                "title": "论文框架训练",
                "count": 1,
                "unit": "篇",
                "command": f"python scripts/study.py paper --topic {DEFAULT_PAPER_TOPIC} --format markdown",
                "source": "assets/profile/learner_profile.json",
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
        "practice_count": practice_count,
        "task_budget": task_budget,
        "tasks": tasks,
    }


def render_plan_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# 每日学习计划 {payload['date']}",
        "",
        f"- 已答题：{payload['answered']}",
        f"- 到期复习：{payload['due_review_count']}",
        f"- 新版大纲高优先级章节：{','.join(str(chapter) for chapter in payload['focus_chapters'])}",
        f"- 画像：每日 {payload['profile']['daily_minutes']} 分钟，{payload['profile']['study_load']}负荷，策略：{payload['profile'].get('strategy') or '待确认'}",
        f"- 今日自动题量：{payload['practice_count']} 题；任务上限：{payload['task_budget']} 项",
        "",
        "## 今日任务",
    ]
    for index, task in enumerate(payload["tasks"], start=1):
        lines.append(f"{index}. {task['title']} ({task['count']}{task.get('unit', '题')})")
        lines.append(f"   {task['command']}")
    lines.append("")
    lines.append("画像入口：python scripts/study.py profile --format markdown")
    return "\n".join(lines) + "\n"


def command_plan(args: argparse.Namespace) -> int:
    payload = build_plan_payload(args)
    if args.format == "markdown":
        print(render_plan_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_profile_payload(args: argparse.Namespace | None = None) -> dict[str, Any]:
    profile = load_learner_profile()
    summary = profile_summary(profile)
    return {
        "profile": profile,
        "summary": summary,
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


def public_case(case: dict[str, Any], include_answer: bool = False) -> dict[str, Any]:
    questions = []
    for question in case.get("questions", []):
        item = {
            "id": question.get("id"),
            "question": question.get("question"),
            "question_type": question.get("question_type", "choice" if question.get("options") else "subjective"),
            "score": question.get("score"),
        }
        if question.get("options"):
            item["options"] = question.get("options")
        if include_answer:
            item["answer"] = question.get("answer")
            item["explanation"] = question.get("explanation")
        questions.append(item)
    return {
        "id": case.get("id"),
        "chapter": case.get("chapter"),
        "chapters": case.get("chapters", [case.get("chapter")]),
        "title": case.get("title"),
        "difficulty": case.get("difficulty"),
        "total_score": case.get("total_score"),
        "scenario": case.get("scenario"),
        "questions": questions,
    }


def render_case_markdown(case: dict[str, Any], include_answer: bool = False) -> str:
    lines = [f"# {case.get('title')} [{case.get('id')}]", "", str(case.get("scenario", "")), ""]
    for index, question in enumerate(case.get("questions", []), start=1):
        lines.append(f"{index}. [{question.get('id')}] {question.get('question')}")
        for option in question.get("options", []):
            lines.append(f"   {option}")
        if include_answer:
            lines.append(f"   Answer: {question.get('answer')}")
            if question.get("explanation"):
                lines.append(f"   Explanation: {question.get('explanation')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_case_answer_text(answer_text: str, question_ids: list[str]) -> dict[str, str]:
    text = answer_text.strip()
    if not text:
        return {}
    if text.startswith("{"):
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("JSON answers must be an object mapping question id to answer")
        return {str(key): str(value).strip() for key, value in data.items()}
    if "=" in text or ":" in text or "：" in text:
        keyed = list(re.finditer(r"(?<!\w)([A-Za-z][A-Za-z0-9_]*_q\d+)\s*[=：:]", text))
        if keyed:
            answers = {}
            for idx, match in enumerate(keyed):
                start = match.end()
                end = keyed[idx + 1].start() if idx + 1 < len(keyed) else len(text)
                answers[match.group(1).strip()] = text[start:end].strip(" \t\r\n,，;；")
            return answers
        answers: dict[str, str] = {}
        for part in re.split(r"[,;\n]+", text):
            item = part.strip()
            if not item:
                continue
            if "=" in item:
                key, value = item.split("=", 1)
            elif "：" in item:
                key, value = item.split("：", 1)
            else:
                key, value = item.split(":", 1)
            answers[key.strip()] = value.strip()
        return answers
    return parse_answer_text(text, question_ids)


def case_keywords(reference: str, limit: int = 16) -> list[str]:
    chunks = re.split(r"[；;。.!！?？\n]|(?:\(\d+\))|(?:（\d+）)", reference or "")
    phrases = []
    for chunk in chunks:
        cleaned = re.sub(r"^[\s:：,，、\-—]+|[\s:：,，、\-—]+$", "", chunk)
        if 4 <= len(cleaned) <= 28 and not any(term in cleaned for term in ("可能原因分析", "提升策略", "计算方法")):
            phrases.append(cleaned)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+/.-]{1,}|[\u4e00-\u9fff]{2,}", reference or "")
    keywords = []
    for phrase in phrases:
        if phrase not in keywords:
            keywords.append(phrase)
    for token in tokens:
        item = token.strip("：:，,。；;（）()、-—")
        if len(item) < 2 or item in GENERIC_CASE_TERMS:
            continue
        if item not in keywords:
            keywords.append(item)
    return keywords[:limit]


def char_ngrams(text: str, size: int = 2) -> set[str]:
    normalized = normalize_text(text)
    if len(normalized) < size:
        return {normalized} if normalized else set()
    return {normalized[index:index + size] for index in range(len(normalized) - size + 1)}


def point_matched(point: str, normalized_answer: str) -> bool:
    normalized_point = normalize_text(point)
    if not normalized_point:
        return False
    if normalized_point in normalized_answer:
        return True
    point_grams = char_ngrams(normalized_point)
    answer_grams = char_ngrams(normalized_answer)
    if point_grams and len(point_grams & answer_grams) / len(point_grams) >= 0.45:
        return True
    if len(normalized_point) >= 6:
        parts = re.findall(r"[A-Za-z][A-Za-z0-9+/.-]{1,}|[\u4e00-\u9fff]{2,}", point)
        meaningful = [part for part in parts if part not in GENERIC_CASE_TERMS and len(part) >= 2]
        if meaningful:
            hits = sum(1 for part in meaningful if normalize_text(part) in normalized_answer)
            return hits / len(meaningful) >= 0.5
    return False


def grade_subjective_answer(user_answer: str, reference_answer: str, max_score: int) -> dict[str, Any]:
    keywords = case_keywords(reference_answer)
    normalized = normalize_text(user_answer)
    matched = [keyword for keyword in keywords if point_matched(keyword, normalized)]
    missing = [keyword for keyword in keywords if not point_matched(keyword, normalized)]
    coverage = len(matched) / len(keywords) if keywords else 0
    answer_terms = [
        term for term in re.findall(r"[A-Za-z][A-Za-z0-9+/.-]{1,}|[\u4e00-\u9fff]{2,}", user_answer or "")
        if term not in GENERIC_CASE_TERMS
    ]
    reference_terms = [
        term for term in re.findall(r"[A-Za-z][A-Za-z0-9+/.-]{1,}|[\u4e00-\u9fff]{2,}", reference_answer or "")
        if term not in GENERIC_CASE_TERMS
    ]
    reference_terms = list(dict.fromkeys(reference_terms))
    term_matched = [term for term in reference_terms if point_matched(term, normalized)]
    term_missing = [term for term in reference_terms if not point_matched(term, normalized)]
    term_hits = len(term_matched)
    term_coverage = term_hits / len(reference_terms) if reference_terms else 0
    length_ratio = min(1.0, len(normalized) / max(80, min(240, len(normalize_text(reference_answer)))))
    scenario_terms = ["案例", "场景", "问题", "原因", "策略", "措施", "目标", "指标", "风险", "用户", "业务", "平台", "数据", "流程", "组织"]
    scenario_hits = sum(1 for term in scenario_terms if term in user_answer)
    scenario_ratio = min(1.0, scenario_hits / 4)
    problem_terms = ["原因", "问题", "痛点", "不足", "现状", "影响", "瓶颈", "需求", "风险"]
    action_terms = ["优化", "建立", "完善", "制定", "提升", "改进", "监控", "培训", "治理", "协同", "保障", "评估", "闭环", "机制", "流程"]
    metric_terms = ["指标", "KPI", "SLA", "满意度", "正确率", "及时率", "覆盖率", "成本", "效率", "周期", "质量", "%", "％"]
    problem_hits = [term for term in problem_terms if term in user_answer]
    action_hits = [term for term in action_terms if term in user_answer]
    metric_hits = [term for term in metric_terms if term in user_answer]
    if re.search(r"\d+|一|二|三|四|五|六|七|八|九|十", user_answer or ""):
        metric_hits.append("量化表达")
    problem_ratio = min(1.0, len(problem_hits) / 2)
    action_ratio = min(1.0, len(action_hits) / 3)
    metric_ratio = min(1.0, len(metric_hits) / 2)
    structure_markers = re.findall(r"(?:^|[；;。.\n])\s*(?:[一二三四五六七八九十]、|[0-9]+[.、]|首先|其次|再次|最后|第一|第二|第三)", user_answer)
    structure_ratio = min(1.0, len(structure_markers) / 3)
    rubric = [
        ("key_points", "采分点覆盖", 0.36, coverage, matched[:8], missing[:8]),
        ("terms", "关键术语", 0.14, term_coverage, term_matched[:8], term_missing[:8]),
        ("scenario", "场景化表达", 0.1, scenario_ratio, [term for term in scenario_terms if term in user_answer][:8], []),
        ("problem", "问题定位", 0.1, problem_ratio, problem_hits[:8], []),
        ("action", "措施可执行性", 0.12, action_ratio, action_hits[:8], []),
        ("metrics", "量化指标", 0.08, metric_ratio, metric_hits[:8], []),
        ("structure", "结构完整性", 0.06, structure_ratio, structure_markers[:5], []),
        ("length", "答题充分度", 0.04, length_ratio, [], []),
    ]
    score = round(max_score * sum(weight * ratio for _, _, weight, ratio, _, _ in rubric)) if max_score else 0
    if not normalized:
        score = 0
    rubric_rows = [
        {
            "key": key,
            "label": label,
            "weight": weight,
            "ratio": round(ratio, 4),
            "score": round(max_score * weight * ratio, 2) if max_score else 0,
            "max_score": round(max_score * weight, 2) if max_score else 0,
            "matched": hits,
            "missing": misses,
        }
        for key, label, weight, ratio, hits, misses in rubric
    ]
    feedback_parts = []
    if coverage < 0.65:
        feedback_parts.append("优先补齐参考答案中的核心采分点")
    if problem_ratio < 0.5:
        feedback_parts.append("先写清原因、问题或风险定位")
    if action_ratio < 0.67:
        feedback_parts.append("措施要写成可执行动作和闭环机制")
    if metric_ratio < 0.5:
        feedback_parts.append("补充可量化指标或验收标准")
    if scenario_ratio < 0.5:
        feedback_parts.append("结合题干场景写原因、措施和指标")
    if structure_ratio < 0.5:
        feedback_parts.append("用分点结构作答，避免整段堆叙")
    if length_ratio < 0.7:
        feedback_parts.append("答案篇幅偏短，需要展开关键措施")
    return {
        "is_correct": None,
        "auto_score": min(max_score, score),
        "max_score": max_score,
        "keyword_coverage": round(coverage, 4),
        "term_coverage": round(term_coverage, 4),
        "scenario_coverage": round(scenario_ratio, 4),
        "structure_coverage": round(structure_ratio, 4),
        "length_coverage": round(length_ratio, 4),
        "rubric": rubric_rows,
        "matched_points": matched[:10],
        "missing_points": missing[:10],
        "feedback": "；".join(feedback_parts) if feedback_parts else "要点覆盖较好，继续补充场景化表达和量化指标。",
    }


def command_case_start(args: argparse.Namespace) -> int:
    cases = load_case_studies()
    cases = filter_cases_by_source(cases, getattr(args, "source", None))
    if args.chapters:
        chapters = set(parse_chapters(args.chapters))
        cases = [case for case in cases if chapters.intersection(set(case.get("chapters") or [case.get("chapter")]))]
    if args.difficulty:
        filtered = [case for case in cases if case.get("difficulty") == args.difficulty]
        if filtered:
            cases = filtered
    selected = choose_questions(cases, args.count, seed=args.seed)
    session = make_session("case_study", [case["id"] for case in selected], {"chapters": args.chapters, "count": args.count, "difficulty": args.difficulty, "seed": args.seed, "source": getattr(args, "source", None)})
    session["case_ids"] = session.pop("question_ids")
    session["answers_template"] = {
        question["id"]: "" for case in selected for question in case.get("questions", [])
    }
    session_path = write_session(session)
    payload = {
        "session": session,
        "session_file": str(session_path.relative_to(ROOT)),
        "cases": [public_case(case) for case in selected],
        "next_step": f"Submit answers with: python scripts/study.py case submit --session {session['id']} --answers \"cs_x_q1=A,...\"",
    }
    if args.format == "markdown":
        print(f"Session: {session['id']}")
        print(f"File: {session_path.relative_to(ROOT)}\n")
        for case in selected:
            print(render_case_markdown(case))
        print(payload["next_step"])
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_case_submit_payload(args: argparse.Namespace) -> dict[str, Any]:
    session_path = resolve_session(args.session)
    session = load_json(session_path)
    answers = parse_case_answer_text(args.answers, list(session.get("answers_template", {}).keys()))
    if session.get("type") == "past_exam_case":
        cases_by_id = {case["id"]: case for case in load_past_exam_cases()}
    else:
        cases_by_id = {case["id"]: case for case in load_case_studies()}
    results = []
    auto_score = 0
    max_score = 0
    subjective = []

    for case_id in session.get("case_ids", []):
        case = cases_by_id.get(case_id)
        if not case:
            continue
        case_result = {"case_id": case_id, "title": case.get("title"), "questions": []}
        for question in case.get("questions", []):
            qid = question.get("id")
            answer = answers.get(qid, "")
            expected = str(question.get("answer", ""))
            has_options = bool(question.get("options"))
            score = int(question.get("score", 0) or 0)
            max_score += score
            item = {
                "question_id": qid,
                "user_answer": answer,
                "reference_answer": expected,
                "score": score,
                "explanation": question.get("explanation"),
            }
            if has_options and expected in {"A", "B", "C", "D"}:
                item["is_correct"] = answer == expected
                if item["is_correct"]:
                    auto_score += score
            else:
                grading = grade_subjective_answer(answer, expected, score)
                item.update(grading)
                auto_score += int(item["auto_score"])
                subjective.append(item)
            case_result["questions"].append(item)
        results.append(case_result)

    payload = {
        "session_id": session.get("id"),
        "auto_score": auto_score,
        "max_score": max_score,
        "score_percent": round((auto_score / max_score) * 100, 2) if max_score else 0,
        "subjective_count": len(subjective),
        "results": results,
        "recommendation": "选择题已自动批改；主观题已按参考答案关键词、篇幅和要点覆盖自动估分，建议按 missing_points 二次补答。",
    }
    record = not getattr(args, "no_record", False)
    attempts = list(session.get("case_attempts", []))
    previous = attempts[-1] if attempts else None
    submitted_at = now_iso()
    attempt = {
        "attempt_no": len(attempts) + 1,
        "submitted_at": submitted_at,
        "auto_score": auto_score,
        "max_score": max_score,
        "score_percent": payload["score_percent"],
        "answers": answers,
    }
    if previous:
        attempt["delta_score"] = auto_score - int(previous.get("auto_score", 0))
        attempt["delta_percent"] = round(payload["score_percent"] - float(previous.get("score_percent", 0)), 2)
        payload["improvement"] = {
            "previous_score": previous.get("auto_score"),
            "current_score": auto_score,
            "delta_score": attempt["delta_score"],
            "delta_percent": attempt["delta_percent"],
        }
    if record:
        session.setdefault("case_attempts", []).append(attempt)
        write_session(session)

        progress = load_progress()
        progress.setdefault("case_attempts", []).append(
            {
                "session_id": session.get("id"),
                "submitted_at": submitted_at,
                "attempt_no": attempt["attempt_no"],
                "auto_score": auto_score,
                "max_score": max_score,
                "score_percent": payload["score_percent"],
            }
        )
        progress["last_updated"] = submitted_at
        save_json(ROOT / "assets" / "questions" / "progress.json", progress)
    payload["recorded"] = record
    payload["attempt_no"] = attempt["attempt_no"]
    payload["session_file"] = str(session_path.relative_to(ROOT))
    return payload


def render_case_submit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"Auto score: {payload['auto_score']}/{payload['max_score']}",
        f"Recorded: {payload.get('recorded', True)}",
        f"Attempt: {payload['attempt_no']}",
    ]
    if payload.get("improvement"):
        improvement = payload["improvement"]
        lines.append(f"Improvement: {improvement['delta_score']} 分，{improvement['delta_percent']} 个百分点")
    for case in payload["results"]:
        lines.append(f"\n## {case['title']} [{case['case_id']}]")
        for item in case["questions"]:
            mark = "SUBJECTIVE" if item["is_correct"] is None else ("OK" if item["is_correct"] else "WRONG")
            score_text = f" score={item.get('auto_score', item.get('score', 0) if item.get('is_correct') else 0)}/{item.get('max_score', item.get('score'))}" if item["is_correct"] is None else ""
            lines.append(f"- {mark} {item['question_id']}{score_text}: your {item['user_answer'] or '-'}, reference {item['reference_answer']}")
            if item["is_correct"] is None:
                if item.get("matched_points"):
                    lines.append(f"  Matched: {'、'.join(item['matched_points'])}")
                if item.get("missing_points"):
                    lines.append(f"  Missing: {'、'.join(item['missing_points'])}")
                if item.get("rubric"):
                    lines.append("  Rubric:")
                    for row in item["rubric"]:
                        lines.append(f"    - {row['label']}: {row['score']}/{row['max_score']} ({round(row['ratio'] * 100, 1)}%)")
                lines.append(f"  Feedback: {item.get('feedback')}")
            if item.get("explanation"):
                lines.append(f"  {item['explanation']}")
    lines.append("")
    lines.append(f"Next: {payload['recommendation']}")
    return "\n".join(lines) + "\n"


def command_case_submit(args: argparse.Namespace) -> int:
    payload = build_case_submit_payload(args)
    if args.format == "markdown":
        print(render_case_submit_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def resolve_paper_topic(topic_text: str | None) -> tuple[str, dict[str, Any]] | None:
    topic = (topic_text or "").strip() or DEFAULT_PAPER_TOPIC
    topic = PAPER_TOPIC_ALIASES.get(topic, topic)
    if topic in PAPER_TOPICS:
        return topic, PAPER_TOPICS[topic]
    for alias, canonical in PAPER_TOPIC_ALIASES.items():
        if alias in topic:
            return canonical, PAPER_TOPICS[canonical]
    for canonical, data in PAPER_TOPICS.items():
        if canonical in topic or topic in canonical or data["chapter_title"] in topic:
            return canonical, data
    return None


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


def is_weak_knowledge_point(point: str) -> bool:
    text = str(point or "").strip()
    if len(text) < 3:
        return True
    return any(pattern.match(text) for pattern in WEAK_KNOWLEDGE_POINT_PATTERNS)


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
        if is_weak_knowledge_point(point):
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
    return re.sub(r"\s+", "", text or "")


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


def knowledge_point_index() -> dict[str, dict[str, Any]]:
    questions, _, _ = load_all_questions()
    index: dict[str, dict[str, Any]] = {}
    for question in questions:
        point = str(question.get("knowledge_point") or "").strip()
        if not point:
            continue
        row = index.setdefault(point, {"knowledge_point": point, "question_count": 0, "chapters": Counter(), "sections": Counter()})
        row["question_count"] += 1
        chapter_no = chapter_no_from_label(str(question.get("chapter") or ""))
        if chapter_no is not None:
            row["chapters"][chapter_no] += 1
        section = str(question.get("section") or "").strip()
        if section:
            row["sections"][section] += 1
    return index


def practiced_knowledge_stats() -> dict[str, dict[str, Any]]:
    progress = load_progress()
    stats: dict[str, dict[str, Any]] = {}
    for answer in progress.get("answers", []):
        point = str(answer.get("knowledge_point") or "").strip()
        if not point:
            continue
        row = stats.setdefault(point, {"knowledge_point": point, "answered": 0, "correct": 0, "chapters": Counter()})
        row["answered"] += 1
        if answer.get("is_correct"):
            row["correct"] += 1
        chapter_no = chapter_no_from_label(str(answer.get("chapter") or ""))
        if chapter_no is not None:
            row["chapters"][chapter_no] += 1
    for row in stats.values():
        answered = int(row["answered"])
        row["accuracy"] = round(row["correct"] / answered, 4) if answered else None
    return stats


def chapter_command_for_point(point: str, chapters: Counter[int] | dict[int, int] | None, count: int = 5) -> str:
    chapter_part = ""
    if chapters:
        chapter_no = max(chapters.items(), key=lambda item: item[1])[0]
        chapter_part = f" --chapters {chapter_no}"
    return f"python scripts/study.py start{chapter_part} --knowledge-point {point} --count {count} --format markdown"


def mastery_level(score: float) -> str:
    if score < 20:
        return "未接触"
    if score < 45:
        return "初学"
    if score < 65:
        return "不稳定"
    if score < 85:
        return "已掌握"
    return "精通"


def mastery_action(level: str) -> str:
    return {
        "未接触": "先做基础题建立覆盖",
        "初学": "安排入门题并精读解析",
        "不稳定": "做专项题并复盘错因",
        "已掌握": "降低频率，隔几天抽查",
        "精通": "冲刺前抽查即可",
    }.get(level, "继续练习")


def recency_factor(records: list[dict[str, Any]]) -> float:
    if not records:
        return 0.0
    recent = records[-5:]
    if not recent:
        return 0.0
    hits = sum(1 for record in recent if record.get("is_correct"))
    return hits / len(recent)


def build_mastery_rows() -> list[dict[str, Any]]:
    index = knowledge_point_index()
    progress = load_progress()
    archive = load_archive()
    by_point_records: dict[str, list[dict[str, Any]]] = {}
    wrong_by_point: Counter[str] = Counter()
    _, by_id, _ = load_all_questions()

    for answer in progress.get("answers", []):
        point = str(answer.get("knowledge_point") or "").strip()
        if point:
            by_point_records.setdefault(point, []).append(answer)

    for item in archive.get("archive", []):
        qid = item.get("question_id")
        question = by_id.get(qid)
        point = str((question or {}).get("knowledge_point") or "").strip()
        if point:
            wrong_by_point[point] += int(item.get("wrong_count", item.get("error_count", 1)) or 1)

    rows: list[dict[str, Any]] = []
    for point, meta in index.items():
        records = by_point_records.get(point, [])
        answered = len(records)
        correct = sum(1 for record in records if record.get("is_correct"))
        accuracy = correct / answered if answered else None
        volume_score = min(1.0, answered / 6)
        accuracy_score = accuracy if accuracy is not None else 0.0
        recent_score = recency_factor(records)
        wrong_penalty = min(0.3, wrong_by_point[point] * 0.06)
        score = round(max(0, min(100, (accuracy_score * 0.5 + volume_score * 0.25 + recent_score * 0.25 - wrong_penalty) * 100)), 2)
        if answered == 0:
            score = 0.0
        level = mastery_level(score)
        rows.append(
            {
                "knowledge_point": point,
                "score": score,
                "level": level,
                "answered": answered,
                "correct": correct,
                "accuracy": round(accuracy, 4) if accuracy is not None else None,
                "recent_accuracy": round(recent_score, 4) if answered else None,
                "wrong_attempts": wrong_by_point[point],
                "question_count": meta["question_count"],
                "chapters": meta["chapters"],
                "sections": meta["sections"],
                "action": mastery_action(level),
                "command": chapter_command_for_point(point, meta.get("chapters")),
            }
        )
    rows.sort(key=lambda row: (row["score"], -int(row["question_count"]), row["knowledge_point"]))
    return rows


def build_mastery_payload(args: argparse.Namespace) -> dict[str, Any]:
    rows = build_mastery_rows()
    if getattr(args, "chapter", None):
        chapter = int(args.chapter)
        rows = [row for row in rows if chapter in row.get("chapters", {})]
    levels = Counter(row["level"] for row in rows)
    total = len(rows)
    avg_score = round(sum(float(row["score"]) for row in rows) / total, 2) if total else 0
    weak_levels = {"未接触", "初学", "不稳定"}
    weak_rows = [row for row in rows if row["level"] in weak_levels]
    stable_rows = [row for row in rows if row["level"] in {"已掌握", "精通"}]
    return {
        "total_knowledge_points": total,
        "average_mastery_score": avg_score,
        "counts_by_level": dict(levels),
        "weak_points": weak_rows[: args.limit],
        "stable_points": sorted(stable_rows, key=lambda row: (-float(row["score"]), row["knowledge_point"]))[: args.limit],
        "all_points": rows,
    }


def render_mastery_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 知识点掌握度",
        "",
        f"- 知识点数：{payload['total_knowledge_points']}",
        f"- 平均掌握度：{payload['average_mastery_score']}/100",
        "",
        "## 分布",
    ]
    for level in ("未接触", "初学", "不稳定", "已掌握", "精通"):
        lines.append(f"- {level}: {payload['counts_by_level'].get(level, 0)}")
    lines.append("")
    lines.append("## 优先突破")
    if payload["weak_points"]:
        for row in payload["weak_points"]:
            lines.append(
                f"- {row['knowledge_point']}: {row['score']}/100，{row['level']}，"
                f"answered={row['answered']}，accuracy={round(row['accuracy'] * 100, 2) if row['accuracy'] is not None else '-'}%"
            )
            lines.append(f"  {row['action']}: {row['command']}")
    else:
        lines.append("- 暂无明显薄弱知识点。")
    lines.append("")
    lines.append("## 稳定掌握")
    if payload["stable_points"]:
        for row in payload["stable_points"]:
            lines.append(f"- {row['knowledge_point']}: {row['score']}/100，{row['level']}")
    else:
        lines.append("- 暂无稳定掌握知识点，先扩大练习覆盖。")
    return "\n".join(lines) + "\n"


def command_mastery(args: argparse.Namespace) -> int:
    payload = build_mastery_payload(args)
    if args.format == "markdown":
        print(render_mastery_markdown(payload))
    else:
        print(json.dumps(simplify_json(payload), ensure_ascii=False, indent=2))
    return 0


def build_coverage_payload(args: argparse.Namespace) -> dict[str, Any]:
    index = knowledge_point_index()
    practiced = practiced_knowledge_stats()
    total = len(index)
    practiced_points = set(practiced)
    unpracticed = sorted(set(index) - practiced_points)
    low_accuracy = [
        row for row in practiced.values()
        if int(row.get("answered", 0)) >= args.min_attempts and row.get("accuracy") is not None and float(row["accuracy"]) < args.threshold
    ]
    low_accuracy.sort(key=lambda row: (float(row["accuracy"]), -int(row["answered"]), row["knowledge_point"]))
    priority_unpracticed = sorted(
        (index[point] for point in unpracticed),
        key=lambda row: (-int(row["question_count"]), row["knowledge_point"]),
    )
    suggestions = []
    for row in low_accuracy[: args.limit]:
        suggestions.append(
            {
                "type": "low_accuracy",
                "knowledge_point": row["knowledge_point"],
                "accuracy": row["accuracy"],
                "answered": row["answered"],
                "command": chapter_command_for_point(row["knowledge_point"], row.get("chapters")),
            }
        )
    for row in priority_unpracticed[: max(0, args.limit - len(suggestions))]:
        suggestions.append(
            {
                "type": "unpracticed",
                "knowledge_point": row["knowledge_point"],
                "question_count": row["question_count"],
                "command": chapter_command_for_point(row["knowledge_point"], row.get("chapters")),
            }
        )
    return {
        "total_knowledge_points": total,
        "practiced_knowledge_points": len(practiced_points),
        "unpracticed_knowledge_points": len(unpracticed),
        "coverage_percent": round((len(practiced_points) / total) * 100, 2) if total else 0,
        "low_accuracy_threshold": args.threshold,
        "low_accuracy_points": low_accuracy[: args.limit],
        "top_unpracticed_points": priority_unpracticed[: args.limit],
        "suggestions": suggestions,
    }


def render_coverage_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 知识点覆盖率报告",
        "",
        f"- 知识点总数：{payload['total_knowledge_points']}",
        f"- 已练知识点：{payload['practiced_knowledge_points']}",
        f"- 未练知识点：{payload['unpracticed_knowledge_points']}",
        f"- 覆盖率：{payload['coverage_percent']}%",
        "",
    ]
    if payload["low_accuracy_points"]:
        lines.append("## 低正确率知识点")
        for row in payload["low_accuracy_points"]:
            lines.append(f"- {row['knowledge_point']}: accuracy={round(row['accuracy'] * 100, 2)}%, answered={row['answered']}")
        lines.append("")
    else:
        lines.append("## 低正确率知识点")
        lines.append("- 暂无低正确率知识点；如果进度为空，请先完成章节练习。")
        lines.append("")
    lines.append("## 优先补练知识点")
    if payload["top_unpracticed_points"]:
        for row in payload["top_unpracticed_points"]:
            chapters = ",".join(str(chapter) for chapter, _ in row["chapters"].most_common(3))
            lines.append(f"- {row['knowledge_point']}: questions={row['question_count']}, chapters={chapters}")
    else:
        lines.append("- 所有已索引知识点至少练过一次。")
    lines.append("")
    lines.append("## 建议命令")
    if payload["suggestions"]:
        for item in payload["suggestions"]:
            lines.append(f"- [{item['type']}] {item['knowledge_point']}: {item['command']}")
    else:
        lines.append("- python scripts/study.py plan --format markdown")
    return "\n".join(lines) + "\n"


def command_coverage(args: argparse.Namespace) -> int:
    payload = build_coverage_payload(args)
    if args.format == "markdown":
        print(render_coverage_markdown(payload))
    else:
        print(json.dumps(simplify_json(payload), ensure_ascii=False, indent=2))
    return 0


def option_body(option: Any) -> str:
    text = str(option or "").strip()
    return re.sub(r"^[A-Da-d][\.\、:：\)]\s*", "", text).strip()


def add_audit_issue(issues: list[dict[str, Any]], severity: str, code: str, message: str, question: dict[str, Any] | None = None, detail: Any | None = None) -> None:
    issue = {"severity": severity, "code": code, "message": message}
    if question:
        issue["question_id"] = question.get("id")
        issue["chapter"] = question.get("chapter")
    if detail is not None:
        issue["detail"] = detail
    issues.append(issue)


def audit_questions_payload(questions: list[dict[str, Any]], limit: int, min_explanation_length: int) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    required = ["id", "chapter", "question", "options", "answer", "explanation", "difficulty", "section", "knowledge_point", "source_ref", "tags"]
    answer_distribution = Counter(str(question.get("answer") or "") for question in questions)
    difficulty_distribution = Counter(str(question.get("difficulty") or "") for question in questions)
    knowledge_distribution = Counter(str(question.get("knowledge_point") or "").strip() for question in questions if str(question.get("knowledge_point") or "").strip())
    question_texts = Counter(str(question.get("question") or "").strip() for question in questions)
    suspicious_terms = ["军事", "军事化", "军队", "作战", "军事基地", "军事训练", "军事政策", "军事服务", "军事生产", "军事安全", "军事技术"]

    total = len(questions)
    if total:
        answer, count = answer_distribution.most_common(1)[0]
        ratio = count / total
        if ratio >= 0.45:
            add_audit_issue(issues, "high", "answer_skew", f"答案 {answer} 占比 {round(ratio * 100, 2)}%，分布明显偏斜。", detail=dict(answer_distribution))
        hard_ratio = difficulty_distribution.get("hard", 0) / total
        easy_ratio = difficulty_distribution.get("easy", 0) / total
        if hard_ratio < 0.05:
            add_audit_issue(issues, "medium", "difficulty_imbalance", f"hard 难度占比仅 {round(hard_ratio * 100, 2)}%，高难题偏少。", detail=dict(difficulty_distribution))
        if easy_ratio > 0.45:
            add_audit_issue(issues, "medium", "difficulty_imbalance", f"easy 难度占比 {round(easy_ratio * 100, 2)}%，题库可能偏基础。", detail=dict(difficulty_distribution))

    for question in questions:
        missing = [field for field in required if field not in question or question.get(field) in (None, "", [])]
        if missing:
            add_audit_issue(issues, "high", "missing_field", "题目缺少必要字段。", question, missing)
        answer = str(question.get("answer") or "").strip()
        if answer not in {"A", "B", "C", "D"}:
            add_audit_issue(issues, "high", "invalid_answer", "答案不在 A/B/C/D 范围。", question, answer)
        options = question.get("options") or []
        option_bodies = [option_body(option) for option in options]
        if len(options) != 4:
            add_audit_issue(issues, "high", "option_count", "选择题选项数量不是4个。", question, len(options))
        duplicates = [body for body, count in Counter(option_bodies).items() if body and count > 1]
        if duplicates:
            add_audit_issue(issues, "medium", "duplicate_options", "存在重复或近似重复选项。", question, duplicates)
        explanation = str(question.get("explanation") or "").strip()
        if len(explanation) < min_explanation_length:
            add_audit_issue(issues, "medium", "short_explanation", "解析过短，难以支撑学习闭环。", question, f"{len(explanation)} chars")
        point = str(question.get("knowledge_point") or "").strip()
        if is_weak_knowledge_point(point):
            add_audit_issue(issues, "medium", "weak_knowledge_point", "knowledge_point 过短、过泛或像截断短语。", question, point)
        source_ref = str(question.get("source_ref") or "").strip()
        if source_ref and not source_ref.startswith("references/"):
            add_audit_issue(issues, "low", "weak_source_ref", "source_ref 不是 references/ 路径。", question, source_ref)
        text_bundle = " ".join([str(question.get("question") or ""), explanation, " ".join(str(option) for option in options)])
        matched_terms = sorted({term for term in suspicious_terms if term in text_bundle})
        if matched_terms:
            add_audit_issue(issues, "medium", "artificial_distractor", "出现明显模板化或与考试场景弱相关的干扰项词汇。", question, matched_terms)

    for text, count in question_texts.items():
        if text and count > 1:
            add_audit_issue(issues, "medium", "duplicate_question_text", f"存在完全相同题干，重复 {count} 次。", detail=text[:80])

    if total:
        for point, count in knowledge_distribution.most_common(10):
            if count / total >= 0.08:
                add_audit_issue(issues, "low", "overused_knowledge_point", f"知识点“{point}”出现 {count} 次，可能过泛。", detail={"knowledge_point": point, "count": count})

    severity_order = {"high": 0, "medium": 1, "low": 2}
    issues.sort(key=lambda item: (severity_order.get(item["severity"], 9), item["code"], item.get("question_id", "")))
    counts_by_code = Counter(issue["code"] for issue in issues)
    counts_by_severity = Counter(issue["severity"] for issue in issues)
    return {
        "total_questions": total,
        "answer_distribution": dict(answer_distribution),
        "difficulty_distribution": dict(difficulty_distribution),
        "issue_count": len(issues),
        "counts_by_severity": dict(counts_by_severity),
        "counts_by_code": dict(counts_by_code),
        "issues": issues[: limit],
        "truncated": len(issues) > limit,
    }


def build_audit_payload(args: argparse.Namespace) -> dict[str, Any]:
    questions, _, _ = load_all_questions()
    return audit_questions_payload(questions, args.limit, args.min_explanation_length)


def render_audit_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 题库质量审计",
        "",
        f"- 题目总数：{payload['total_questions']}",
        f"- 问题数量：{payload['issue_count']}",
        f"- 答案分布：{payload['answer_distribution']}",
        f"- 难度分布：{payload['difficulty_distribution']}",
        "",
        "## 问题汇总",
    ]
    if payload["counts_by_code"]:
        for code, count in sorted(payload["counts_by_code"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {code}: {count}")
    else:
        lines.append("- 暂未发现问题。")
    lines.append("")
    lines.append("## 示例")
    if payload["issues"]:
        for issue in payload["issues"]:
            location = f" {issue.get('question_id')}" if issue.get("question_id") else ""
            detail = f" detail={issue['detail']}" if "detail" in issue else ""
            lines.append(f"- [{issue['severity']}] {issue['code']}{location}: {issue['message']}{detail}")
        if payload.get("truncated"):
            lines.append("- 输出已截断；可增加 --limit 查看更多示例。")
    else:
        lines.append("- 暂无示例。")
    return "\n".join(lines) + "\n"


def command_audit(args: argparse.Namespace) -> int:
    payload = build_audit_payload(args)
    if args.format == "markdown":
        print(render_audit_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def chapter_path_from_question(question: dict[str, Any]) -> Path | None:
    chapter_no = chapter_no_from_label(str(question.get("chapter") or ""))
    if chapter_no is None:
        return None
    return CHAPTERS_DIR / f"chapter_{chapter_no:02d}.json"


def inferred_knowledge_point(question: dict[str, Any]) -> str:
    qid = str(question.get("id") or "")
    if qid in STRONG_KNOWLEDGE_POINT_OVERRIDES:
        return STRONG_KNOWLEDGE_POINT_OVERRIDES[qid]
    section = str(question.get("section") or "").strip()
    tags = [str(tag).strip() for tag in question.get("tags", []) if str(tag).strip()]
    for tag in tags:
        if not is_weak_knowledge_point(tag) and tag != section:
            return tag
    if section and not is_weak_knowledge_point(section):
        return section
    chapter_no = chapter_no_from_label(str(question.get("chapter") or ""))
    if chapter_no:
        for data in PAPER_TOPICS.values():
            if data["chapter"] == chapter_no:
                return data["chapter_title"]
    return section or str(question.get("chapter") or "通用知识点")


def replace_suspicious_terms(text: str) -> str:
    fixed = str(text)
    for bad, replacement in SUSPICIOUS_DISTRACTOR_REPLACEMENTS.items():
        fixed = fixed.replace(bad, replacement)
    return fixed


def apply_quality_fix(question: dict[str, Any], min_explanation_length: int, fix_options: bool = False) -> list[dict[str, Any]]:
    changes = []
    if fix_options:
        for field in ("question", "explanation"):
            original = str(question.get(field) or "")
            fixed = replace_suspicious_terms(original)
            if fixed != original:
                question[field] = fixed
                changes.append({"field": field, "reason": "replace_template_distractor"})
        original_options = list(question.get("options") or [])
        fixed_options = [replace_suspicious_terms(str(option)) for option in original_options]
        if fixed_options != original_options:
            question["options"] = fixed_options
            changes.append({"field": "options", "reason": "replace_template_distractor"})

    point = str(question.get("knowledge_point") or "").strip()
    if is_weak_knowledge_point(point) or point in STOP_KNOWLEDGE_POINTS:
        new_point = inferred_knowledge_point(question)
        if new_point and new_point != point:
            question["knowledge_point"] = new_point
            tags = list(question.get("tags") or [])
            if new_point not in tags:
                tags.insert(0, new_point)
                question["tags"] = tags[:5]
            changes.append({"field": "knowledge_point", "reason": "replace_weak_metadata", "from": point, "to": new_point})

    explanation = str(question.get("explanation") or "").strip()
    if len(explanation) < min_explanation_length:
        answer = str(question.get("answer") or "").strip()
        section = str(question.get("section") or question.get("knowledge_point") or "").strip()
        supplement = f"本题考查{section}。正确答案为{answer}，可结合教材对应小节理解概念边界和适用场景。"
        if explanation:
            question["explanation"] = f"{explanation} {supplement}"
        else:
            question["explanation"] = supplement
        changes.append({"field": "explanation", "reason": "expand_short_explanation"})

    return changes


def option_letter(index: int) -> str:
    return "ABCD"[index]


def option_text_without_letter(option: Any) -> str:
    return re.sub(r"^[A-Da-d][\.\、:：\)]\s*", "", str(option or "")).strip()


def format_option(letter: str, body: str) -> str:
    return f"{letter}. {body}"


def rebalance_answer_distribution(questions: list[dict[str, Any]], target_max_ratio: float = 0.44) -> list[dict[str, Any]]:
    changes = []
    total = len(questions)
    if not total:
        return changes
    distribution = Counter(str(question.get("answer") or "") for question in questions)
    target_max = int(total * target_max_ratio)
    target_letters = ("A", "B", "C", "D")
    for source_letter, source_count in distribution.most_common():
        while source_count > target_max:
            target_letter = min(target_letters, key=lambda letter: distribution.get(letter, 0))
            if distribution[target_letter] >= target_max or target_letter == source_letter:
                break
            question = next(
                (
                    item for item in questions
                    if str(item.get("answer") or "") == source_letter
                    and len(item.get("options") or []) == 4
                    and item.get("question_type", "single_choice") in {"single_choice", "choice"}
                ),
                None,
            )
            if not question:
                break
            options = list(question.get("options") or [])
            source_index = target_letters.index(source_letter)
            target_index = target_letters.index(target_letter)
            bodies = [option_text_without_letter(option) for option in options]
            bodies[source_index], bodies[target_index] = bodies[target_index], bodies[source_index]
            question["options"] = [format_option(letter, body) for letter, body in zip(target_letters, bodies)]
            question["answer"] = target_letter
            changes.append({"question_id": question.get("id"), "field": "answer/options", "reason": "rebalance_answer_distribution", "from": source_letter, "to": target_letter})
            distribution[source_letter] -= 1
            distribution[target_letter] += 1
            source_count = distribution[source_letter]
    return changes


def hard_question_score(question: dict[str, Any]) -> int:
    text = f"{question.get('question', '')} {question.get('explanation', '')}"
    score = 0
    score += 2 if any(term in text for term in ("不正确", "不包括", "不属于", "最恰当", "主要原因", "核心要求")) else 0
    score += 2 if any(term in text for term in ("案例", "场景", "分析", "规划", "治理", "架构", "成熟度", "连续性")) else 0
    score += 1 if len(normalize_text(text)) >= 120 else 0
    return score


def rebalance_difficulty(questions: list[dict[str, Any]], min_hard_ratio: float = 0.06) -> list[dict[str, Any]]:
    total = len(questions)
    target_hard = max(1, int(total * min_hard_ratio))
    current_hard = sum(1 for question in questions if question.get("difficulty") == "hard")
    needed = max(0, target_hard - current_hard)
    if needed == 0:
        return []
    candidates = [
        question for question in questions
        if question.get("difficulty") == "medium" and hard_question_score(question) >= 3
    ]
    candidates.sort(key=lambda question: (-hard_question_score(question), str(question.get("id") or "")))
    changes = []
    for question in candidates[:needed]:
        question["difficulty"] = "hard"
        tags = list(question.get("tags") or [])
        if "hard" not in tags:
            tags.append("hard")
            question["tags"] = tags[:5]
        changes.append({"question_id": question.get("id"), "field": "difficulty", "reason": "promote_high_cognitive_load", "to": "hard"})
    return changes


def build_quality_fix_payload(args: argparse.Namespace) -> dict[str, Any]:
    files = sorted(CHAPTERS_DIR.glob("chapter_*.json"))
    changed_files: dict[str, list[dict[str, Any]]] = {}
    loaded_files: dict[Path, list[dict[str, Any]]] = {}
    all_questions_after_fix: list[dict[str, Any]] = []
    total_changes = 0
    touched_questions = 0
    for path in files:
        data = load_json(path)
        if not isinstance(data, list):
            continue
        loaded_files[path] = data
        file_changes = []
        for question in data:
            if not isinstance(question, dict):
                continue
            changes = apply_quality_fix(question, args.min_explanation_length, fix_options=args.fix_options)
            all_questions_after_fix.append(question)
            if changes:
                touched_questions += 1
                total_changes += len(changes)
                file_changes.append({"question_id": question.get("id"), "changes": changes})
        if file_changes:
            rel = str(path.relative_to(ROOT))
            changed_files[rel] = file_changes
            if args.write:
                save_json(path, data)
    all_questions_after_fix = [question for data in loaded_files.values() for question in data if isinstance(question, dict)]
    if args.rebalance_answers:
        answer_changes = rebalance_answer_distribution(all_questions_after_fix, target_max_ratio=args.answer_max_ratio)
        if answer_changes:
            by_id = {str(question.get("id")): question for question in all_questions_after_fix}
            for change in answer_changes:
                question = by_id.get(str(change.get("question_id")))
                if not question:
                    continue
                path = chapter_path_from_question(question)
                if not path:
                    continue
                rel = str(path.relative_to(ROOT))
                changed_files.setdefault(rel, []).append({"question_id": question.get("id"), "changes": [change]})
            touched_questions += len(answer_changes)
            total_changes += len(answer_changes)
    if args.rebalance_difficulty:
        difficulty_changes = rebalance_difficulty(all_questions_after_fix, min_hard_ratio=args.min_hard_ratio)
        if difficulty_changes:
            by_id = {str(question.get("id")): question for question in all_questions_after_fix}
            for change in difficulty_changes:
                question = by_id.get(str(change.get("question_id")))
                if not question:
                    continue
                path = chapter_path_from_question(question)
                if not path:
                    continue
                rel = str(path.relative_to(ROOT))
                changed_files.setdefault(rel, []).append({"question_id": question.get("id"), "changes": [change]})
            touched_questions += len(difficulty_changes)
            total_changes += len(difficulty_changes)
    if args.write:
        for path, data in loaded_files.items():
            save_json(path, data)
    remaining = audit_questions_payload(all_questions_after_fix, args.audit_limit, args.min_explanation_length)
    payload = {
        "mode": "write" if args.write else "dry_run",
        "changed_files": changed_files,
        "changed_file_count": len(changed_files),
        "touched_questions": touched_questions,
        "total_changes": total_changes,
        "remaining_issue_count": remaining["issue_count"],
        "remaining_counts_by_code": remaining["counts_by_code"],
        "remaining_issues": remaining["issues"],
        "note": "默认自动修复弱 knowledge_point 和过短解析；--fix-options 替换题干/选项/解析中的明显模板化干扰词；--rebalance-answers 只重排选项不改变知识含义；--rebalance-difficulty 按题干复杂度提升部分 hard。",
    }
    return payload


def render_quality_fix_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 题库质量修复",
        "",
        f"- 模式：{payload['mode']}",
        f"- 涉及文件：{payload['changed_file_count']}",
        f"- 涉及题目：{payload['touched_questions']}",
        f"- 修复项：{payload['total_changes']}",
        f"- 剩余问题：{payload['remaining_issue_count']}",
        f"- 说明：{payload['note']}",
        "",
        "## 剩余问题分布",
    ]
    if payload["remaining_counts_by_code"]:
        for code, count in sorted(payload["remaining_counts_by_code"].items(), key=lambda item: (-item[1], item[0])):
            lines.append(f"- {code}: {count}")
    else:
        lines.append("- 暂无剩余问题。")
    if payload.get("remaining_issues"):
        lines.append("")
        lines.append("## 剩余问题示例")
        for issue in payload["remaining_issues"][:10]:
            location = f" {issue.get('question_id')}" if issue.get("question_id") else ""
            detail = f" detail={issue['detail']}" if "detail" in issue else ""
            lines.append(f"- [{issue['severity']}] {issue['code']}{location}: {issue['message']}{detail}")
    lines.append("")
    lines.append("## 修复示例")
    examples = []
    for rel, items in payload["changed_files"].items():
        for item in items:
            examples.append((rel, item))
            if len(examples) >= 10:
                break
        if len(examples) >= 10:
            break
    if examples:
        for rel, item in examples:
            reasons = ", ".join(change["reason"] for change in item["changes"])
            lines.append(f"- {rel} {item['question_id']}: {reasons}")
    else:
        lines.append("- 没有可自动修复项。")
    if payload["mode"] == "dry_run":
        lines.append("")
        lines.append("Next: 确认后执行 python scripts/study.py fix-quality --write --format markdown")
    return "\n".join(lines) + "\n"


def command_fix_quality(args: argparse.Namespace) -> int:
    payload = build_quality_fix_payload(args)
    if args.format == "markdown":
        print(render_quality_fix_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_dashboard_payload(args: argparse.Namespace) -> dict[str, Any]:
    profile = load_learner_profile()
    profile_info = profile_summary(profile)
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
    for chapter in profile_weak_chapters(profile)[:2]:
        guide_row = chapter_guide_row(chapter)
        title = f"画像薄弱章节：第{chapter}章" + (f" {guide_row['title']}" if guide_row else "")
        add_task({"priority": 2.2, "type": "profile_weak_chapter", "title": title, "command": f"python scripts/study.py start --chapters {chapter} --count {practice_count} --format markdown"})
    if profile_has_weak_subject(profile, "案例", "主观题"):
        add_task({"priority": 3, "type": "profile_case", "title": "案例分析采分点训练", "command": f"python scripts/study.py case start --chapters {case_chapters} --count {profile_case_count(profile)} --format markdown"})
    if profile_has_weak_subject(profile, "论文", "作文"):
        add_task({"priority": 3.5, "type": "profile_paper", "title": "论文框架训练", "command": f"python scripts/study.py paper --topic {DEFAULT_PAPER_TOPIC} --format markdown"})
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
        lines.append(f"- 查看画像：python scripts/study.py profile --format markdown")
        lines.append("")
    lines.append("## 掌握度分布")
    for level in ("未接触", "初学", "不稳定", "已掌握", "精通"):
        lines.append(f"- {level}: {payload['mastery_counts_by_level'].get(level, 0)}")
    lines.append("")
    lines.append("## 今日建议")
    for index, task in enumerate(payload["tasks"], start=1):
        lines.append(f"{index}. {task['title']}")
        lines.append(f"   {task['command']}")
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


def render_exam_guide_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 考试导航与大纲分析",
        "",
    ]
    if payload.get("note"):
        lines.append(f"> {payload['note']}")
        lines.append("")
    schedule = payload.get("exam_schedule", {})
    if schedule:
        lines.extend(
            [
                "## 考试安排",
                f"- 资格：{schedule.get('qualification', '系统规划与管理师')}（{schedule.get('level', '高级')}）",
                f"- 预测考试时间：{schedule.get('predicted_2025_h2_dates', '-')}",
                f"- 合格线参考：{schedule.get('full_score', 75)} 分满分，{schedule.get('pass_score', 45)} 分及格",
            ]
        )
        for subject in payload.get("subjects", []):
            lines.append(f"- {subject['name']}：{subject['content']}，{subject['duration_minutes']} 分钟，{subject['time_window']}")
        lines.append("")
    ranges = payload.get("subject_ranges", {})
    if ranges:
        lines.extend(
            [
                "## 大纲范围",
                f"- 综合知识：第{ranges.get('comprehensive', {}).get('chapters', '1-24')}章",
                f"- 案例分析：第{ranges.get('case_analysis', {}).get('chapters', '4-24')}章",
                f"- 论文：第{ranges.get('paper', {}).get('chapters', '4-17')}章",
                "",
            ]
        )
    lines.append("## 高优先级章节")
    for row in payload.get("top_chapters", []):
        lines.append(f"- 第{row['chapter']}章 {row['title']}：重要度 {row['importance']}，{row.get('advice', '')}")
    lines.extend(
        [
            "",
            "## 资料位置",
            f"- 学习指南：{payload['paths']['guide']}",
            f"- 大纲分析：{payload['paths']['syllabus']}",
        ]
    )
    return "\n".join(lines) + "\n"


def command_exam_guide(args: argparse.Namespace) -> int:
    payload = build_exam_guide_payload(args)
    if args.format == "markdown":
        print(render_exam_guide_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


INTERNAL_KIND_CONFIG = {
    "notes": {
        "label": "三色笔记",
        "index": INTERNAL_DIR / "three-color-notes" / "index.json",
        "description": "高频知识点补充和背诵清单",
    },
    "mindmap": {
        "label": "思维导图",
        "index": INTERNAL_DIR / "mindmaps" / "index.json",
        "description": "章节速览和知识结构导航",
    },
}


def build_internal_material_payload(args: argparse.Namespace) -> dict[str, Any]:
    kind = args.kind
    config = INTERNAL_KIND_CONFIG[kind]
    index = load_internal_json(config["index"], {"items": []})
    items = index.get("items", []) if isinstance(index, dict) else []
    if args.chapter:
        items = [item for item in items if int(item.get("chapter", 0) or 0) == int(args.chapter)]
    rows = []
    for item in items:
        md_path = ROOT / item["markdown"] if item.get("markdown") else None
        preview: list[str] = []
        if md_path and md_path.exists():
            text_lines = [
                line.strip()
                for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                if line.strip() and not line.startswith(">") and not line.startswith("#")
            ]
            preview = text_lines[: args.preview_lines]
        rows.append({**item, "preview": preview})
    return {
        "kind": kind,
        "label": config["label"],
        "description": config["description"],
        "index_file": str(config["index"].relative_to(ROOT)),
        "count": len(rows),
        "items": rows,
    }


def render_internal_material_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload['label']}",
        "",
        f"- 用途：{payload['description']}",
        f"- 索引：{payload['index_file']}",
        f"- 命中：{payload['count']}",
        "",
    ]
    for item in payload["items"]:
        lines.append(f"## 第{item['chapter']}章 {item['chapter_title']}")
        lines.append(f"- 抽取文本：{item.get('markdown') or '-'}")
        if item.get("asset"):
            lines.append(f"- 原始资源：{item['asset']}")
        lines.append(f"- 原始资料：{item.get('source')}")
        preview = item.get("preview") or []
        if preview:
            lines.append("- 预览：")
            lines.extend(f"  - {line}" for line in preview)
        lines.append("")
    return "\n".join(lines)


def command_internal_material(args: argparse.Namespace) -> int:
    payload = build_internal_material_payload(args)
    if args.format == "markdown":
        print(render_internal_material_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def render_vip_material_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# VIP材料",
        "",
        f"- 来源目录：{payload.get('base_path')}",
        f"- 索引：{payload['index_file']}",
        f"- 筛选：{payload.get('kind') or 'all'} {payload.get('keyword') or ''}".rstrip(),
        f"- 总文件：{payload['total_files']}，已抽取：{payload['extracted_count']}，命中：{payload['matched_count']}",
        f"- 总大小：{payload['total_size_mb']} MB",
        "",
    ]
    if not payload.get("files"):
        lines.append("没有匹配到 VIP 材料。")
        return "\n".join(lines) + "\n"
    for item in payload["files"]:
        lines.append(f"## {item.get('kind_label')}：{item.get('title')}")
        lines.append(f"- 原始文件：{item.get('relative_path')}")
        lines.append(f"- 页数：{item.get('page_count') or '-'}；文本量：{item.get('text_chars', 0)}；策略：{item.get('strategy')}")
        lines.append(f"- 抽取文本：{item.get('markdown') or '仅索引'}")
        if item.get("description"):
            lines.append(f"- 用途：{item['description']}")
        preview = item.get("preview") or []
        if preview:
            lines.append("- 预览：")
            lines.extend(f"  - {line}" for line in preview)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_vip_material(args: argparse.Namespace) -> int:
    payload = build_vip_material_payload(args)
    if args.format == "markdown":
        print(render_vip_material_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def render_sprint_material_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 冲刺资料",
        "",
        f"- 来源目录：{payload.get('base_path')}",
        f"- 索引：{payload['index_file']}",
        f"- 筛选：{payload.get('kind') or 'all'} {payload.get('keyword') or ''}".rstrip(),
        f"- 总文件：{payload['total_files']}，存在：{payload.get('existing_count', 0)}，已抽取：{payload['extracted_count']}，需OCR：{payload.get('needs_ocr_count', 0)}，命中：{payload['matched_count']}",
        f"- 总大小：{payload['total_size_mb']} MB",
        "> 说明：冲刺资料、押题资料和模拟题是补充资料源，不等同历年真题；扫描件需 OCR 后才适合进一步结构化。",
        "",
    ]
    if not payload.get("files"):
        lines.append("没有匹配到冲刺资料。")
        return "\n".join(lines) + "\n"
    for item in payload["files"]:
        lines.append(f"## {item.get('kind_label')}：{item.get('title')}")
        lines.append(f"- 原始文件：{item.get('relative_path')}")
        lines.append(
            f"- 页数：{item.get('page_count') or '-'}；文本量：{item.get('text_chars', 0)}；"
            f"需OCR：{'是' if item.get('needs_ocr') else '否'}；策略：{item.get('strategy')}"
        )
        lines.append(f"- 抽取文本：{item.get('markdown') or '仅索引'}")
        if item.get("sha1_prefix"):
            lines.append(f"- SHA1：{item.get('sha1_prefix')}")
        if item.get("description"):
            lines.append(f"- 用途：{item['description']}")
        preview = item.get("preview") or []
        if preview:
            lines.append("- 预览：")
            lines.extend(f"  - {line}" for line in preview)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_sprint_material(args: argparse.Namespace) -> int:
    payload = build_sprint_material_payload(args)
    if args.format == "markdown":
        print(render_sprint_material_markdown(payload))
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
    session_file = "<no-write>"
    if write:
        session_path = write_session(session)
        session_file = str(session_path.relative_to(ROOT))
    return {
        "title": "冲刺模拟候选题训练",
        "session": session,
        "session_file": session_file,
        "kind": getattr(args, "kind", "all"),
        "keyword": getattr(args, "keyword", None),
        "available": len(rows),
        "questions": [public_sprint_training_question(question) for question in selected],
        "next_step": f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown",
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


def render_candidate_practice_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 章节习题候选题源",
        "",
        f"> {payload['note']}",
        "",
        f"- 来源：{payload['source']}",
        f"- 章节：{payload['chapter'] if payload['chapter'] else '全部'}",
        f"- 可用候选题：{payload['total_available']}",
        f"- 索引：{payload['index_file']}",
    ]
    report = payload.get("quality_report") or {}
    if report:
        lines.append(f"- 总候选题：{report.get('total')}")
        lines.append(f"- 答案分布：{report.get('answer_distribution')}")
        lines.append(f"- 质量问题：{report.get('issue_counts') or '暂无'}")
    lines.append("")
    for index, question in enumerate(payload["questions"], start=1):
        lines.append(f"{index}. [{question['id']}] {question['question']}")
        for option in question.get("options", []):
            lines.append(f"   {option}")
        lines.append(f"   Answer: {question.get('answer')}")
        lines.append(f"   Explanation: {question.get('explanation')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_candidate_practice(args: argparse.Namespace) -> int:
    payload = build_candidate_practice_payload(args)
    if args.format == "markdown":
        print(render_candidate_practice_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def render_recitation_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 案例背诵训练",
        "",
        f"> {payload['note']}",
        "",
        f"- 来源：{payload['source']}",
        f"- 章节：{payload['chapter'] if payload['chapter'] else '全部'}",
        f"- 可用候选题：{payload['total_available']}",
        f"- 索引：{payload['index_file']}",
    ]
    report = payload.get("quality_report") or {}
    if report:
        lines.append(f"- 总候选题：{report.get('total')}")
        lines.append(f"- 质量问题：{report.get('issue_counts') or '暂无'}")
    lines.append("")
    for index, item in enumerate(payload["items"], start=1):
        lines.append(f"{index}. [{item['id']}] {item['question']}")
        if payload.get("show_answer"):
            lines.append("   参考答案/采分点：")
            for line in str(item.get("answer", "")).splitlines():
                lines.append(f"   - {line}")
        else:
            lines.append("   参考答案：隐藏；加 `--show-answer` 查看采分点。")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def command_recitation(args: argparse.Namespace) -> int:
    payload = build_recitation_payload(args)
    if args.format == "markdown":
        print(render_recitation_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def render_backup_pdf_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# F盘备份PDF：{payload['category_label']}",
        "",
        f"- 来源目录：`{payload.get('base_path')}`",
        f"- 索引：`{payload['index_file']}`",
        f"- 总 PDF：{payload['total_files']}，已抽取：{payload['extracted_count']}，需 OCR：{payload['needs_ocr_count']}，总大小：{payload['total_size_mb']} MB",
        f"- 当前匹配：{payload['matched_count']}",
        "",
        "## 文件",
    ]
    if not payload["files"]:
        lines.append("- 暂无匹配文件。")
    for item in payload["files"]:
        year = item.get("year") or "-"
        period = item.get("period") or ""
        subject = item.get("subject") or "-"
        status = "需OCR" if item.get("needs_ocr") else f"{item.get('text_chars', 0)}字"
        markdown = item.get("markdown") or "-"
        lines.append(f"- {item.get('title')} | {year}{period} | {subject} | {status}")
        lines.append(f"  `{markdown}`")
    return "\n".join(lines) + "\n"


def command_backup_pdfs(args: argparse.Namespace) -> int:
    payload = build_backup_pdf_payload(args)
    if args.format == "markdown":
        print(render_backup_pdf_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_continue_payload(args: argparse.Namespace) -> dict[str, Any]:
    record = latest_session(kind=getattr(args, "type", None), open_only=not args.any)
    if record is None and not args.any:
        record = latest_session(kind=getattr(args, "type", None), open_only=False)
    if record is None:
        next_step = "python scripts/study.py start --chapters 12 --count 5 --format markdown"
        if getattr(args, "type", None) == "standards_training":
            next_step = "python scripts/study.py standards start --count 5 --format markdown"
        elif getattr(args, "type", None) == "past_exam":
            next_step = "python scripts/study.py past-exam start --count 5 --format markdown"
        elif getattr(args, "type", None) == "past_exam_case":
            next_step = "python scripts/study.py past-exam case --count 1 --format markdown"
        elif getattr(args, "type", None) == "case_study":
            next_step = f"python scripts/study.py case start --chapters {case_range_chapters_text()} --count 1 --format markdown"
        return {
            "message": "没有找到历史 session，建议先开始一次练习。",
            "next_step": next_step,
        }

    session = record["session"]
    path = record["path"]
    payload = {
        "session": session,
        "session_file": str(path.relative_to(ROOT)),
        "completed": is_session_completed(session),
        "type": session.get("type"),
        "created_at": session.get("created_at"),
    }
    if session.get("type") in {"case_study", "past_exam_case"}:
        source_cases = load_past_exam_cases() if session.get("type") == "past_exam_case" else load_case_studies()
        cases_by_id = {case["id"]: case for case in source_cases}
        cases = [public_case(cases_by_id[case_id]) for case_id in session.get("case_ids", []) if case_id in cases_by_id]
        payload["cases"] = cases
        payload["next_step"] = f"python scripts/study.py case submit --session {session['id']} --answers \"...\" --format markdown"
    else:
        _, by_id, _ = load_all_questions()
        if session.get("type") == "past_exam":
            by_id = {**by_id, **past_exam_choice_lookup()}
        if session.get("type") == "standards_training":
            by_id = {**by_id, **standards_question_lookup()}
        if session.get("type") == "past_exam":
            questions = [public_past_exam_question(by_id[qid]) for qid in session.get("question_ids", []) if qid in by_id]
        elif session.get("type") == "standards_training":
            questions = [public_standard_question(by_id[qid]) for qid in session.get("question_ids", []) if qid in by_id]
        else:
            questions = [public_question(by_id[qid]) for qid in session.get("question_ids", []) if qid in by_id]
        payload["questions"] = questions
        payload["next_step"] = f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown"
    return payload


def render_continue_markdown(payload: dict[str, Any]) -> str:
    if payload.get("message"):
        return f"{payload['message']}\nNext: {payload['next_step']}\n"
    lines = [
        "# 继续学习",
        "",
        f"- Session: {payload['session']['id']}",
        f"- File: {payload['session_file']}",
        f"- 类型：{payload['type']}",
        f"- 状态：{'已提交/已完成' if payload['completed'] else '未完成'}",
        "",
    ]
    if payload.get("questions"):
        lines.append(render_questions_markdown(payload["questions"]).rstrip())
    if payload.get("cases"):
        for case in payload["cases"]:
            lines.append(render_case_markdown(case).rstrip())
            lines.append("")
    lines.append(f"Next: {payload['next_step']}")
    return "\n".join(lines).rstrip() + "\n"


def command_continue(args: argparse.Namespace) -> int:
    payload = build_continue_payload(args)
    if args.format == "markdown":
        print(render_continue_markdown(payload))
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
            lines.append(f"  建议：{item['command']}")
    else:
        lines.append("- 先完成一次练习并提交答案。")
    lines.append("")
    lines.append(f"Next: {payload['next_step']}")
    return "\n".join(lines) + "\n"


def command_root_cause(args: argparse.Namespace) -> int:
    payload = build_root_cause_payload(args)
    if args.format == "markdown":
        print(render_root_cause_markdown(payload))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_drill_payload(args: argparse.Namespace) -> dict[str, Any]:
    mastery = build_mastery_payload(argparse.Namespace(limit=max(args.count * 3, 10), chapter=args.chapter))
    target_points = [row for row in mastery["weak_points"] if row["level"] in {"初学", "不稳定"}]
    if len(target_points) < args.count:
        target_points.extend(row for row in mastery["weak_points"] if row not in target_points)
    _, _, by_chapter = load_all_questions()
    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for row in target_points:
        chapter_numbers = list(row.get("chapters", {}).keys())
        candidates = []
        for chapter_no in chapter_numbers:
            candidates.extend(by_chapter.get(int(chapter_no), []))
        candidates = [question for question in candidates if str(question.get("knowledge_point") or "") == row["knowledge_point"]]
        picked = choose_questions(candidates, 1, seed=args.seed, exclude_ids=selected_ids)
        selected.extend(picked)
        selected_ids.update(question["id"] for question in picked)
        if len(selected) >= args.count:
            break
    if len(selected) < args.count:
        chapters = [int(args.chapter)] if args.chapter else list(range(1, 25))
        fallback = [question for chapter in chapters for question in by_chapter.get(chapter, [])]
        selected.extend(choose_questions(fallback, args.count - len(selected), seed=args.seed, exclude_ids=selected_ids, difficulty=args.difficulty))
    selected = selected[: args.count]
    session = make_session("drill", [question["id"] for question in selected], {"chapter": args.chapter, "count": args.count, "difficulty": args.difficulty, "seed": args.seed})
    session_path = write_session(session)
    return {
        "session": session,
        "session_file": str(session_path.relative_to(ROOT)),
        "target_points": target_points[: args.count],
        "questions": [public_question(question) for question in selected],
        "next_step": f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown",
    }


def render_drill_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# 专项题单",
        "",
        f"Session: {payload['session']['id']}",
        f"File: {payload['session_file']}",
        "",
        "## 目标知识点",
    ]
    for row in payload["target_points"]:
        lines.append(f"- {row['knowledge_point']}: {row['score']}/100，{row['level']}")
    lines.append("")
    lines.append(render_questions_markdown(payload["questions"]).rstrip() if payload["questions"] else "No questions matched this request.")
    lines.append("")
    lines.append(f"Next: {payload['next_step']}")
    return "\n".join(lines) + "\n"


def command_drill(args: argparse.Namespace) -> int:
    payload = build_drill_payload(args)
    if args.format == "markdown":
        print(render_drill_markdown(payload))
    else:
        print(json.dumps(simplify_json(payload), ensure_ascii=False, indent=2))
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
    return {"name": name, "status": status, "error": error, "output_preview": output[:300]}


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


def build_regression_payload(args: argparse.Namespace) -> dict[str, Any]:
    cases = [
        ("audit", command_audit, argparse.Namespace(limit=5, min_explanation_length=30, format="markdown"), {"contains": "问题数量：0"}),
        ("dashboard", command_dashboard, argparse.Namespace(limit=4, include_audit=True, format="markdown"), {"contains": "学习驾驶舱"}),
        ("profile", command_profile, argparse.Namespace(format="markdown"), {"contains": "个人备考画像"}),
        ("profile_update_preview", command_profile_update, argparse.Namespace(text="我每天能学1小时，论文最弱，优先保过", write=False, format="markdown"), {"contains": "availability.daily_minutes"}),
        ("profile_update_sensitive_block", command_profile_update, argparse.Namespace(text="保存到画像：我每天能学1小时，手机号13800000000", write=True, format="markdown"), {"contains": "写入被拦截"}),
        ("mastery", command_mastery, argparse.Namespace(limit=5, chapter=None, format="markdown"), {"contains": "知识点掌握度"}),
        ("readiness", command_readiness, argparse.Namespace(format="markdown"), {"contains": "备考成熟度评分"}),
        ("report", command_report, argparse.Namespace(period="weekly", format="markdown"), {"contains": "学习周报"}),
        ("exam_guide", command_exam_guide, argparse.Namespace(limit=5, format="markdown"), {"contains": "论文：第4-17章"}),
        ("internal_notes", command_internal_material, argparse.Namespace(kind="notes", chapter=12, preview_lines=3, format="markdown"), {"contains": "第12章 信息系统服务管理"}),
        ("internal_mindmap", command_internal_material, argparse.Namespace(kind="mindmap", chapter=12, preview_lines=3, format="markdown"), {"contains": "服务战略规划"}),
        ("backup_past_exams", command_backup_pdfs, argparse.Namespace(category="past-exam", year=None, subject=None, limit=5, format="markdown"), {"contains": "历年真题"}),
        ("past_exam_choices", command_regression_past_exam_choices, argparse.Namespace(year=2022, period=None, count=2, seed=1, format="markdown"), {"contains": "历年真题选择题"}),
        ("past_exam_case", command_regression_past_exam_case, argparse.Namespace(year=2021, period=None, count=1, seed=1, show_answer=False, format="markdown"), {"contains": "历年案例真题"}),
        ("past_exam_paper", command_past_exam_paper, argparse.Namespace(year=2022, period=None, topic=None, count=2, seed=1, format="markdown"), {"contains": "历年论文真题"}),
        ("backup_standards", command_backup_pdfs, argparse.Namespace(category="standards", year=None, subject=None, limit=5, format="markdown"), {"contains": "标准规范库"}),
        ("standards_list", command_standards_list, argparse.Namespace(document=None, tag=None, limit=5, format="markdown"), {"contains": "标准规范结构化训练库"}),
        ("standards_clauses", command_standards_clauses, argparse.Namespace(document="网络安全法", keyword=None, tag=None, limit=3, format="markdown"), {"contains": "标准规范条款检索"}),
        ("standards_start", command_regression_standards_start, argparse.Namespace(document="网络安全法", keyword=None, tag=None, count=2, seed=1, format="markdown"), {"contains": "标准规范专项训练"}),
        ("standards_submit_no_record", command_regression_standards_submit, argparse.Namespace(format="markdown"), {"contains": "Recorded: False"}),
        ("sprint_materials", command_sprint_material, argparse.Namespace(kind="sprint-guide", keyword=None, limit=5, preview_lines=3, format="markdown"), {"contains": "规划冲刺资料"}),
        ("search_materials", command_search, argparse.Namespace(query="服务目录设计", source_type=None, chapter=None, limit=3, format="markdown"), {"contains": "全资料检索"}),
        ("sprint_training_cards", command_sprint_training_cards, argparse.Namespace(kind="activities", keyword=None, count=2, seed=1, show_answer=False, format="markdown"), {"contains": "冲刺背诵卡"}),
        ("sprint_training_start", command_regression_sprint_training_start, argparse.Namespace(kind="mock-exam", keyword=None, count=2, seed=1, format="markdown"), {"contains": "冲刺模拟候选题训练"}),
        ("sprint_training_case", command_sprint_training_case, argparse.Namespace(kind="csf-risk", keyword=None, count=2, seed=1, show_answer=False, format="markdown"), {"contains": "冲刺案例采分点训练"}),
        ("candidate_practice", command_candidate_practice, argparse.Namespace(chapter=12, count=2, format="markdown"), {"contains": "候选题源仅用于预览"}),
        ("recitation", command_recitation, argparse.Namespace(chapter=12, count=2, show_answer=True, format="markdown"), {"contains": "参考答案/采分点"}),
        ("case_recitation_start", command_regression_case_recitation_start, argparse.Namespace(format="markdown"), {"contains": "cs_recite_ch12"}),
        ("paper_reference", command_paper_reference, argparse.Namespace(topic="信息系统规划", scenario="政务", format="markdown"), {"contains": "内部论文专题参考"}),
        ("paper_start_refs", command_paper, argparse.Namespace(topic="信息系统规划", limit=8, format="markdown"), {"contains": "内部论文专题参考"}),
        ("paper_no_record", command_regression_paper_no_record, argparse.Namespace(format="markdown"), {"contains": "记录写入：否"}),
        ("ask_dashboard", command_ask, argparse.Namespace(text="今天我该学什么", execute=True, no_record=True, format="markdown"), {"contains": "学习驾驶舱"}),
        ("ask_plan", command_ask, argparse.Namespace(text="给我安排今日计划", execute=True, no_record=True, format="markdown"), {"contains": "每日学习计划"}),
        ("ask_profile", command_ask, argparse.Namespace(text="查看我的备考画像", execute=True, no_record=True, format="markdown"), {"contains": "个人备考画像"}),
        ("ask_profile_update_preview", command_ask, argparse.Namespace(text="我每天能学1小时，论文最弱，优先保过", execute=True, no_record=True, format="markdown"), {"contains": "画像自然语言更新"}),
        ("ask_profile_update_command", command_ask, argparse.Namespace(text="保存到画像：我每天能学1小时，论文最弱，优先保过", execute=False, no_record=True, format="markdown"), {"contains": "profile-update"}),
        ("ask_backup_past_exam", command_ask, argparse.Namespace(text="查看2023年历年真题资料", execute=True, no_record=True, format="markdown"), {"contains": "2023"}),
        ("ask_past_exam_choice", command_ask, argparse.Namespace(text="给我出2道2022年真题", execute=False, no_record=True, format="markdown"), {"contains": "past-exam start --year 2022"}),
        ("ask_past_exam_case", command_ask, argparse.Namespace(text="做2021年案例真题", execute=False, no_record=True, format="markdown"), {"contains": "past-exam case --year 2021"}),
        ("ask_past_exam_paper", command_ask, argparse.Namespace(text="查看2022年论文真题", execute=False, no_record=True, format="markdown"), {"contains": "past-exam paper --year 2022"}),
        ("ask_standards_training", command_ask, argparse.Namespace(text="给我出2道网络安全法标准规范题", execute=False, no_record=True, format="markdown"), {"contains": "standards start --document 网络安全法"}),
        ("ask_standards_clauses", command_ask, argparse.Namespace(text="查看网络安全法条款", execute=True, no_record=True, format="markdown"), {"contains": "标准规范条款检索"}),
        ("ask_vip_material", command_ask, argparse.Namespace(text="查看VIP理论必背材料", execute=False, no_record=True, format="markdown"), {"contains": "vip --kind theory-core"}),
        ("ask_sprint_material", command_ask, argparse.Namespace(text="查看金色考点冲刺资料", execute=False, no_record=True, format="markdown"), {"contains": "sprint-materials --kind gold-points"}),
        ("ask_search_material", command_ask, argparse.Namespace(text="全资料检索 服务目录设计", execute=False, no_record=True, format="markdown"), {"contains": "study.py search"}),
        ("ask_sprint_training", command_ask, argparse.Namespace(text="练5个130个活动", execute=False, no_record=True, format="markdown"), {"contains": "sprint-training cards --kind activities --count 5"}),
        ("ask_formal_practice", command_ask, argparse.Namespace(text="给我出2道第12章正式入库题", execute=False, no_record=True, format="markdown"), {"contains": "--tag 正式入库"}),
        ("ask_drill", command_ask, argparse.Namespace(text="按薄弱点给我出2道题", execute=False, no_record=True, format="markdown"), {"contains": "python scripts/study.py drill --count 2 --format markdown"}),
        ("ask_paper_reference", command_ask, argparse.Namespace(text="给我信息系统规划政务论文范文参考", execute=True, no_record=True, format="markdown"), {"contains": "内部论文专题参考"}),
        ("ask_paper_review_needs_input", command_ask, argparse.Namespace(text="我论文写好了帮我批", execute=True, no_record=True, format="markdown"), {"contains": "请提供 --draft 文件或 --text 草稿内容"}),
        ("ask_answer_no_record", command_ask, argparse.Namespace(text="我的答案是 A B C", execute=True, no_record=True, format="markdown"), {"contains": "Recorded: False"}),
    ]
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


def render_submit_latest_markdown(payload: dict[str, Any]) -> str:
    if payload.get("error"):
        return f"{payload['error']}\n"
    if payload.get("route_type") == "case_submit":
        return render_case_submit_markdown(payload)
    return render_grade_markdown(payload)


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
            lines.append(f"   - {task['title']}: {task['command']}")
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


def extract_count(text: str, default: int = 5) -> int:
    match = re.search(r"(\d+)\s*(?:道|题|个|篇)", text)
    if match:
        return int(match.group(1))
    return default


def extract_chapters_from_text(text: str) -> str | None:
    match = re.search(r"第\s*(\d+)\s*章", text)
    if match:
        return match.group(1)
    if "案例" in text:
        return case_range_chapters_text()
    for topic, data in PAPER_TOPICS.items():
        if topic in text or data["chapter_title"] in text:
            return str(data["chapter"])
    return None


def detect_topic_from_text(text: str) -> str:
    resolved = resolve_paper_topic(text)
    return resolved[0] if resolved else DEFAULT_PAPER_TOPIC


def detect_paper_scenario_from_text(text: str) -> str | None:
    if any(word in text for word in ("政务", "政府", "一网通办", "公共服务")):
        return "政务"
    if any(word in text for word in ("医院", "医疗", "病患", "门诊")):
        return "医院"
    if any(word in text for word in ("制造", "工厂", "生产", "车间", "智能制造")):
        return "制造"
    return None


def detect_report_period(text: str) -> str:
    if any(word in text for word in ("月报", "本月", "月度")):
        return "monthly"
    if any(word in text for word in ("诊断", "考前", "通过率", "风险")):
        return "exam"
    return "weekly"


def extract_year_from_text(text: str) -> int | None:
    match = re.search(r"(20\d{2})", text)
    return int(match.group(1)) if match else None


def detect_period_from_text(text: str) -> str | None:
    if any(word in text for word in ("上半年", "5月", "05月", "五月")):
        return "上半年"
    if any(word in text for word in ("下半年", "11月", "十一月")):
        return "下半年"
    return None


def is_past_exam_training_request(text: str) -> bool:
    if not any(word in text for word in ("真题", "历年")):
        return False
    if any(word in text for word in ("论文真题", "案例真题", "上午真题", "选择题真题", "选择真题", "综合知识真题")):
        return True
    if any(word in text for word in ("真题资料", "真题解析", "备份资料", "备份PDF", "F盘资料")):
        return False
    return any(word in text for word in ("练", "刷", "出题", "出", "开始", "训练", "做", "来一道", "来几道"))


def is_standards_training_request(text: str) -> bool:
    if not any(word in text for word in ("标准规范", "规范库", "法规", "法律", "网络安全法", "密码法", "保密法", "ISO20000", "GB50462", "机房施工", "桌面及外围设备")):
        return False
    if any(word in text for word in ("资料", "索引", "清单", "PDF", "目录", "有哪些")):
        return False
    return any(word in text for word in ("练", "刷", "出题", "出", "开始", "训练", "做", "来一道", "来几道", "专项"))


def is_standards_clause_request(text: str) -> bool:
    standard_words = ("标准规范", "规范库", "法规", "法律", "网络安全法", "密码法", "保密法", "ISO20000", "GB50462", "机房施工", "桌面及外围设备")
    if any(word in text for word in ("资料", "索引", "清单", "PDF", "目录", "有哪些")):
        return False
    clause_words = ("条款", "条文", "原文", "摘要", "查看", "查询", "检索", "看看")
    return any(word in text for word in standard_words) and any(word in text for word in clause_words)


def detect_standard_document_from_text(text: str) -> str | None:
    for keyword in ("网络安全法", "密码法", "保密法", "ISO20000", "GB50462", "机房施工", "桌面及外围设备", "政府采购评审", "信用管理"):
        if keyword.lower() in text.lower():
            return keyword
    return None


def is_formal_practice_request(text: str) -> bool:
    formal_words = ("正式入库", "正式题库", "正式练习", "精选题", "已入库", "入库题")
    practice_words = ("出题", "练", "练习", "刷题", "题")
    return any(word in text for word in formal_words) and any(word in text for word in practice_words)


def is_search_request(text: str) -> bool:
    if any(word in text for word in ("检索", "搜索", "查资料", "查询资料", "全资料", "资料里", "资料中", "哪里提到", "在哪个资料", "来源")):
        return True
    if any(word in text for word in ("帮我找", "找一下", "查一下")) and not any(word in text for word in ("条款", "真题", "资料清单", "目录")):
        return True
    return False


def detect_search_source_type(text: str) -> str | None:
    mapping = [
        (("三色笔记", "高频笔记"), "three_color_notes"),
        (("思维导图",), "mindmap"),
        (("真题", "历年"), "past_exam"),
        (("标准规范", "法规", "法律", "条款"), "standards_training"),
        (("冲刺", "金色考点", "记忆口诀", "130个活动", "关键成功因素", "风险控制"), "sprint_material"),
        (("VIP", "vip", "理论必背"), "vip_material"),
        (("论文", "范文"), "paper_special"),
        (("案例",), "case_study"),
    ]
    for words, source_type in mapping:
        if any(word in text for word in words):
            return source_type
    return None


def strip_search_markers(text: str) -> str:
    value = text.strip()
    for marker in ("全资料检索", "全资料搜索", "检索", "搜索", "查资料", "查询资料", "资料里", "资料中", "帮我找", "找一下", "查一下", "哪里提到", "在哪个资料"):
        value = value.replace(marker, " ")
    value = re.sub(r"\s+", " ", value).strip(" ：:")
    return value or text.strip()


def route_intent(text: str) -> dict[str, Any]:
    normalized = text.strip()
    count = extract_count(normalized)
    answer_info = answer_payload_from_text(normalized)
    if answer_info:
        return {"intent": "submit_latest", "command": "python scripts/study.py ask \"我的答案是 A B C D\" --format markdown", "execute": "submit_latest"}
    if is_profile_update_request(normalized):
        write = profile_write_requested(normalized)
        write_part = " --write" if write else ""
        return {
            "intent": "profile_update",
            "command": f"python scripts/study.py profile-update \"{normalized}\"{write_part} --format markdown",
            "execute": "profile_update",
            "write": write,
        }
    if any(word in normalized for word in ("继续", "接着", "上次", "刚才", "没做完", "断点", "接着学", "恢复")):
        return {"intent": "continue", "command": "python scripts/study.py continue --format markdown", "execute": "continue"}
    if any(word in normalized for word in ("周报", "月报", "学习报告", "诊断报告", "考前诊断", "复盘报告")):
        period = detect_report_period(normalized)
        return {"intent": "report", "command": f"python scripts/study.py report --period {period} --format markdown", "execute": "report", "period": period}
    if any(word in normalized for word in ("回归测试", "自检", "冒烟测试", "自动测试")):
        return {"intent": "regression", "command": "python scripts/study.py regression --format markdown", "execute": "regression"}
    if any(word in normalized for word in ("个人画像", "备考画像", "学习画像", "学习设置", "我的设置", "我的目标", "备考目标")):
        return {"intent": "profile", "command": "python scripts/study.py profile --format markdown", "execute": "profile"}
    if any(word in normalized for word in ("考试时间", "考试科目", "考试安排", "学习指南", "大纲分析", "考试大纲", "分值预测", "章节重点", "新版大纲")):
        return {"intent": "exam_guide", "command": "python scripts/study.py exam-guide --format markdown", "execute": "exam_guide"}
    if any(word in normalized for word in ("三色笔记", "背诵笔记", "高频笔记")):
        chapters = extract_chapters_from_text(normalized)
        chapter_part = f" --chapter {chapters}" if chapters and "," not in chapters and "-" not in chapters else ""
        return {"intent": "internal_material", "command": f"python scripts/study.py internal --kind notes{chapter_part} --format markdown", "execute": "internal_material", "kind": "notes", "chapter": chapters if chapters and "," not in chapters and "-" not in chapters else None}
    if any(word in normalized for word in ("思维导图", "知识结构", "章节速览", "结构导航")):
        chapters = extract_chapters_from_text(normalized)
        chapter_part = f" --chapter {chapters}" if chapters and "," not in chapters and "-" not in chapters else ""
        return {"intent": "internal_material", "command": f"python scripts/study.py internal --kind mindmap{chapter_part} --format markdown", "execute": "internal_material", "kind": "mindmap", "chapter": chapters if chapters and "," not in chapters and "-" not in chapters else None}
    if is_search_request(normalized):
        query = strip_search_markers(normalized)
        source_type = detect_search_source_type(normalized)
        source_part = f" --source-type {source_type}" if source_type else ""
        chapters = extract_chapters_from_text(normalized)
        chapter_value = chapters if chapters and "," not in chapters and "-" not in chapters else None
        chapter_part = f" --chapter {chapter_value}" if chapter_value else ""
        return {"intent": "search", "command": f"python scripts/study.py search \"{query}\"{source_part}{chapter_part} --format markdown", "execute": "search", "query": query, "source_type": source_type, "chapter": int(chapter_value) if chapter_value else None}
    if any(word in normalized for word in ("VIP", "vip", "vip材料", "VIP材料", "理论必背", "一本通")):
        kind = "all"
        if any(word in normalized for word in ("理论必背", "案例论文必背", "必背知识点")):
            kind = "theory-core"
        elif any(word in normalized for word in ("分章节", "章节练习", "练习题")):
            kind = "chapter-practice-answer"
        elif "一本通" in normalized:
            kind = "comprehensive"
        elif "三色" in normalized or "汇总" in normalized:
            kind = "notes-summary"
        kind_part = "" if kind == "all" else f" --kind {kind}"
        return {"intent": "vip_material", "command": f"python scripts/study.py vip{kind_part} --format markdown", "execute": "vip_material", "kind": kind}
    if any(word in normalized for word in ("冲刺", "金色考点", "记忆口诀", "临考突击", "押题", "模考题", "模拟题", "关键成功因素", "风险控制", "130个活动", "130 个活动", "规划冲刺资料", "马军")) and any(word in normalized for word in ("练", "训练", "背", "默写", "出题", "刷题", "采分点", "考我")):
        kind = "all"
        if any(word in normalized for word in ("记忆口诀", "口诀")):
            kind = "mnemonic"
        elif any(word in normalized for word in ("金色考点", "临考突击", "押题")):
            kind = "gold-points"
        elif any(word in normalized for word in ("模考题", "模拟题")):
            kind = "mock-exam"
        elif any(word in normalized for word in ("关键成功因素", "风险控制")):
            kind = "csf-risk"
        elif any(word in normalized for word in ("130个活动", "130 个活动", "活动")):
            kind = "activities"
        elif any(word in normalized for word in ("规划冲刺资料", "马军")):
            kind = "sprint-guide"
        kind_part = "" if kind == "all" else f" --kind {kind}"
        if any(word in normalized for word in ("模考题", "模拟题", "选择题", "刷题", "出题")):
            return {"intent": "sprint_training_start", "command": f"python scripts/study.py sprint-training start{kind_part} --count {count} --format markdown", "execute": "sprint_training_start", "kind": kind, "count": count}
        if any(word in normalized for word in ("案例", "采分点", "主观题")):
            return {"intent": "sprint_training_case", "command": f"python scripts/study.py sprint-training case{kind_part} --count {count} --format markdown", "execute": "sprint_training_case", "kind": kind, "count": count}
        return {"intent": "sprint_training_cards", "command": f"python scripts/study.py sprint-training cards{kind_part} --count {count} --format markdown", "execute": "sprint_training_cards", "kind": kind, "count": count}
    if any(word in normalized for word in ("冲刺资料", "金色考点", "记忆口诀", "临考突击", "押题资料", "模考题", "模拟题资料", "关键成功因素", "风险控制", "130个活动", "130 个活动", "规划冲刺资料", "马军")):
        kind = "all"
        if any(word in normalized for word in ("记忆口诀", "口诀")):
            kind = "mnemonic"
        elif any(word in normalized for word in ("金色考点", "临考突击", "押题")):
            kind = "gold-points"
        elif any(word in normalized for word in ("模考题", "模拟题")):
            kind = "mock-exam"
        elif any(word in normalized for word in ("关键成功因素", "风险控制")):
            kind = "csf-risk"
        elif any(word in normalized for word in ("130个活动", "130 个活动", "活动")):
            kind = "activities"
        elif any(word in normalized for word in ("规划冲刺资料", "马军")):
            kind = "sprint-guide"
        kind_part = "" if kind == "all" else f" --kind {kind}"
        return {"intent": "sprint_material", "command": f"python scripts/study.py sprint-materials{kind_part} --format markdown", "execute": "sprint_material", "kind": kind}
    if is_past_exam_training_request(normalized):
        year = extract_year_from_text(normalized)
        period = detect_period_from_text(normalized)
        year_part = f" --year {year}" if year else ""
        period_part = f" --period {period}" if period else ""
        if "案例" in normalized or "主观题" in normalized:
            return {
                "intent": "past_exam_case",
                "command": f"python scripts/study.py past-exam case{year_part}{period_part} --count 1 --format markdown",
                "execute": "past_exam_case",
                "year": year,
                "period": period,
                "count": 1,
            }
        if "论文" in normalized or "作文" in normalized:
            return {
                "intent": "past_exam_paper",
                "command": f"python scripts/study.py past-exam paper{year_part}{period_part} --format markdown",
                "execute": "past_exam_paper",
                "year": year,
                "period": period,
                "count": count,
            }
        return {
            "intent": "past_exam_choice",
            "command": f"python scripts/study.py past-exam start{year_part}{period_part} --count {count} --format markdown",
            "execute": "past_exam_choice",
            "year": year,
            "period": period,
            "count": count,
        }
    if is_standards_clause_request(normalized):
        document = detect_standard_document_from_text(normalized)
        document_part = f" --document {document}" if document else ""
        return {
            "intent": "standards_clauses",
            "command": f"python scripts/study.py standards clauses{document_part} --limit 10 --format markdown",
            "execute": "standards_clauses",
            "document": document,
        }
    if is_standards_training_request(normalized):
        document = detect_standard_document_from_text(normalized)
        document_part = f" --document {document}" if document else ""
        return {
            "intent": "standards_training",
            "command": f"python scripts/study.py standards start{document_part} --count {count} --format markdown",
            "execute": "standards_training",
            "document": document,
            "count": count,
        }
    if any(word in normalized for word in ("历年真题", "真题资料", "真题解析", "标准规范", "规范库", "法规库", "模拟题库", "F盘资料", "备份PDF", "备份资料")):
        category = backup_category_from_text(normalized)
        year = extract_year_from_text(normalized)
        subject = None
        if any(word in normalized for word in ("上午", "选择", "综合")):
            subject = "综合知识"
        elif "案例" in normalized:
            subject = "案例分析"
        elif "论文" in normalized:
            subject = "论文"
        year_part = f" --year {year}" if year else ""
        subject_part = f" --subject {subject}" if subject else ""
        return {"intent": "backup_pdfs", "command": f"python scripts/study.py backup-pdfs --category {category}{year_part}{subject_part} --format markdown", "execute": "backup_pdfs", "category": category, "year": year, "subject": subject}
    if is_formal_practice_request(normalized):
        chapters = extract_chapters_from_text(normalized)
        chapter_part = f" --chapters {chapters}" if chapters else ""
        return {"intent": "practice", "command": f"python scripts/study.py start{chapter_part} --tag 正式入库 --count {count} --format markdown", "execute": "start", "chapters": chapters, "count": count, "tag": "正式入库"}
    if any(word in normalized for word in ("千题闯关", "候选题", "内部习题", "章节习题资料", "新版习题")):
        chapters = extract_chapters_from_text(normalized)
        chapter_part = f" --chapter {chapters}" if chapters and "," not in chapters and "-" not in chapters else ""
        return {"intent": "candidate_practice", "command": f"python scripts/study.py candidate{chapter_part} --count {count} --format markdown", "execute": "candidate_practice", "chapter": chapters if chapters and "," not in chapters and "-" not in chapters else None, "count": count}
    if any(word in normalized for word in ("正式案例背诵", "正式采分点", "背诵案例训练", "案例背诵训练")) and any(word in normalized for word in ("练", "出", "开始", "训练")):
        chapters = extract_chapters_from_text(normalized)
        chapter_part = f" --chapters {chapters}" if chapters else ""
        return {"intent": "case_start", "command": f"python scripts/study.py case start{chapter_part} --source recitation --count 1 --format markdown", "execute": "case_start", "chapters": chapters, "source": "recitation"}
    if any(word in normalized for word in ("案例背诵", "案例默写", "背诵题", "采分点背诵", "案例采分点")):
        chapters = extract_chapters_from_text(normalized)
        chapter_part = f" --chapter {chapters}" if chapters and "," not in chapters and "-" not in chapters else ""
        show_answer = any(word in normalized for word in ("答案", "采分点", "对照", "解析"))
        answer_part = " --show-answer" if show_answer else ""
        return {"intent": "recitation", "command": f"python scripts/study.py recite{chapter_part} --count {count}{answer_part} --format markdown", "execute": "recitation", "chapter": chapters if chapters and "," not in chapters and "-" not in chapters else None, "count": count, "show_answer": show_answer}
    if any(word in normalized for word in ("今日计划", "每日计划", "今天计划", "今日安排", "每日安排")):
        return {"intent": "plan", "command": "python scripts/study.py plan --format markdown", "execute": "plan"}
    if any(word in normalized for word in ("今天", "下一步", "学什么", "总览", "驾驶舱", "安排一下", "怎么学", "当前状态")):
        return {"intent": "dashboard", "command": "python scripts/study.py dashboard --format markdown", "execute": "dashboard"}
    if any(word in normalized for word in ("冲刺", "备考计划", "战略", "备考安排", "倒计时")):
        days_match = re.search(r"(\d+)\s*天", normalized)
        days = int(days_match.group(1)) if days_match else 14
        return {"intent": "sprint", "command": f"python scripts/study.py sprint --days {days} --format markdown", "execute": "sprint", "days": days}
    if any(word in normalized for word in ("成熟度", "准备度", "备考水平", "能不能过", "通过风险", "通过概率")):
        return {"intent": "readiness", "command": "python scripts/study.py readiness --format markdown", "execute": "readiness"}
    if any(word in normalized for word in ("专项", "题单", "针对薄弱", "薄弱点练习", "定向练习", "个性化练习", "按薄弱点", "薄弱点出题")):
        chapters = extract_chapters_from_text(normalized)
        chapter_part = f" --chapter {chapters}" if chapters and "," not in chapters and "-" not in chapters else ""
        return {"intent": "drill", "command": f"python scripts/study.py drill{chapter_part} --count {count} --format markdown", "execute": "drill", "chapter": chapters if chapters and "," not in chapters and "-" not in chapters else None, "count": count}
    if any(word in normalized for word in ("掌握度", "薄弱知识点", "最薄弱", "会不会", "掌握情况", "哪里弱", "不会什么", "薄弱点")):
        return {"intent": "mastery", "command": "python scripts/study.py mastery --format markdown", "execute": "mastery"}
    if any(word in normalized for word in ("错因", "根因", "为什么错", "错题分析", "错在哪里", "错题原因")):
        return {"intent": "root_cause", "command": "python scripts/study.py root-cause --format markdown", "execute": "root_cause"}
    if "错题" in normalized and any(word in normalized for word in ("复习", "到期", "今天")):
        return {"intent": "review", "command": "python scripts/study.py review --format markdown", "execute": "review"}
    if "错题" in normalized:
        return {"intent": "wrong_retry", "command": f"python scripts/study.py start --mode wrong --count {count} --format markdown", "execute": "start", "mode": "wrong", "count": count}
    if any(word in normalized for word in ("案例", "主观题")) and any(word in normalized for word in ("练", "出", "开始")):
        case_chapters = case_range_chapters_text()
        return {"intent": "case_start", "command": f"python scripts/study.py case start --chapters {case_chapters} --count 1 --format markdown", "execute": "case_start", "chapters": case_chapters}
    if any(word in normalized for word in ("论文专题", "论文范文", "范文参考", "论文参考", "评分标准", "框架格式", "写作模板")):
        topic = detect_topic_from_text(normalized)
        scenario = detect_paper_scenario_from_text(normalized)
        scenario_part = f" --scenario {scenario}" if scenario else ""
        return {"intent": "paper_reference", "command": f"python scripts/study.py paper-ref --topic {topic}{scenario_part} --format markdown", "execute": "paper_reference", "topic": topic, "scenario": scenario}
    if any(word in normalized for word in ("论文", "作文", "草稿", "文章")) and any(word in normalized for word in ("评分", "点评", "批改", "看看", "评一下", "写好了", "写完了", "帮我批")):
        topic = detect_topic_from_text(normalized)
        return {"intent": "paper_review", "command": f"python scripts/study.py paper submit --topic {topic} --draft <draft.md> --format markdown", "execute": None, "needs_input": "请提供 --draft 文件或 --text 草稿内容。"}
    if any(word in normalized for word in ("论文", "框架", "写作", "提纲", "素材")):
        topic = detect_topic_from_text(normalized)
        return {"intent": "paper_start", "command": f"python scripts/study.py paper --topic {topic} --format markdown", "execute": "paper", "topic": topic}
    if any(word in normalized for word in ("覆盖", "没练", "盲区", "知识点", "漏掉", "空白点")):
        return {"intent": "coverage", "command": "python scripts/study.py coverage --format markdown", "execute": "coverage"}
    if any(word in normalized for word in ("修题库", "修复题库", "质量修复")):
        return {"intent": "fix_quality", "command": "python scripts/study.py fix-quality --fix-options --rebalance-answers --rebalance-difficulty --format markdown", "execute": "fix_quality"}
    if any(word in normalized for word in ("题库质量", "审计", "题库怎么样", "题目质量")):
        return {"intent": "audit", "command": "python scripts/study.py audit --format markdown", "execute": "audit"}
    chapters = extract_chapters_from_text(normalized)
    if any(word in normalized for word in ("出题", "练习", "刷题", "题")):
        chapter_part = f" --chapters {chapters}" if chapters else ""
        return {"intent": "practice", "command": f"python scripts/study.py start{chapter_part} --count {count} --format markdown", "execute": "start", "chapters": chapters, "count": count}
    return {"intent": "dashboard", "command": "python scripts/study.py dashboard --format markdown", "execute": "dashboard"}


def build_ask_payload(args: argparse.Namespace) -> dict[str, Any]:
    route = route_intent(args.text)
    payload = {"text": args.text, "route": route}
    if not args.execute or route.get("needs_input"):
        return payload
    intent = route.get("execute")
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
        payload["result"] = build_drill_payload(argparse.Namespace(count=route.get("count", 5), chapter=route.get("chapter"), difficulty=None, seed=None, format=args.format))
    elif intent == "root_cause":
        payload["result"] = build_root_cause_payload(argparse.Namespace(limit=10, session=None, format=args.format))
    elif intent == "report":
        payload["result"] = build_report_payload(argparse.Namespace(period=route.get("period", "weekly"), format=args.format))
    elif intent == "regression":
        payload["result"] = build_regression_payload(argparse.Namespace(verbose=False, format=args.format))
    elif intent == "profile":
        payload["result"] = build_profile_payload(argparse.Namespace(format=args.format))
    elif intent == "profile_update":
        write_profile = bool(route.get("write", False)) and not bool(getattr(args, "no_record", False))
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
        payload["result"] = build_sprint_training_start_payload(argparse.Namespace(kind=route.get("kind", "all"), keyword=None, count=route.get("count", 5), seed=None, format=args.format))
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
            argparse.Namespace(year=route.get("year"), period=route.get("period"), count=route.get("count", 5), seed=None, format=args.format)
        )
    elif intent == "past_exam_case":
        payload["result"] = build_past_exam_case_payload(
            argparse.Namespace(year=route.get("year"), period=route.get("period"), count=route.get("count", 1), seed=None, show_answer=False, format=args.format)
        )
    elif intent == "past_exam_paper":
        payload["result"] = build_past_exam_paper_payload(
            argparse.Namespace(year=route.get("year"), period=route.get("period"), count=route.get("count", 5), topic=None, seed=None, format=args.format)
        )
    elif intent == "standards_training":
        payload["result"] = build_standards_start_payload(
            argparse.Namespace(document=route.get("document"), keyword=None, tag=None, count=route.get("count", 5), seed=None, format=args.format)
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
        start_args = argparse.Namespace(mode=mode, chapters=route.get("chapters"), count=route.get("count", 5), difficulty=None, knowledge_point=None, section=None, tag=route.get("tag"), seed=None, format=args.format)
        session, selected = build_wrong(start_args) if mode == "wrong" else build_practice(start_args)
        session_path = write_session(session)
        payload["result"] = {"session": session, "session_file": str(session_path.relative_to(ROOT)), "questions": [public_question(question) for question in selected], "next_step": f"python scripts/study.py submit --session {session['id']} --answers \"A B C ...\" --format markdown"}
    elif intent == "case_start":
        case_args = argparse.Namespace(chapters=route.get("chapters") or case_range_chapters_text(), count=1, difficulty=None, seed=None, source=route.get("source"), format=args.format)
        cases = load_case_studies()
        cases = filter_cases_by_source(cases, getattr(case_args, "source", None))
        chapters = set(parse_chapters(case_args.chapters))
        cases = [case for case in cases if chapters.intersection(set(case.get("chapters") or [case.get("chapter")]))]
        selected = choose_questions(cases, case_args.count, seed=None)
        session = make_session("case_study", [case["id"] for case in selected], {"chapters": case_args.chapters, "count": 1, "difficulty": None, "seed": None})
        session["case_ids"] = session.pop("question_ids")
        session["answers_template"] = {question["id"]: "" for case in selected for question in case.get("questions", [])}
        session_path = write_session(session)
        payload["result"] = {"session": session, "session_file": str(session_path.relative_to(ROOT)), "cases": [public_case(case) for case in selected], "next_step": f"python scripts/study.py case submit --session {session['id']} --answers \"...\" --format markdown"}
    elif intent == "review":
        payload["result"] = {"due": due_items(20)}
    return payload


def render_ask_markdown(payload: dict[str, Any]) -> str:
    route = payload["route"]
    lines = ["# 自然语言路由", "", f"- 识别意图：{route['intent']}", f"- 建议命令：{route['command']}"]
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
        lines.append(f"Next: {result['next_step']}")
    elif route["intent"] == "case_start":
        lines.append(f"Session: {result['session']['id']}")
        lines.append(f"File: {result['session_file']}")
        for case in result["cases"]:
            lines.append("")
            lines.append(render_case_markdown(case).rstrip())
        lines.append(f"Next: {result['next_step']}")
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a complete study loop.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Start a practice or mock-exam session.")
    start.add_argument("--mode", choices=["practice", "mock", "wrong"], default="practice")
    start.add_argument("--chapters", default=None)
    start.add_argument("--count", type=int, default=5)
    start.add_argument("--difficulty", choices=["easy", "medium", "hard"], default=None)
    start.add_argument("--knowledge-point", default=None)
    start.add_argument("--section", default=None)
    start.add_argument("--tag", default=None)
    start.add_argument("--seed", type=int, default=None)
    start.add_argument("--format", choices=["json", "markdown"], default="json")
    start.set_defaults(func=command_start)

    submit = subparsers.add_parser("submit", help="Submit answers, grade, and record progress.")
    submit.add_argument("--session", required=True)
    submit.add_argument("--answers", required=True, help='Answer text such as "A B C" or "ch01_q001=A,ch01_q002=B".')
    submit.add_argument("--no-record", action="store_true", help="Grade without writing progress/archive files.")
    submit.add_argument("--format", choices=["json", "markdown"], default="json")
    submit.set_defaults(func=command_submit)

    review = subparsers.add_parser("review", help="Show due reviews or mark reviewed questions.")
    review.add_argument("--date", default=None)
    review.add_argument("--limit", type=int, default=20)
    review.add_argument("--mark-reviewed", nargs="*", default=None)
    review.add_argument("--format", choices=["json", "markdown"], default="json")
    review.set_defaults(func=command_review)

    status = subparsers.add_parser("status", help="Show learning status and next action.")
    status.add_argument("--limit", type=int, default=10)
    status.add_argument("--format", choices=["json", "markdown"], default="json")
    status.set_defaults(func=command_status)

    plan = subparsers.add_parser("plan", help="Generate a daily study plan.")
    plan.add_argument("--review-limit", type=int, default=10)
    plan.add_argument("--weak-limit", type=int, default=5)
    plan.add_argument("--practice-count", type=int, default=5)
    plan.add_argument("--default-chapter", type=int, default=12)
    plan.add_argument("--include-mock", action="store_true")
    plan.add_argument("--format", choices=["json", "markdown"], default="json")
    plan.set_defaults(func=command_plan)

    profile = subparsers.add_parser("profile", help="Show learner profile and personalization settings.")
    profile.add_argument("--format", choices=["json", "markdown"], default="json")
    profile.set_defaults(func=command_profile)

    profile_update = subparsers.add_parser("profile-update", help="Preview or write learner profile updates from natural language.")
    profile_update.add_argument("text")
    profile_update.add_argument("--write", action="store_true", help="Write recognized non-sensitive fields into assets/profile/learner_profile.json.")
    profile_update.add_argument("--format", choices=["json", "markdown"], default="json")
    profile_update.set_defaults(func=command_profile_update)

    exam_guide = subparsers.add_parser("exam-guide", help="Show exam schedule, subject ranges, and chapter priorities from internal guide/syllabus.")
    exam_guide.add_argument("--limit", type=int, default=8)
    exam_guide.add_argument("--format", choices=["json", "markdown"], default="json")
    exam_guide.set_defaults(func=command_exam_guide)

    internal = subparsers.add_parser("internal", help="Read structured internal notes or mindmaps by chapter.")
    internal.add_argument("--kind", choices=["notes", "mindmap"], default="notes")
    internal.add_argument("--chapter", type=int, default=None)
    internal.add_argument("--preview-lines", type=int, default=10)
    internal.add_argument("--format", choices=["json", "markdown"], default="json")
    internal.set_defaults(func=command_internal_material)

    vip = subparsers.add_parser("vip", help="List or preview indexed VIP materials.")
    vip.add_argument("--kind", choices=["all", "comprehensive", "chapter-practice-answer", "chapter-practice-blank", "theory-core", "notes-summary", "other"], default="all")
    vip.add_argument("--keyword", default=None)
    vip.add_argument("--limit", type=int, default=10)
    vip.add_argument("--preview-lines", type=int, default=8)
    vip.add_argument("--format", choices=["json", "markdown"], default="json")
    vip.set_defaults(func=command_vip_material)

    sprint_materials = subparsers.add_parser("sprint-materials", help="List or preview indexed sprint/cram materials.")
    sprint_materials.add_argument("--kind", choices=["all", "mnemonic", "gold-points", "mock-exam", "csf-risk", "activities", "sprint-guide"], default="all")
    sprint_materials.add_argument("--keyword", default=None)
    sprint_materials.add_argument("--limit", type=int, default=10)
    sprint_materials.add_argument("--preview-lines", type=int, default=8)
    sprint_materials.add_argument("--format", choices=["json", "markdown"], default="json")
    sprint_materials.set_defaults(func=command_sprint_material)

    sprint_training = subparsers.add_parser("sprint-training", help="Run structured training generated from sprint/cram materials.")
    sprint_training_subparsers = sprint_training.add_subparsers(dest="sprint_training_command", required=True)
    sprint_cards = sprint_training_subparsers.add_parser("cards", help="Practice recall cards from sprint materials.")
    sprint_cards.add_argument("--kind", choices=list(SPRINT_KINDS), default="all")
    sprint_cards.add_argument("--keyword", default=None)
    sprint_cards.add_argument("--count", type=int, default=5)
    sprint_cards.add_argument("--seed", type=int, default=None)
    sprint_cards.add_argument("--show-answer", action="store_true")
    sprint_cards.add_argument("--format", choices=["json", "markdown"], default="json")
    sprint_cards.set_defaults(func=command_sprint_training_cards)
    sprint_start = sprint_training_subparsers.add_parser("start", help="Start a sprint mock candidate choice-question session.")
    sprint_start.add_argument("--kind", choices=list(SPRINT_KINDS), default="all")
    sprint_start.add_argument("--keyword", default=None)
    sprint_start.add_argument("--count", type=int, default=5)
    sprint_start.add_argument("--seed", type=int, default=None)
    sprint_start.add_argument("--format", choices=["json", "markdown"], default="json")
    sprint_start.set_defaults(func=command_sprint_training_start)
    sprint_case = sprint_training_subparsers.add_parser("case", help="Practice sprint case-analysis scoring points.")
    sprint_case.add_argument("--kind", choices=list(SPRINT_KINDS), default="all")
    sprint_case.add_argument("--keyword", default=None)
    sprint_case.add_argument("--count", type=int, default=3)
    sprint_case.add_argument("--seed", type=int, default=None)
    sprint_case.add_argument("--show-answer", action="store_true")
    sprint_case.add_argument("--format", choices=["json", "markdown"], default="json")
    sprint_case.set_defaults(func=command_sprint_training_case)

    search = subparsers.add_parser("search", help="Search across all indexed study materials with source citations.")
    search.add_argument("query")
    search.add_argument("--source-type", choices=list(SEARCH_SOURCE_TYPES), default=None)
    search.add_argument("--chapter", type=int, default=None)
    search.add_argument("--limit", type=int, default=8)
    search.add_argument("--format", choices=["json", "markdown"], default="json")
    search.set_defaults(func=command_search)

    backup_pdfs = subparsers.add_parser("backup-pdfs", help="List indexed PDFs imported from F:\\备份项目.")
    backup_pdfs.add_argument("--category", choices=["all", "past-exam", "standards", "mock"], default="all")
    backup_pdfs.add_argument("--year", type=int, default=None)
    backup_pdfs.add_argument("--subject", default=None)
    backup_pdfs.add_argument("--limit", type=int, default=20)
    backup_pdfs.add_argument("--format", choices=["json", "markdown"], default="json")
    backup_pdfs.set_defaults(func=command_backup_pdfs)

    past_exam = subparsers.add_parser("past-exam", help="Run structured 2017-2024 past-exam training.")
    past_exam_subparsers = past_exam.add_subparsers(dest="past_exam_command", required=True)
    past_exam_start = past_exam_subparsers.add_parser("start", help="Start a past-exam morning choice session.")
    past_exam_start.add_argument("--year", type=int, default=None)
    past_exam_start.add_argument("--period", choices=["上半年", "下半年"], default=None)
    past_exam_start.add_argument("--count", type=int, default=5)
    past_exam_start.add_argument("--seed", type=int, default=None)
    past_exam_start.add_argument("--format", choices=["json", "markdown"], default="json")
    past_exam_start.set_defaults(func=command_past_exam_start)
    past_exam_case = past_exam_subparsers.add_parser("case", help="Start a past-exam case-analysis session.")
    past_exam_case.add_argument("--year", type=int, default=None)
    past_exam_case.add_argument("--period", choices=["上半年", "下半年"], default=None)
    past_exam_case.add_argument("--count", type=int, default=1)
    past_exam_case.add_argument("--seed", type=int, default=None)
    past_exam_case.add_argument("--show-answer", action="store_true")
    past_exam_case.add_argument("--format", choices=["json", "markdown"], default="json")
    past_exam_case.set_defaults(func=command_past_exam_case)
    past_exam_paper = past_exam_subparsers.add_parser("paper", help="Show past-exam paper topics.")
    past_exam_paper.add_argument("--year", type=int, default=None)
    past_exam_paper.add_argument("--period", choices=["上半年", "下半年"], default=None)
    past_exam_paper.add_argument("--topic", default=None)
    past_exam_paper.add_argument("--count", type=int, default=5)
    past_exam_paper.add_argument("--seed", type=int, default=None)
    past_exam_paper.add_argument("--format", choices=["json", "markdown"], default="json")
    past_exam_paper.set_defaults(func=command_past_exam_paper)

    standards = subparsers.add_parser("standards", help="Run structured standards/laws training from 07-标准规范库.")
    standards_subparsers = standards.add_subparsers(dest="standards_command", required=True)
    standards_list = standards_subparsers.add_parser("list", help="List structured standards documents and OCR gaps.")
    standards_list.add_argument("--document", default=None)
    standards_list.add_argument("--tag", default=None)
    standards_list.add_argument("--limit", type=int, default=20)
    standards_list.add_argument("--format", choices=["json", "markdown"], default="json")
    standards_list.set_defaults(func=command_standards_list)
    standards_clauses = standards_subparsers.add_parser("clauses", help="Search structured standards clauses.")
    standards_clauses.add_argument("--document", default=None)
    standards_clauses.add_argument("--keyword", default=None)
    standards_clauses.add_argument("--tag", default=None)
    standards_clauses.add_argument("--limit", type=int, default=10)
    standards_clauses.add_argument("--format", choices=["json", "markdown"], default="json")
    standards_clauses.set_defaults(func=command_standards_clauses)
    standards_start = standards_subparsers.add_parser("start", help="Start a standards/laws single-choice training session.")
    standards_start.add_argument("--document", default=None)
    standards_start.add_argument("--keyword", default=None)
    standards_start.add_argument("--tag", default=None)
    standards_start.add_argument("--count", type=int, default=5)
    standards_start.add_argument("--seed", type=int, default=None)
    standards_start.add_argument("--format", choices=["json", "markdown"], default="json")
    standards_start.set_defaults(func=command_standards_start)

    candidate = subparsers.add_parser("candidate", help="Preview internal chapter-practice candidate questions without recording progress.")
    candidate.add_argument("--chapter", type=int, default=None)
    candidate.add_argument("--count", type=int, default=5)
    candidate.add_argument("--format", choices=["json", "markdown"], default="json")
    candidate.set_defaults(func=command_candidate_practice)

    recite = subparsers.add_parser("recite", help="Preview internal case-recitation prompts and optional scoring points.")
    recite.add_argument("--chapter", type=int, default=None)
    recite.add_argument("--count", type=int, default=5)
    recite.add_argument("--show-answer", action="store_true")
    recite.add_argument("--format", choices=["json", "markdown"], default="json")
    recite.set_defaults(func=command_recitation)

    paper_ref = subparsers.add_parser("paper-ref", help="Show structured internal paper guidance, rubric, framework, and sample references.")
    paper_ref.add_argument("--topic", default=DEFAULT_PAPER_TOPIC)
    paper_ref.add_argument("--scenario", choices=["政务", "医院", "制造"], default=None)
    paper_ref.add_argument("--format", choices=["json", "markdown"], default="json")
    paper_ref.set_defaults(func=command_paper_reference)

    paper = subparsers.add_parser("paper", help="Run paper-writing practice.")
    paper.add_argument("--topic", default=DEFAULT_PAPER_TOPIC, help="Paper topic, default follows the new syllabus range: chapters 4-17.")
    paper.add_argument("--limit", type=int, default=12, help="Number of knowledge points to include.")
    paper.add_argument("--format", choices=["json", "markdown"], default="json")
    paper.set_defaults(func=command_paper)
    paper_subparsers = paper.add_subparsers(dest="paper_command")
    paper_start = paper_subparsers.add_parser("start", help="Generate a paper-writing practice loop.")
    paper_start.add_argument("--topic", default=DEFAULT_PAPER_TOPIC)
    paper_start.add_argument("--limit", type=int, default=12)
    paper_start.add_argument("--format", choices=["json", "markdown"], default="json")
    paper_start.set_defaults(func=command_paper)
    paper_submit = paper_subparsers.add_parser("submit", help="Score a paper draft and return revision advice.")
    paper_submit.add_argument("--topic", default=DEFAULT_PAPER_TOPIC)
    paper_submit.add_argument("--draft", default=None, help="Markdown/text file containing the draft.")
    paper_submit.add_argument("--text", default=None, help="Draft text passed directly on the command line.")
    paper_submit.add_argument("--min-chars", type=int, default=800)
    paper_submit.add_argument("--no-record", action="store_true", help="Score without writing paper attempt history.")
    paper_submit.add_argument("--format", choices=["json", "markdown"], default="json")
    paper_submit.set_defaults(func=command_paper_submit)

    coverage = subparsers.add_parser("coverage", help="Report knowledge-point coverage from question metadata and progress.")
    coverage.add_argument("--limit", type=int, default=10)
    coverage.add_argument("--threshold", type=float, default=0.7, help="Accuracy threshold for low-accuracy points, e.g. 0.7.")
    coverage.add_argument("--min-attempts", type=int, default=2)
    coverage.add_argument("--format", choices=["json", "markdown"], default="json")
    coverage.set_defaults(func=command_coverage)

    audit = subparsers.add_parser("audit", help="Audit question-bank quality without changing data.")
    audit.add_argument("--limit", type=int, default=30)
    audit.add_argument("--min-explanation-length", type=int, default=30)
    audit.add_argument("--format", choices=["json", "markdown"], default="json")
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
    fix_quality.add_argument("--format", choices=["json", "markdown"], default="json")
    fix_quality.set_defaults(func=command_fix_quality)

    dashboard = subparsers.add_parser("dashboard", help="Show a learning dashboard and next actions.")
    dashboard.add_argument("--limit", type=int, default=6)
    dashboard.add_argument("--include-audit", action="store_true", default=True)
    dashboard.add_argument("--format", choices=["json", "markdown"], default="json")
    dashboard.set_defaults(func=command_dashboard)

    mastery = subparsers.add_parser("mastery", help="Score mastery for each knowledge point.")
    mastery.add_argument("--chapter", type=int, default=None)
    mastery.add_argument("--limit", type=int, default=10)
    mastery.add_argument("--format", choices=["json", "markdown"], default="json")
    mastery.set_defaults(func=command_mastery)

    continue_cmd = subparsers.add_parser("continue", help="Resume the latest unfinished session.")
    continue_cmd.add_argument("--type", choices=["practice", "mock_exam", "wrong_retry", "drill", "case_study", "past_exam", "past_exam_case", "standards_training"], default=None)
    continue_cmd.add_argument("--any", action="store_true", help="Allow completed sessions when no unfinished session is available.")
    continue_cmd.add_argument("--format", choices=["json", "markdown"], default="json")
    continue_cmd.set_defaults(func=command_continue)

    drill = subparsers.add_parser("drill", help="Create a personalized drill from weak mastery points.")
    drill.add_argument("--chapter", type=int, default=None)
    drill.add_argument("--count", type=int, default=5)
    drill.add_argument("--difficulty", choices=["easy", "medium", "hard"], default=None)
    drill.add_argument("--seed", type=int, default=None)
    drill.add_argument("--format", choices=["json", "markdown"], default="json")
    drill.set_defaults(func=command_drill)

    root_cause = subparsers.add_parser("root-cause", help="Analyze wrong-answer root causes.")
    root_cause.add_argument("--session", default=None)
    root_cause.add_argument("--limit", type=int, default=10)
    root_cause.add_argument("--format", choices=["json", "markdown"], default="json")
    root_cause.set_defaults(func=command_root_cause)

    report = subparsers.add_parser("report", help="Export weekly/monthly/exam diagnostic study reports.")
    report.add_argument("--period", choices=["weekly", "monthly", "exam"], default="weekly")
    report.add_argument("--format", choices=["json", "markdown"], default="json")
    report.set_defaults(func=command_report)

    regression = subparsers.add_parser("regression", help="Run built-in smoke/regression tests for the skill.")
    regression.add_argument("--verbose", action="store_true")
    regression.add_argument("--format", choices=["json", "markdown"], default="json")
    regression.set_defaults(func=command_regression)

    readiness = subparsers.add_parser("readiness", help="Score exam readiness across knowledge, case, paper, review, and mock practice.")
    readiness.add_argument("--format", choices=["json", "markdown"], default="json")
    readiness.set_defaults(func=command_readiness)

    sprint = subparsers.add_parser("sprint", help="Generate a sprint study plan.")
    sprint.add_argument("--days", type=int, default=14)
    sprint.add_argument("--include-audit", action="store_true", default=True)
    sprint.add_argument("--format", choices=["json", "markdown"], default="json")
    sprint.set_defaults(func=command_sprint)

    ask = subparsers.add_parser("ask", help="Route a natural-language study request.")
    ask.add_argument("text")
    ask.add_argument("--execute", action="store_true", default=True)
    ask.add_argument("--no-record", action="store_true", help="When routing an answer submission, grade without writing progress/archive files.")
    ask.add_argument("--format", choices=["json", "markdown"], default="json")
    ask.set_defaults(func=command_ask)

    case = subparsers.add_parser("case", help="Run case-study practice.")
    case_subparsers = case.add_subparsers(dest="case_command", required=True)
    case_start = case_subparsers.add_parser("start", help="Start case-study practice.")
    case_start.add_argument("--chapters", default=None)
    case_start.add_argument("--count", type=int, default=1)
    case_start.add_argument("--difficulty", choices=["easy", "medium", "hard"], default=None)
    case_start.add_argument("--source", choices=["all", "scenario", "recitation"], default="all", help="Filter formal cases: all, scenario cases, or promoted recitation cases.")
    case_start.add_argument("--seed", type=int, default=None)
    case_start.add_argument("--format", choices=["json", "markdown"], default="json")
    case_start.set_defaults(func=command_case_start)

    case_submit = case_subparsers.add_parser("submit", help="Submit case-study answers.")
    case_submit.add_argument("--session", required=True)
    case_submit.add_argument("--answers", required=True)
    case_submit.add_argument("--no-record", action="store_true", help="Grade without writing case attempt history.")
    case_submit.add_argument("--format", choices=["json", "markdown"], default="json")
    case_submit.set_defaults(func=command_case_submit)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
