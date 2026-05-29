#!/usr/bin/env python3
"""Enrich chapter questions with deterministic metadata fields."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_DIR = ROOT / "assets" / "questions"
CHAPTERS_DIR = QUESTIONS_DIR / "chapters"
REFERENCES_DIR = ROOT / "references"


CHAPTER_FILES = {
    1: "第1章_信息系统与信息技术发展.md",
    2: "第2章_数字中国与数智化发展.md",
    3: "第3章_系统科学与哲学方法论.md",
    4: "第4章_信息系统规划.md",
    5: "第5章_应用系统规划.md",
    6: "第6章_云资源规划.md",
    7: "第7章_网络环境规划.md",
    8: "第8章_数据资源规划.md",
    9: "第9章_信息安全规划.md",
    10: "第10章_云原生系统规划.md",
    11: "第11章_信息系统治理.md",
    12: "第12章_信息系统服务管理.md",
    13: "第13章_人员管理.md",
    14: "第14章_规范与过程管理.md",
    15: "第15章_技术与研发管理.md",
    16: "第16章_资源与工具管理.md",
    17: "第17章_信息系统项目管理.md",
    18: "第18章_智慧城市发展规划.md",
    19: "第19章_智慧园区发展规划.md",
    20: "第20章_数字乡村发展规划.md",
    21: "第21章_企业数字化转型发展规划.md",
    22: "第22章_智能制造发展规划.md",
    23: "第23章_新型消费系统规划.md",
    24: "第24章_法律法规和标准规范.md",
}


CHAPTER_KEYWORDS = {
    1: ["信息化", "信息系统", "诺兰", "OSI", "TCP/IP", "网络", "数据库", "数据仓库", "信息安全", "物联网", "RFID", "区块链", "共识", "云计算", "IaaS", "PaaS", "SaaS", "大数据", "人工智能", "知识图谱", "专家系统", "边缘计算", "数字孪生", "5G", "SDN"],
    2: ["数字化转型", "数字中国", "数字经济", "数字政府", "数字社会", "智慧城市", "数字乡村", "数据要素", "数智化", "数字生态"],
    3: ["矛盾论", "实践论", "系统论", "控制论", "信息论", "耗散结构", "协同论", "突变论", "霍尔", "切克兰德"],
    4: ["信息系统规划", "企业架构", "TOGAF", "Zachman", "BSP", "CSF", "SST", "价值链", "战略规划", "业务流程"],
    5: ["应用系统", "ERP", "CRM", "SCM", "OA", "BI", "数据仓库", "ETL", "OLAP", "中间件", "系统集成", "EAI", "敏捷", "EJB"],
    6: ["云资源", "云计算", "IaaS", "PaaS", "SaaS", "公有云", "私有云", "混合云", "云迁移", "虚拟化", "存储"],
    7: ["网络架构", "OSI", "TCP/IP", "SDN", "NFV", "VPN", "防火墙", "IDS", "IPS", "负载均衡", "CDN", "VLAN", "WLAN"],
    8: ["数据治理", "数据架构", "数据标准", "数据质量", "主数据", "元数据", "数据仓库", "数据湖", "DCMM", "数据库"],
    9: ["信息安全", "等级保护", "ISO27001", "加密", "PKI", "访问控制", "安全审计", "风险评估", "双人控制"],
    10: ["云原生", "容器", "Docker", "Kubernetes", "微服务", "DevOps", "CI/CD", "Serverless", "Service Mesh"],
    11: ["IT治理", "IT审计", "COBIT", "合规", "内部控制", "风险管理", "治理成熟度"],
    12: ["ITIL", "IT服务", "SLA", "OLA", "UC", "服务目录", "服务台", "事件管理", "问题管理", "服务成本", "服务退役", "服务质量", "ISO20000"],
    13: ["人员管理", "团队建设", "能力模型", "RACI", "塔克曼", "激励理论", "马斯洛", "招聘", "培训", "绩效"],
    14: ["流程管理", "CMMI", "BPR", "BPI", "标准化", "过程改进", "SOP"],
    15: ["技术管理", "研发管理", "质量管理", "PDCA", "六西格玛", "配置管理", "知识产权", "技术评审"],
    16: ["资源管理", "运维工具", "监控管理", "自动化运维", "ITSM", "Nagios", "Project", "Bug"],
    17: ["项目管理", "项目集", "项目组合", "WBS", "挣值", "关键路径", "风险管理", "配置管理", "变更管理", "生命周期", "干系人"],
    18: ["智慧城市", "城市大脑", "数字孪生城市", "CIM", "政务数据", "城市治理", "智慧交通", "智慧医疗"],
    19: ["智慧园区", "园区信息化", "智能楼宇", "园区管理平台", "物联网园区", "招商", "低碳"],
    20: ["数字乡村", "农业信息化", "农村电商", "智慧农业", "乡村治理", "互联网+医疗", "农产品"],
    21: ["数字化转型", "企业架构", "数据中台", "业务中台", "低代码", "RPA", "数字营销", "成熟度", "数字化蓝图", "数智赋能"],
    22: ["智能制造", "工业互联网", "CMMM", "工业4.0", "数字工厂", "智能工厂", "MES", "MOM", "PLM", "APS"],
    23: ["新零售", "共享消费", "兴趣消费", "精准营销", "用户体验", "O2O", "直播电商", "XR", "智慧门店"],
    24: ["法律法规", "标准规范", "法的效力层级", "大陆法系", "标准化法", "国家标准", "标准有效期", "法的本质", "法的基本特征", "著作权法", "专利法", "商标法", "招投标法", "数据安全法", "个人信息保护法", "ITSS", "ISO/IEC 20000", "ISO20000", "ITIL", "GB/T", "GB"],
}


SECTION_HINTS = {
    1: [
        ("信息系统发展", ["诺兰", "信息系统发展"]),
        ("人工智能", ["人工智能", "知识图谱", "专家系统"]),
        ("数字挛生", ["数字孪生", "MBSE"]),
        ("边缘计算", ["边缘计算"]),
        ("大数据", ["大数据", "Hadoop", "Spark", "Storm"]),
        ("云计算", ["云计算", "IaaS", "PaaS", "SaaS", "容器"]),
        ("区块链", ["区块链", "共识", "SHA256"]),
        ("物联网", ["物联网", "RFID"]),
        ("计算机网络", ["OSI", "TCP/IP", "网络", "SDN", "5G", "WLAN", "IEEE"]),
        ("数据存储和数据库", ["数据库", "数据仓库", "OLAP", "ACID", "DAS", "SAN", "NAS"]),
        ("信息安全", ["信息安全", "加密", "访问控制", "防火墙", "UEBA"]),
        ("信息化内涵与特征", ["信息化"]),
        ("信息系统内涵与特征", ["信息系统"]),
    ],
    12: [
        ("服务目录管理", ["服务目录"]),
        ("服务需求识别", ["SLA", "OLA", "UC", "可用性", "需求"]),
        ("业务关系管理", ["业务关系", "客户满意", "投诉"]),
        ("服务成本度量", ["成本", "预算", "核算", "结算"]),
        ("服务退役终止", ["退役", "终止", "下线"]),
        ("服务质量管理", ["服务质量", "质量"]),
        ("服务风险管理", ["风险"]),
        ("服务测量", ["测量", "MTBF", "MTTR"]),
        ("服务改进", ["改进"]),
    ],
    17: [
        ("项目基本要素", ["项目", "临时性", "业务价值"]),
        ("价值驱动的项目管理知识体系", ["WBS", "挣值", "关键路径", "风险", "干系人", "生命周期", "变更", "配置"]),
    ],
    21: [
        ("转型驱动力", ["驱动力", "政策", "金融", "双碳", "基础设施"]),
        ("转型关注焦点", ["客户中心", "数智赋能", "敏捷组织", "新型文化", "泛在互联", "软件定义", "平台支撑"]),
        ("转型能力成熟度", ["成熟度", "能力域"]),
        ("转型的规划要点", ["蓝图", "规划", "管控", "人才", "保障"]),
        ("转型系统架构规划设计", ["业务架构", "数据架构", "应用架构", "技术架构", "数据中台", "业务中台"]),
    ],
    22: [
        ("能力成熟度模型", ["CMMM", "成熟度"]),
        ("发展规划要点", ["规划", "OEE", "APS"]),
        ("信息系统架构", ["MES", "MOM", "PLM", "工业互联网", "数字孪生", "智能工厂"]),
    ],
    23: [
        ("规划要点", ["新零售", "共享消费", "兴趣消费", "精准营销", "智慧门店"]),
        ("系统架构", ["系统架构", "供应链", "会员", "XR", "直播电商"]),
    ],
    24: [
        ("标准规范", ["标准", "GB", "GB/T", "ITSS", "ISO/IEC", "ISO20000", "ITIL"]),
        ("法律法规", ["法", "著作权", "专利", "商标", "招投标", "数据安全", "个人信息"]),
    ],
}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def chapter_no_from_question(question: dict[str, Any], fallback: int) -> int:
    chapter = str(question.get("chapter", ""))
    match = re.search(r"第(\d+)章", chapter)
    return int(match.group(1)) if match else fallback


def collect_reference_sections() -> dict[int, list[str]]:
    sections: dict[int, list[str]] = {}
    for chapter_no, filename in CHAPTER_FILES.items():
        path = REFERENCES_DIR / filename
        found: list[str] = []
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^(#{2,3})\s+(.+?)\s*$", line)
                if match:
                    found.append(match.group(2).strip())
        sections[chapter_no] = found
    return sections


def infer_knowledge_point(question: dict[str, Any], chapter_no: int) -> str:
    stem = str(question.get("question", ""))
    text = question_text(question)
    candidates = CHAPTER_KEYWORDS.get(chapter_no, [])
    scored: list[tuple[int, int, str]] = []
    for keyword in candidates:
        keyword_lower = keyword.lower()
        score = 0
        if keyword_lower in stem.lower():
            score += 100
        if keyword_lower in text.lower():
            score += 10
        if score:
            scored.append((score, len(keyword), keyword))
    if scored:
        scored.sort(reverse=True)
        return scored[0][2]

    cleaned = re.sub(r"根据|以下|关于|描述|正确|不正确|哪项|哪个|几项|排列|顺序|包括|不包括|主要|目的|一般|的是|是|为|？|\\?|。|（.*?）|\\(.*?\\)", "", str(question.get("question", "")))
    cleaned = cleaned.strip(" ，,、：:\"“”《》")
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9/+\-.]*|[\u4e00-\u9fff]{2,12}", cleaned)
    return tokens[0] if tokens else f"第{chapter_no}章知识点"


def infer_section(question: dict[str, Any], chapter_no: int, reference_sections: dict[int, list[str]]) -> str:
    text = question_text(question)
    hints = SECTION_HINTS.get(chapter_no, [])
    for section, keywords in hints:
        if any(keyword.lower() in text.lower() for keyword in keywords):
            return section

    sections = reference_sections.get(chapter_no, [])
    for section in sections:
        if section.lower() in text.lower():
            return section

    knowledge_point = infer_knowledge_point(question, chapter_no)
    for section in sections:
        if knowledge_point.lower() in section.lower() or section.lower() in knowledge_point.lower():
            return section

    return sections[0] if sections else f"第{chapter_no}章"


def infer_difficulty(question: dict[str, Any]) -> str:
    text = question_text(question)
    hard_markers = ["计算", "公式", "MTBF", "MTTR", "挣值", "SPI", "CPI", "净现值", "投资回报率", "排序", "顺序", "步骤", "阶段", "成熟度", "GB/T", "ISO", "等级保护"]
    easy_markers = ["是指", "简称", "不属于", "不包括", "定义", "全称", "主体是"]
    option_length = sum(len(str(option)) for option in question.get("options", []))
    explanation_length = len(str(question.get("explanation", "")))

    hard_score = sum(1 for marker in hard_markers if marker.lower() in text.lower())
    easy_score = sum(1 for marker in easy_markers if marker.lower() in text.lower())
    if hard_score >= 2 or option_length > 160 or explanation_length > 180:
        return "hard"
    if hard_score == 1:
        return "medium"
    if easy_score >= 1 and option_length < 100:
        return "easy"
    return "medium"


def infer_tags(question: dict[str, Any], chapter_no: int, knowledge_point: str, section: str) -> list[str]:
    text = question_text(question)
    tags: list[str] = []
    for tag in (knowledge_point, section):
        if tag and tag not in tags:
            tags.append(tag)
    for keyword in CHAPTER_KEYWORDS.get(chapter_no, []):
        if keyword.lower() in text.lower() and keyword not in tags:
            tags.append(keyword)
        if len(tags) >= 5:
            break
    return tags[:5]


def question_text(question: dict[str, Any]) -> str:
    parts = [str(question.get("question", "")), str(question.get("explanation", ""))]
    parts.extend(str(option) for option in question.get("options", []))
    return "\n".join(parts)


def source_ref(chapter_no: int, section: str) -> str:
    filename = CHAPTER_FILES.get(chapter_no, "")
    anchor = section.strip().replace(" ", "-")
    return f"references/{filename}#{anchor}" if filename else f"references/index.md#第{chapter_no}章"


def enrich_question(question: dict[str, Any], fallback_chapter_no: int, reference_sections: dict[int, list[str]], overwrite: bool) -> dict[str, Any]:
    chapter_no = chapter_no_from_question(question, fallback_chapter_no)
    section = infer_section(question, chapter_no, reference_sections)
    knowledge_point = infer_knowledge_point(question, chapter_no)
    enriched = dict(question)
    if overwrite or not enriched.get("question_type"):
        enriched["question_type"] = "single_choice"
    if overwrite or not enriched.get("difficulty"):
        enriched["difficulty"] = infer_difficulty(enriched)
    if overwrite or not enriched.get("section"):
        enriched["section"] = section
    if overwrite or not enriched.get("knowledge_point"):
        enriched["knowledge_point"] = knowledge_point
    if overwrite or not enriched.get("source_ref"):
        enriched["source_ref"] = source_ref(chapter_no, section)
    if overwrite or not enriched.get("tags"):
        enriched["tags"] = infer_tags(enriched, chapter_no, knowledge_point, section)
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description="Add deterministic metadata fields to chapter questions.")
    parser.add_argument("--write", action="store_true", help="Write enriched questions back to chapter files.")
    parser.add_argument("--overwrite", action="store_true", help="Regenerate metadata fields even if they already exist.")
    parser.add_argument("--chapter", type=int, default=None, help="Only enrich one chapter.")
    args = parser.parse_args()

    reference_sections = collect_reference_sections()
    files = [CHAPTERS_DIR / f"chapter_{args.chapter:02d}.json"] if args.chapter else sorted(CHAPTERS_DIR.glob("chapter_*.json"))
    changed = 0
    total = 0

    for path in files:
        if not path.exists():
            print(f"missing {path.relative_to(ROOT)}", file=sys.stderr)
            return 1
        match = re.search(r"chapter_(\d+)\.json", path.name)
        chapter_no = int(match.group(1)) if match else 0
        data = load_json(path)
        enriched = []
        for question in data:
            total += 1
            next_question = enrich_question(question, chapter_no, reference_sections, args.overwrite)
            if next_question != question:
                changed += 1
            enriched.append(next_question)
        if args.write:
            save_json(path, enriched)

    result = {"processed": total, "changed": changed, "written": args.write}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
