# 标准规范结构化训练摘要

- 来源：`references/backup-pdfs/manifest.json`
- 已结构化文档：10/16
- 条款数：645
- 训练题：106
- 跳过文档：6（多为需 OCR 或文本过少）
- 需补充数据清单：`references/backup-pdfs/standards/pdf-data-needed.md`

## 已结构化文档

- GBT 29264-2012 信息技术服务 分类与代码：8 条款，8 题，pdf_skill_ocr，`references/pdf-skill-parsed/standards-ocr/GBT-29264-2012-信息技术服务-分类与代码.md`
- ISO20000-1_信息技术服务体系要求：73 条款，10 题，backup_pdf_text，`references/backup-pdfs/standards/ISO20000-1_信息技术服务体系要求.md`
- 中华人民共和国保守国家秘密法：53 条款，12 题，backup_pdf_text，`references/backup-pdfs/standards/中华人民共和国保守国家秘密法.md`
- 中华人民共和国密码法：44 条款，12 题，backup_pdf_text，`references/backup-pdfs/standards/中华人民共和国密码法.md`
- 中华人民共和国招标投标法：65 条款，12 题，pdf_skill_ocr，`references/pdf-skill-parsed/standards-ocr/中华人民共和国招标投标法.md`
- 中华人民共和国政府采购法：72 条款，12 题，pdf_skill_ocr，`references/pdf-skill-parsed/standards-ocr/中华人民共和国政府采购法.md`
- 中华人民共和国网络安全法：79 条款，12 题，backup_pdf_text，`references/backup-pdfs/standards/中华人民共和国网络安全法.md`
- 政府采购评审专家信用管理规范：15 条款，8 题，backup_pdf_text，`references/backup-pdfs/standards/政府采购评审专家信用管理规范.md`
- 桌面及外围设备服务规范：71 条款，10 题，backup_pdf_text，`references/backup-pdfs/standards/桌面及外围设备服务规范.md`
- 电子信息系统机房施工及验收规范(GB50462-2008)：165 条款，10 题，backup_pdf_text，`references/backup-pdfs/standards/电子信息系统机房施工及验收规范(GB50462-2008).md`

## 待 OCR / 未结构化文档

- GB 24405.1-2009 信息技术 服务管理 第1部分：规范：low_text，文本 0 字；需要：请提供文字层正常或高清扫描版标准 PDF；若只有扫描版，建议提供可 OCR 的 300dpi 以上 PDF。
- GBT 28827.1-2012 信息技术服务 运行维护 第1部分：通用要求：missing_text_source，文本 0 字；本轮按用户要求跳过。
- GBT 28827.2-2012 信息技术服务 运行维护 第2部分：交付规范：missing_text_source，文本 0 字；本轮按用户要求跳过。
- GBT 28827.3-2012 信息技术服务 运行维护 第3部分：应急响应规范：low_text，文本 0 字；本轮按用户要求跳过。
- GB∕T 28448-2019 信息安全技术网络安全等级保护测评要求 2022-11-29 113936 1：missing_text_source，文本 0 字；需要：请提供文字层正常或高清扫描版标准 PDF；若只有扫描版，建议提供可 OCR 的 300dpi 以上 PDF。
- ISO20000-2信息技术服务管理实施指南：missing_text_source，文本 0 字；需要：请提供文字层正常或高清扫描版标准 PDF；若只有扫描版，建议提供可 OCR 的 300dpi 以上 PDF。

## 使用方式

```bash
python scripts/study.py standards list --format markdown
python scripts/study.py standards clauses --document 网络安全法 --limit 10 --format markdown
python scripts/study.py standards start --document ISO20000 --count 5 --format markdown
python scripts/study.py ask "给我出5道网络安全法标准规范题" --format markdown
```

> 注意：标准规范训练题是专项训练题，不是历年真题。
