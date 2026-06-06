from __future__ import annotations

import re
from typing import Any

from study_modules.profile import is_profile_update_request, profile_write_requested
from study_modules.settings import DEFAULT_CASE_CHAPTERS, DEFAULT_PAPER_TOPIC, PAPER_TOPICS, resolve_paper_topic

_case_range_chapters_resolver = None


def set_case_range_chapters_resolver(resolver: Any) -> None:
    global _case_range_chapters_resolver
    _case_range_chapters_resolver = resolver


def case_range_chapters_text() -> str:
    if _case_range_chapters_resolver is None:
        return DEFAULT_CASE_CHAPTERS
    return str(_case_range_chapters_resolver())

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

def backup_category_from_text(text: str) -> str:
    if any(word in text for word in ("真题", "历年", "上午", "案例真题", "论文真题")):
        return "past-exam"
    if any(word in text for word in ("标准", "规范", "法规", "ISO", "GB", "法律")):
        return "standards"
    if any(word in text for word in ("模拟", "押题", "冲刺")):
        return "mock"
    return "all"

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
    if not any(word in text for word in ("标准规范", "规范库", "法规", "法律", "网络安全法", "密码法", "保密法", "招标投标法", "政府采购法", "ISO20000", "GB50462", "机房施工", "桌面及外围设备")):
        return False
    if any(word in text for word in ("资料", "索引", "清单", "PDF", "目录", "有哪些")):
        return False
    return any(word in text for word in ("练", "刷", "出题", "出", "开始", "训练", "做", "来一道", "来几道", "专项"))


def is_standards_clause_request(text: str) -> bool:
    standard_words = ("标准规范", "规范库", "法规", "法律", "网络安全法", "密码法", "保密法", "招标投标法", "政府采购法", "ISO20000", "GB50462", "机房施工", "桌面及外围设备")
    if any(word in text for word in ("资料", "索引", "清单", "PDF", "目录", "有哪些")):
        return False
    clause_words = ("条款", "条文", "原文", "摘要", "查看", "查询", "检索", "看看")
    return any(word in text for word in standard_words) and any(word in text for word in clause_words)


def detect_standard_document_from_text(text: str) -> str | None:
    for keyword in ("网络安全法", "密码法", "保密法", "招标投标法", "政府采购法", "ISO20000", "GB50462", "机房施工", "桌面及外围设备", "政府采购评审", "信用管理"):
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
