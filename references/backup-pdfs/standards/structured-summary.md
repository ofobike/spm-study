# 标准规范结构化训练摘要

- 来源：`references/backup-pdfs/manifest.json`
- 已结构化文档：7/16
- 条款数：494
- 训练题：74
- 跳过文档：9（多为需 OCR 或文本过少）

## 已结构化文档

- ISO20000-1_信息技术服务体系要求：71 条款，10 题，`references/backup-pdfs/standards/ISO20000-1_信息技术服务体系要求.md`
- 中华人民共和国保守国家秘密法：52 条款，12 题，`references/backup-pdfs/standards/中华人民共和国保守国家秘密法.md`
- 中华人民共和国密码法：43 条款，12 题，`references/backup-pdfs/standards/中华人民共和国密码法.md`
- 中华人民共和国网络安全法：77 条款，12 题，`references/backup-pdfs/standards/中华人民共和国网络安全法.md`
- 政府采购评审专家信用管理规范：15 条款，8 题，`references/backup-pdfs/standards/政府采购评审专家信用管理规范.md`
- 桌面及外围设备服务规范：71 条款，10 题，`references/backup-pdfs/standards/桌面及外围设备服务规范.md`
- 电子信息系统机房施工及验收规范(GB50462-2008)：165 条款，10 题，`references/backup-pdfs/standards/电子信息系统机房施工及验收规范(GB50462-2008).md`

## 待 OCR / 未结构化文档

- GB 24405.1-2009 信息技术 服务管理 第1部分：规范：needs_ocr_or_low_text，文本 0 字
- GBT 28827.1-2012 信息技术服务 运行维护 第1部分：通用要求：needs_ocr_or_low_text，文本 0 字
- GBT 28827.2-2012 信息技术服务 运行维护 第2部分：交付规范：needs_ocr_or_low_text，文本 0 字
- GBT 28827.3-2012 信息技术服务 运行维护 第3部分：应急响应规范：needs_ocr_or_low_text，文本 0 字
- GBT 29264-2012 信息技术服务 分类与代码：needs_ocr_or_low_text，文本 0 字
- GB∕T 28448-2019 信息安全技术网络安全等级保护测评要求 2022-11-29 113936 1：needs_ocr_or_low_text，文本 0 字
- ISO20000-2信息技术服务管理实施指南：needs_ocr_or_low_text，文本 0 字
- 中华人民共和国招标投标法：needs_ocr_or_low_text，文本 0 字
- 中华人民共和国政府采购法：needs_ocr_or_low_text，文本 0 字

## 使用方式

```bash
python scripts/study.py standards list --format markdown
python scripts/study.py standards clauses --document 网络安全法 --limit 10 --format markdown
python scripts/study.py standards start --document ISO20000 --count 5 --format markdown
python scripts/study.py ask "给我出5道网络安全法标准规范题" --format markdown
```

> 注意：标准规范训练题是专项训练题，不是历年真题。
