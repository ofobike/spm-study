---
name: spm-study
description: 软考高级系统规划与管理师（2025第2版）学习助手。用于系统规划与管理师、IT服务管理、ITIL、信息系统规划、云资源规划、信息安全规划、信息系统治理、项目管理、智慧城市、数字乡村、智能制造、企业数字化转型、新型消费等备考任务；支持自然语言一问一答、全资料本地检索与来源定位、章节练习、正式入库题训练、2017-2024 历年真题结构化训练、标准规范专项训练、冲刺资料训练化、案例分析主观题评分闭环、论文训练与评分、错题复习、知识点掌握度、每日计划、学习驾驶舱、冲刺计划、成熟度评分、周报/月报/考前诊断、题库质量审计修复、内部资料索引和候选资料提升入库。
---

# 系统规划与管理师学习助手

## 核心原则

优先使用 `scripts/study.py ask "<自然语言请求>"` 作为一问一答入口；`scripts/study.py` 默认输出 Markdown，需要结构化自动化结果时显式加 `--format json`。用户明确要某个功能时，也可以直接调用对应子命令。

回答教材、章节、案例、论文和内部资料问题时，标注来源章节或资料路径。不要把非真题称为“真题”，统一称为章节练习题、模拟练习题、候选题或正式入库题。

测试、演示、回归和试评分时使用 `--no-record`，避免污染 `assets/questions/progress.json`、`assets/questions/archive.json`、案例提交历史和论文提交历史。只想预览出题或开始训练、不想写入 `assets/questions/sessions/` 时，加 `--dry-run`（别名 `--no-write-session`）。`profile`、`plan`、`dashboard` 会根据已有作答、案例和论文评分记录做动态校准；记录不足时只提示待校准，不要编造薄弱项。

详细章节索引、内部资料清单、命令速查和维护规则见 `references/index.md`；内部 2025 新版资料总索引见 `references/internal/index.md`；VIP 补充资料索引见 `references/internal/vip-materials/index.md`；冲刺资料索引见 `references/internal/sprint-materials/index.md`；冲刺资料训练化索引见 `references/internal/sprint-materials/structured-training.md`。

## 当前资产

<!-- ASSET_SUMMARY_START -->

正式题库：
- 章节选择题：1680 道，每章 70 道。
- 案例题：62 个案例，273 个子问题。
- 历年真题训练库：`assets/questions/past_exams.json`，当前结构化 466 道上午选择题、22 个下午案例、13 个论文题目；覆盖 2017-2024；其中 2024 下半年 OCR 抽取版保守入库 39 道上午题、3 个案例、2 个论文题目，OCR 破损严重的题保留解析警告（choice_33, choice_34, choice_42 未入库）。
- 标准规范专项训练库：`assets/questions/standards_training.json`，当前结构化 10/16 个标准/法规文档、645 条条款、106 道专项训练题；其余 6 个标准规范 PDF 因需 OCR 或文本过少暂不生成训练题。
- 05 章节习题已筛选 480 道正式入库，剩余候选题约 7248 道，候选题保留在 `references/internal/chapter-practice/structured/`。
- 06 案例专题已筛选 24 个正式案例背诵题入库，剩余采分点候选材料约 637 条，候选材料保留在 `references/internal/case-special/structured/`。
- VIP 补充资料：`references/internal/vip-materials/`，当前索引 5 个 PDF，精选抽取 2 个 markdown；一本通、无答案练习题和三色笔记汇总版默认仅索引，避免重复和体量膨胀。
- 冲刺补充资料：`references/internal/sprint-materials/`，当前索引 6 个 PDF，抽取 6 个 markdown；扫描件由 EasyOCR 识别，仍作为补充资料源，不自动并入正式题库。
- 全资料检索索引：`assets/search/index.json`，当前 11611 个本地资料片段，覆盖教材章节、正式题库、案例、真题、标准规范、内部资料、模拟题库、VIP、冲刺资料、训练化资产。
- 冲刺训练库：`assets/questions/sprint_training.json`，当前 558 张背诵卡、15 道自编综合模考候选选择题、234 个案例采分点训练；来自冲刺资料 OCR/抽取文本，不等同正式题库或历年真题。
- 个人备考画像：`assets/profile/learner_profile.json`，记录考试目标、每日可学时间、薄弱科目/章节、目标分数和学习偏好；最近更新 2026-06-04；`plan`、`dashboard`、`sprint` 会读取画像自动调整题量和任务优先级；自然语言“保存到画像：我每天能学1小时，论文最弱，优先保过”会走 `profile-update`。

<!-- ASSET_SUMMARY_END -->

已接入的 7 类 2025 新版资料：
- 01 学习指南：`references/internal/guide/`
- 02 教材与大纲分析：`references/internal/syllabus/`
- 03 三色笔记：`references/internal/three-color-notes/`
- 04 思维导图：`references/internal/mindmaps/`
- 05 章节习题：正式入库题 + 候选库
- 06 案例专题：正式案例背诵 + 候选采分点
- 07 论文专题：`references/internal/paper-special/`
- F盘备份 PDF：`references/backup-pdfs/`，含 2017-2024 历年真题、标准规范库和模拟题库索引；部分扫描件标记为需 OCR。
- F盘备份 PDF 增强解析：`references/pdf-skill-parsed/`，使用 `D:\表\pdf-skill\parse_pdf_compare.py` 解析；当前有 21 个历年真题 Markdown、24 个模拟题 Markdown，2023 问题 PDF 的多解析器诊断保存在 `diagnostics/`。

## 入口选择

默认触发方式：安装并启用 Skill 后，优先直接对 Codex 说自然语言；如果自动触发不准，再用底层等价命令 `python scripts/study.py ask "<你的请求>"` 排查。下面这些句子都应优先走 `ask` 路由。

### 自然语言触发大全

开始学习、计划和驾驶舱：

- “今天我该学什么？”
- “根据我的画像安排今天学习。”
- “给我安排今日计划。”
- “我今天只有30分钟，帮我安排最重要的任务。”
- “给我14天冲刺计划。”
- “给我3天冲刺计划。”
- “看学习驾驶舱。”
- “查看我的学习状态。”
- “看看我的备考成熟度。”
- “我现在离考试还差什么？”
- “生成本周学习报告。”
- “分析我的错题根因。”

个人备考画像：

- “查看我的备考画像。”
- “我的学习设置是什么？”
- “我的备考目标是什么？”
- “我每天能学1小时，论文最弱，优先保过。”
- “我工作日能学1小时，周末能学2小时。”
- “保存到画像：我每天能学1小时，论文最弱，优先保过。”
- “更新画像：目标批次是2026年下半年，优先保过。”
- “修改画像：综合知识目标55分，案例目标50分，论文目标50分。”
- “设置学习偏好：先刷选择题，再做案例。”
- “保存到画像：我晚上学习效率最高。”

章节正式题、模拟和薄弱点训练：

- “给我出5道第12章题。”
- “给我出5道第12章正式入库题。”
- “给我出10道第4到第6章正式题。”
- “按薄弱点给我出5道题。”
- “给我做一次个性化补练。”
- “开始模拟考试。”
- “只预览5道第12章题，不要写 session。”
- “不要记录这次练习，只演示一下。”
- “查看第12章知识点覆盖情况。”
- “查看我的知识点掌握度。”

提交、继续、复习和错题：

- “我的答案是 A B C D A。”
- “提交答案：A B C D A。”
- “不记录本次批改，我的答案是 A B C。”
- “继续上次练习。”
- “继续上次真题训练。”
- “继续上次标准规范训练。”
- “复习到期错题。”
- “查看错题复习。”
- “给我按错题生成5道补练。”
- “只批改不入档。”

历年真题：

- “查看2023年历年真题资料。”
- “查看2024年下半年真题资料。”
- “给我出5道2022年真题。”
- “给我出10道2023年上半年真题。”
- “做2021年案例真题。”
- “做2023年案例真题。”
- “查看2022年论文真题。”
- “查看历年论文题目。”
- “只看2024真题解析资料，不出题。”
- “查看2023上午真题解析。”

标准规范和法律法规：

- “标准规范库有哪些资料？”
- “给我出5道网络安全法标准规范题。”
- “给我出3道密码法题。”
- “给我出2道招标投标法标准规范题。”
- “给我出2道政府采购法标准规范题。”
- “给我出5道ISO20000专项题。”
- “给我出5道GB50462机房验收规范题。”
- “给我出3道GBT 29264 分类与代码题。”
- “查看网络安全法条款。”
- “查看密码法条款。”
- “查看政府采购法条款。”
- “查看ISO20000服务级别管理条款。”
- “查资料 ISO20000 服务级别管理。”

案例分析：

- “开始案例训练。”
- “开始第12章案例训练。”
- “开始第12章正式案例背诵训练。”
- “查看第12章案例背诵采分点。”
- “给我一个第12章案例题。”
- “按案例分析题方式练关键成功因素。”
- “用关键成功因素做案例采分点训练。”
- “给我3个风险控制案例采分点。”
- “我的案例答案是……帮我评分。”
- “只评分不记录这次案例答案。”

论文训练：

- “给我一个信息系统规划论文题目。”
- “给我论文训练。”
- “生成信息系统规划论文框架。”
- “给我企业数字化转型论文框架。”
- “给我信息系统规划政务论文范文参考。”
- “给我医院场景论文参考。”
- “给我制造业场景论文参考。”
- “我论文写好了帮我批。”
- “批改这篇论文草稿。”
- “只评分不记录这次论文。”

全资料检索和资料定位：

- “全资料检索 服务目录设计。”
- “查资料 第12章 服务目录设计。”
- “搜索 ISO20000 服务级别管理。”
- “哪里提到服务目录设计？”
- “在哪个资料里讲关键成功因素？”
- “查2023 信息熵。”
- “只查资料，不要出题。”
- “全资料检索 网络安全法 等级保护。”
- “查资料 运营服务和运行维护的区别。”

内部资料、VIP 和冲刺资料查看：

- “查看考试指南。”
- “查看第12章三色笔记。”
- “查看第12章思维导图。”
- “查看VIP理论必背材料。”
- “查看VIP分章节练习题有答案版。”
- “查看金色考点冲刺资料。”
- “查看记忆口诀。”
- “查看130个活动。”
- “查看关键成功因素和风险控制资料。”
- “查看马军规划冲刺资料。”
- “查看F盘标准规范库资料。”
- “查看模拟题库资料。”

冲刺资料训练化：

- “练5个130个活动。”
- “默写5个130个活动。”
- “练5个记忆口诀。”
- “背5个金色考点。”
- “刷5道综合模考候选题。”
- “用关键成功因素做案例采分点训练。”
- “用风险控制做案例采分点训练。”
- “练3个冲刺案例采分点并显示答案。”

候选题和背诵预览：

- “看5道第12章千题闯关候选题。”
- “预览第12章候选题。”
- “查看第12章案例背诵采分点。”
- “查看第12章案例采分点并显示答案。”
- “只看候选题，不要入正式题库。”

质量、覆盖和维护类自然语言：

- “审计题库质量。”
- “修复题库质量问题。”
- “只预览题库修复，不要写入。”
- “查看知识点覆盖率。”
- “查看薄弱知识点。”
- “分析错题根因。”
- “看我的备考成熟度。”

边界表达必须遵守：

- 用户说“查资料、检索、搜索、哪里提到、在哪个资料”时，只检索资料，不自动出题。
- 用户说“查看真题资料、真题解析资料”时，查 `backup-pdfs` 或增强解析资料；用户说“给我出真题、做真题”时，才进入 `past-exam` 训练。
- 用户说“候选题、模拟题、冲刺候选题、千题闯关”时，不要称为历年真题。
- 用户说“标准规范题、法律法规题、条款题”时，走 `standards`；标准规范专项题不是历年真题。
- 画像写入必须有“保存到画像、更新画像、写入画像、设置、修改”等明确写入意图；普通偏好描述只预览。
- 用户说“预览、不写 session、不要落盘”时，加 `--dry-run`；用户说“不记录、不入档、只批改”时，加 `--no-record`。
- 提到身份证、准考证、账号、密码、手机号、邮箱、token 等敏感信息时，不写入画像或长期记忆。

底层命令示例：

```bash
python scripts/study.py ask "今天我该学什么"
python scripts/study.py ask "给我出5道第12章正式入库题"
python scripts/study.py ask "全资料检索 服务目录设计"
python scripts/study.py ask "练5个130个活动"
python scripts/study.py ask "开始第12章正式案例背诵训练"
python scripts/study.py ask "我论文写好了帮我批"
```

章节练习与提交：

```bash
python scripts/study.py start --chapters 12 --count 5
python scripts/study.py start --chapters 12 --count 5 --dry-run
python scripts/study.py start --chapters 12 --tag 正式入库 --count 5
python scripts/study.py submit --session <session_id> --answers "A B C D A"
python scripts/study.py ask "我的答案是 A B C D A"
```

历年真题训练：

```bash
python scripts/study.py past-exam start --year 2022 --count 5
python scripts/study.py past-exam case --year 2021
python scripts/study.py past-exam paper --year 2022
python scripts/study.py ask "给我出5道2022年真题"
python scripts/study.py ask "做2021年案例真题"
python scripts/study.py ask "查看2022年论文真题"
```

标准规范专项训练：

```bash
python scripts/study.py standards list
python scripts/study.py standards clauses --document 网络安全法 --limit 10
python scripts/study.py standards start --document ISO20000 --count 5
python scripts/study.py ask "给我出5道网络安全法标准规范题"
python scripts/study.py ask "查看密码法条款"
```

全资料检索：

```bash
python scripts/study.py search "服务目录设计" --limit 8
python scripts/study.py search "关键成功因素" --source-type sprint_material
python scripts/study.py ask "全资料检索 ISO20000 服务级别管理"
python scripts/study.py ask "查资料 第12章 服务目录设计"
```

计划、掌握度和复习：

```bash
python scripts/study.py dashboard
python scripts/study.py profile
python scripts/study.py profile-update "我每天能学1小时，论文最弱，优先保过"
python scripts/study.py plan
python scripts/study.py mastery
python scripts/study.py drill --count 5
python scripts/study.py review
python scripts/study.py continue
```

案例与论文：

```bash
python scripts/study.py case start --chapters 4-24 --count 1
python scripts/study.py case start --chapters 12 --source recitation --count 1
python scripts/study.py paper --topic 信息系统规划
python scripts/study.py paper-ref --topic 信息系统规划 --scenario 政务
python scripts/study.py paper submit --topic 信息系统规划 --draft draft.md
```

内部资料：

```bash
python scripts/study.py exam-guide
python scripts/study.py backup-pdfs --category past-exam
python scripts/study.py backup-pdfs --category standards
python scripts/study.py internal --kind notes --chapter 12
python scripts/study.py internal --kind mindmap --chapter 12
python scripts/study.py vip --kind theory-core
python scripts/study.py ask "查看VIP理论必背材料"
python scripts/study.py sprint-materials --kind sprint-guide
python scripts/study.py ask "查看金色考点冲刺资料"
python scripts/study.py sprint-training cards --kind activities --count 5
python scripts/study.py sprint-training cards --kind mnemonic --count 5 --show-answer
python scripts/study.py sprint-training start --kind mock-exam --count 5
python scripts/study.py sprint-training case --kind csf-risk --count 3 --show-answer
python scripts/study.py ask "练5个130个活动"
python scripts/study.py ask "用关键成功因素做案例采分点训练"
python scripts/study.py candidate --chapter 12 --count 5
python scripts/study.py recite --chapter 12 --count 5
```

## 决策规则

用户问考试时间、科目、分值预测、学习指南、大纲分析、章节重点时，调用 `exam-guide`。

用户问历年真题、真题解析、标准规范库、法规库、模拟题库、F盘资料时，调用 `backup-pdfs`；需要具体年份或科目时加 `--year` 或 `--subject`。

用户要练历年真题、刷某年上午选择题、做案例真题或查看论文真题时，调用 `past-exam start|case|paper`；`past_exam` 是独立正式真题训练库，不混入章节练习题库。

用户要练标准规范、刷法律法规、做网络安全法/密码法/ISO20000/GB50462 专项题时，调用 `standards start`；用户要看条款原文摘要时调用 `standards clauses`；用户只问标准规范库有哪些资料时仍调用 `backup-pdfs --category standards`。`standards_training` 是条款生成的专项训练题，不是真题。

用户问三色笔记、背诵笔记、高频笔记时，调用 `internal --kind notes`；问思维导图、知识结构、章节速览时，调用 `internal --kind mindmap`。

用户问 VIP 材料、VIP 理论必背、一本通、VIP 分章节练习题时，调用 `vip`；理论必背用 `vip --kind theory-core`，分章节练习题有答案版用 `vip --kind chapter-practice-answer`。VIP 资料当前是补充资料源，不自动等同正式题库。

用户明确说“检索、搜索、查资料、全资料、资料里、哪里提到、在哪个资料”时，调用 `search`，必要时加 `--source-type` 或 `--chapter`；检索结果必须展示来源路径。

用户问个人画像、备考画像、学习设置、我的目标或备考目标时，调用 `profile`。`profile` 同时展示静态画像和从 `progress.json` / `archive.json` 推导的动态校准；`plan`、`dashboard` 会把最近错题知识点、动态薄弱章节、案例/论文低分记录纳入任务排序。用户说“我每天能学1小时、论文最弱、优先保过、目标批次、考试日期、学习强度”等学习偏好时，调用 `profile-update` 先预览；用户明确说“保存到画像、更新画像、写入画像、设置、修改”时才写入。不要在画像中保存身份证、准考证、账号、密码、联系方式、邮箱、token 等敏感信息；检测到敏感信息时拦截写入。

用户只是查看冲刺资料、金色考点、记忆口诀、临考押题、综合模考、关键成功因素、风险控制、130个活动或马军规划冲刺资料时，调用 `sprint-materials`；这类资料是补充资料源和候选题源，不自动称为真题或正式题库。

用户要练冲刺资料、背口诀、默写130个活动、用关键成功因素做案例采分点训练、刷综合模考候选题时，调用 `sprint-training cards|case|start`；`sprint_training` 来自 OCR/抽取文本，是训练化候选库，不混入正式章节题库或历年真题。

用户要练正式题库、新版习题正式练习、正式入库题时，调用 `start --tag 正式入库`；用户只是要看千题闯关、候选题、内部习题资料时，调用 `candidate`。

用户要正式案例背诵训练、正式采分点训练、按案例题方式练案例专题时，调用 `case start --source recitation`；用户只要看案例背诵采分点或候选默写材料时，调用 `recite`。

论文优先按新版大纲第4-17章准备；案例分析按第4-24章覆盖；第18-23章是行业规划场景的重要补充；第24章是选择题常考。

主观题和论文评分是训练估分，用于发现缺失采分点和改稿方向；不要承诺等同正式阅卷。

## 维护规则

修改题库、案例题、配置、自然语言路由、评分规则或报告逻辑后，至少运行：

```bash
python scripts/update_skill_summary.py
python scripts/validate_questions.py
python scripts/study.py audit --format markdown
python scripts/study.py regression --format markdown
python -X utf8 C:\Users\hspcadmin\.codex\skills\.system\skill-creator\scripts\quick_validate.py .
```

`scripts/study.py` 是极薄 CLI 启动入口，不再承载辅助逻辑。维护时优先把学习助手内部逻辑放到 `scripts/study_modules/`：`common.py` 放会话/dry-run/展示工具、JSON 简化、文本规范化和到期复习条目等通用工具，`settings.py` 放路径常量和论文主题配置，`cli.py` 放 argparse 命令注册，`profile.py` 放画像和动态校准，`router.py` 放自然语言意图识别，`ask.py` 放自然语言请求执行编排和渲染，`materials.py` 放考试指南、内部资料、VIP/冲刺资料、候选题和备份 PDF 入口，`mastery.py` 放知识点掌握度、覆盖率统计和专项补练建议，`session_flow.py` 放 `start`/`submit`/`review`/`continue`/`drill` 练习会话闭环，`case.py` 放正式案例训练、案例渲染和主观题评分闭环，`paper.py` 放论文选题训练、内部论文专题参考和草稿评分闭环，`past_exam.py` 放历年真题训练入口，`standards.py` 放标准规范入口，`quality.py` 放题库质量审计和自动修复预览，`reports.py` 放状态、计划、驾驶舱、成熟度、周/月报和冲刺计划，`search_training.py` 放全资料检索、冲刺资料训练库、背诵卡/候选题/案例采分点训练，`regression.py` 放内置回归测试。继续维护时保持 `python scripts/study.py ...` 命令行为不变，并用 regression 覆盖路由边界。

更新教材、题库、真题、标准规范、VIP、冲刺资料或检索索引后，先运行 `python scripts/update_skill_summary.py` 刷新 `SKILL.md` 的 `ASSET_SUMMARY` 自动块；只检查是否过期可用 `python scripts/update_skill_summary.py --check`。

新增或调整自然语言路由时，先更新 `assets/router_examples.json`；该文件维护 “真题 vs 章节练习”“候选题 vs 正式入库题”“查资料 vs 出题”“画像预览 vs 写入”等高风险表达，`regression` 会自动读取这些样例。

更新 F 盘备份 PDF 解析结果时，优先使用本机 `D:\表\pdf-skill\parse_pdf_compare.py`，不要再只依赖 `import_backup_pdfs.py` 的单一 PyMuPDF 文本层抽取。先用 `doctor` 或 `compare` 诊断问题 PDF，再用 `batch --parser pymupdf4llm --format md` 生成增强 Markdown；扫描或坏文本层 PDF 可把 `ocr-tesseract` 纳入 `compare/vote`。增强解析结果放入 `references/pdf-skill-parsed/`，`diagnostics/` 只放解析器对比报告，`build_search_index.py` 会跳过该目录。结构化入库仍需经过 `scripts/import_past_exams.py` 和 `scripts/validate_questions.py`，模拟题库不得直接称为历年真题。

```powershell
python D:\表\pdf-skill\parse_pdf_compare.py doctor --format pdf --json
python D:\表\pdf-skill\parse_pdf_compare.py compare "F:\备份项目\2023年上半年\2023.5系规划真题及解析(选择+案例）V2.4（参考答案）.pdf" --max-pages 3 --parsers markitdown,pymupdf4llm,pymupdf,pdfplumber,pdfminer,liteparse,ocr-tesseract --output-format md
python D:\表\pdf-skill\parse_pdf_compare.py batch "F:\备份项目\2023年上半年" --parser pymupdf4llm --format md --output-dir "E:\AI\Skill\spm-study\spm-study\references\pdf-skill-parsed\past-exams-pymupdf4llm\2023年上半年"
python scripts\build_search_index.py --write --format markdown
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

更新冲刺资料训练库和全资料检索索引时，先训练化再刷新检索：

```bash
python scripts/build_sprint_training.py --write --format markdown
python scripts/build_search_index.py --write --format markdown
python scripts/study.py sprint-training cards --kind activities --count 3 --format markdown
python scripts/study.py search "服务目录设计" --limit 3 --format markdown
```

继续提升章节习题或案例专题时，先预览再写入：

```bash
python scripts/promote_internal_materials.py --format markdown
python scripts/promote_internal_materials.py --write --questions-per-chapter 20 --case-items-per-chapter 5 --format markdown
```

写入后查看 `references/internal/formal-promotion-report.json`，并执行完整校验。不要直接把大体量 PDF 全文写入 `SKILL.md`；优先放入 `references/internal/` 并按需读取。
