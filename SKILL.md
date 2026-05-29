---
name: spm-study
description: 软考高级系统规划与管理师（2025第2版）学习助手。用于系统规划与管理师、IT服务管理、ITIL、信息系统规划、云资源规划、信息安全规划、信息系统治理、项目管理、智慧城市、数字乡村、智能制造、企业数字化转型、新型消费等备考任务；支持自然语言一问一答、章节练习、正式入库题训练、2017-2024 历年真题结构化训练、案例分析主观题评分闭环、论文训练与评分、错题复习、知识点掌握度、每日计划、学习驾驶舱、冲刺计划、成熟度评分、周报/月报/考前诊断、题库质量审计修复、内部资料索引和候选资料提升入库。
---

# 系统规划与管理师学习助手

## 核心原则

优先使用 `scripts/study.py ask "<自然语言请求>" --format markdown` 作为一问一答入口；用户明确要某个功能时，也可以直接调用对应子命令。

回答教材、章节、案例、论文和内部资料问题时，标注来源章节或资料路径。不要把非真题称为“真题”，统一称为章节练习题、模拟练习题、候选题或正式入库题。

测试、演示、回归和试评分时使用 `--no-record`，避免污染 `assets/questions/progress.json`、`assets/questions/archive.json`、案例提交历史和论文提交历史。

详细章节索引、内部资料清单、命令速查和维护规则见 `references/index.md`；内部 2025 新版资料总索引见 `references/internal/index.md`；VIP 补充资料索引见 `references/internal/vip-materials/index.md`；冲刺资料索引见 `references/internal/sprint-materials/index.md`。

## 当前资产

正式题库：
- 章节选择题：1680 道，每章 70 道。
- 案例题：62 个案例，273 个子问题。
- 历年真题训练库：`assets/questions/past_exams.json`，当前结构化 415 道上午选择题、20 个下午案例、13 个论文题目；覆盖 2017-2024，其中 2024 下半年为扫描 PDF OCR 抽取版，已保守入库 39 道上午题、3 个案例、2 个论文题目，OCR 破损严重的题保留解析警告。
- 标准规范专项训练库：`assets/questions/standards_training.json`，当前结构化 7 个标准/法规文档、494 条条款、74 道专项训练题；其余 9 个标准规范 PDF 因需 OCR 或文本过少暂不生成训练题。
- 05 章节习题已筛选 480 道正式入库，剩余候选题保留在 `references/internal/chapter-practice/structured/`。
- 06 案例专题已筛选 24 个正式案例背诵题入库，剩余采分点候选材料保留在 `references/internal/case-special/structured/`。
- VIP 补充资料：`references/internal/vip-materials/`，当前索引 5 个 PDF，精选抽取 2 个 markdown：分章节练习题有答案版、案例论文理论必背；一本通、无答案练习题和三色笔记汇总版默认仅索引，避免重复和体量膨胀。
- 冲刺补充资料：`references/internal/sprint-materials/`，当前索引 6 个 PDF 且均已抽取为可读 markdown；其中记忆口诀、金色考点、综合模考、关键成功因素/风险控制和 130 个活动由 EasyOCR 识别得到，仍作为补充资料源，不自动并入正式题库。

已接入的 7 类 2025 新版资料：
- 01 学习指南：`references/internal/guide/`
- 02 教材与大纲分析：`references/internal/syllabus/`
- 03 三色笔记：`references/internal/three-color-notes/`
- 04 思维导图：`references/internal/mindmaps/`
- 05 章节习题：正式入库题 + 候选库
- 06 案例专题：正式案例背诵 + 候选采分点
- 07 论文专题：`references/internal/paper-special/`
- F盘备份 PDF：`references/backup-pdfs/`，含 2017-2024 历年真题、标准规范库和模拟题库索引；部分扫描件标记为需 OCR。

## 入口选择

自然语言学习请求：

```bash
python scripts/study.py ask "今天我该学什么" --format markdown
python scripts/study.py ask "给我出5道第12章正式入库题" --format markdown
python scripts/study.py ask "开始第12章正式案例背诵训练" --format markdown
python scripts/study.py ask "我论文写好了帮我批" --format markdown
```

章节练习与提交：

```bash
python scripts/study.py start --chapters 12 --count 5 --format markdown
python scripts/study.py start --chapters 12 --tag 正式入库 --count 5 --format markdown
python scripts/study.py submit --session <session_id> --answers "A B C D A" --format markdown
python scripts/study.py ask "我的答案是 A B C D A" --format markdown
```

历年真题训练：

```bash
python scripts/study.py past-exam start --year 2022 --count 5 --format markdown
python scripts/study.py past-exam case --year 2021 --format markdown
python scripts/study.py past-exam paper --year 2022 --format markdown
python scripts/study.py ask "给我出5道2022年真题" --format markdown
python scripts/study.py ask "做2021年案例真题" --format markdown
python scripts/study.py ask "查看2022年论文真题" --format markdown
```

标准规范专项训练：

```bash
python scripts/study.py standards list --format markdown
python scripts/study.py standards clauses --document 网络安全法 --limit 10 --format markdown
python scripts/study.py standards start --document ISO20000 --count 5 --format markdown
python scripts/study.py ask "给我出5道网络安全法标准规范题" --format markdown
python scripts/study.py ask "查看密码法条款" --format markdown
```

计划、掌握度和复习：

```bash
python scripts/study.py dashboard --format markdown
python scripts/study.py plan --format markdown
python scripts/study.py mastery --format markdown
python scripts/study.py drill --count 5 --format markdown
python scripts/study.py review --format markdown
python scripts/study.py continue --format markdown
```

案例与论文：

```bash
python scripts/study.py case start --chapters 4-24 --count 1 --format markdown
python scripts/study.py case start --chapters 12 --source recitation --count 1 --format markdown
python scripts/study.py paper --topic 信息系统规划 --format markdown
python scripts/study.py paper-ref --topic 信息系统规划 --scenario 政务 --format markdown
python scripts/study.py paper submit --topic 信息系统规划 --draft draft.md --format markdown
```

内部资料：

```bash
python scripts/study.py exam-guide --format markdown
python scripts/study.py backup-pdfs --category past-exam --format markdown
python scripts/study.py backup-pdfs --category standards --format markdown
python scripts/study.py internal --kind notes --chapter 12 --format markdown
python scripts/study.py internal --kind mindmap --chapter 12 --format markdown
python scripts/study.py vip --kind theory-core --format markdown
python scripts/study.py ask "查看VIP理论必背材料" --format markdown
python scripts/study.py sprint-materials --kind sprint-guide --format markdown
python scripts/study.py ask "查看金色考点冲刺资料" --format markdown
python scripts/study.py candidate --chapter 12 --count 5 --format markdown
python scripts/study.py recite --chapter 12 --count 5 --format markdown
```

## 决策规则

用户问考试时间、科目、分值预测、学习指南、大纲分析、章节重点时，调用 `exam-guide`。

用户问历年真题、真题解析、标准规范库、法规库、模拟题库、F盘资料时，调用 `backup-pdfs`；需要具体年份或科目时加 `--year` 或 `--subject`。

用户要练历年真题、刷某年上午选择题、做案例真题或查看论文真题时，调用 `past-exam start|case|paper`；`past_exam` 是独立正式真题训练库，不混入章节练习题库。

用户要练标准规范、刷法律法规、做网络安全法/密码法/ISO20000/GB50462 专项题时，调用 `standards start`；用户要看条款原文摘要时调用 `standards clauses`；用户只问标准规范库有哪些资料时仍调用 `backup-pdfs --category standards`。`standards_training` 是条款生成的专项训练题，不是真题。

用户问三色笔记、背诵笔记、高频笔记时，调用 `internal --kind notes`；问思维导图、知识结构、章节速览时，调用 `internal --kind mindmap`。

用户问 VIP 材料、VIP 理论必背、一本通、VIP 分章节练习题时，调用 `vip`；理论必背用 `vip --kind theory-core`，分章节练习题有答案版用 `vip --kind chapter-practice-answer`。VIP 资料当前是补充资料源，不自动等同正式题库。

用户问冲刺资料、金色考点、记忆口诀、临考押题、综合模考、关键成功因素、风险控制、130个活动或马军规划冲刺资料时，调用 `sprint-materials`；这类资料是补充资料源和候选题源，不自动称为真题或正式题库。

用户要练正式题库、新版习题正式练习、正式入库题时，调用 `start --tag 正式入库`；用户只是要看千题闯关、候选题、内部习题资料时，调用 `candidate`。

用户要正式案例背诵训练、正式采分点训练、按案例题方式练案例专题时，调用 `case start --source recitation`；用户只要看案例背诵采分点或候选默写材料时，调用 `recite`。

论文优先按新版大纲第4-17章准备；案例分析按第4-24章覆盖；第18-23章是行业规划场景的重要补充；第24章是选择题常考。

主观题和论文评分是训练估分，用于发现缺失采分点和改稿方向；不要承诺等同正式阅卷。

## 维护规则

修改题库、案例题、配置、自然语言路由、评分规则或报告逻辑后，至少运行：

```bash
python scripts/validate_questions.py
python scripts/study.py audit --format markdown
python scripts/study.py regression --format markdown
python -X utf8 C:\Users\hspcadmin\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
```

更新 07 标准规范结构化训练库时，先重建再校验：

```bash
python scripts/import_standards_training.py --write --format markdown
python scripts/validate_questions.py
python scripts/study.py regression --format markdown
```

更新 VIP 补充资料时，先索引并只抽取精选资料：

```bash
python scripts/import_vip_materials.py --write --extract selected --format markdown
python scripts/study.py vip --format markdown
```

更新冲刺补充资料时，先索引并只抽取可复制文本的精选资料；扫描 PDF 使用 `--ocr` 分批处理：

```bash
python scripts/import_sprint_materials.py --write --extract selected --format markdown
python scripts/import_sprint_materials.py --write --ocr small --format markdown
python scripts/import_sprint_materials.py --write --ocr gold-points --format markdown
python scripts/study.py sprint-materials --format markdown
```

继续提升章节习题或案例专题时，先预览再写入：

```bash
python scripts/promote_internal_materials.py --format markdown
python scripts/promote_internal_materials.py --write --questions-per-chapter 20 --case-items-per-chapter 5 --format markdown
```

写入后查看 `references/internal/formal-promotion-report.json`，并执行完整校验。不要直接把大体量 PDF 全文写入 `SKILL.md`；优先放入 `references/internal/` 并按需读取。
