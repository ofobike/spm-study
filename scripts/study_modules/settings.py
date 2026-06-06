from __future__ import annotations

import re
from typing import Any

from study_utils import ROOT

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
ROUTER_EXAMPLES_FILE = ROOT / "assets" / "router_examples.json"
SKILL_FILE = ROOT / "SKILL.md"
SKILL_SUMMARY_SCRIPT = ROOT / "scripts" / "update_skill_summary.py"
DEFAULT_OUTPUT_FORMAT = "markdown"
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
    "mock_bank_enhanced",
    "paper_special",
    "past_exam",
    "past_exam_pdf",
    "past_exam_pdf_enhanced",
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
