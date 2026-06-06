# 系统规划与管理师学习助手

软考高级「系统规划与管理师」（2025年第2版新大纲）备考学习助手。

## 功能

- **教材查询**：24章完整知识点检索，关键词匹配定位
- **章节练习**：1680 道选择题（每章 70 题），支持按章节/难度/知识点筛选
- **案例分析**：62 个案例题（273 个子问题），覆盖重点章节
- **论文辅导**：论文框架生成、五维评分、草稿批改
- **模拟考试**：按真实考试比例抽题，限时 150 分钟
- **错题归档**：艾宾浩斯遗忘曲线复习提醒
- **薄弱分析**：知识点掌握度、错题根因、专项题单
- **学习驾驶舱**：进度总览、备考成熟度评分、冲刺计划
- **个人备考画像**：记录考试目标、每日可学时间、薄弱科目/章节、目标分数和学习偏好，并结合最近作答、案例和论文评分动态校准每日计划
- **历年真题**：2017-2024 年真题结构化训练库
- **标准规范**：网络安全法、密码法、ISO20000 等专项训练
- **内部资料**：三色笔记、思维导图、论文专题、案例背诵
- **PDF 增强解析**：使用 `D:\表\pdf-skill` 解析 F 盘历年真题和模拟题 PDF，增强文本保存在 `references/pdf-skill-parsed/`

## 考试科目

| 科目 | 题型 | 重点章节 |
|------|------|----------|
| 综合知识 | 75 道选择题 | 全部 24 章 |
| 案例分析 | 主观题 | 第 4-24 章 |
| 论文 | 论文 | 第 4-17 章 |

## 快速开始

安装并启用这个 Skill 后，日常使用不需要手动输入 `python scripts/study.py ...`。直接在 Codex 里提问即可，例如：

```text
今天我该学什么？
查看我的备考画像
保存到画像：我每天能学1小时，论文最弱，优先保过
根据我的画像安排今天学习
给我14天冲刺计划
给我出5道第12章正式入库题
开始第12章正式案例背诵训练
全资料检索 服务目录设计
我的答案是 A B C D A
```

如果 Skill 没有自动触发，可以把问题说得更明确一点，例如“使用 spm-study 帮我安排今天学习”。

下面这些命令是底层脚本入口，主要用于开发、调试、回归测试或需要精确控制参数时使用。`scripts/study.py` 默认输出 Markdown；需要机器读取结构化结果时，显式加 `--format json`。

```bash
# 自然语言入口
python scripts/study.py ask "今天我该学什么"

# 查看个人备考画像
python scripts/study.py profile

# 章节练习
python scripts/study.py start --chapters 12 --count 5

# 只预览出题，不写入 session 文件
python scripts/study.py start --chapters 12 --count 5 --dry-run

# 提交答案
python scripts/study.py submit --session practice_xxx --answers "A B C D A"

# 模拟考试
python scripts/study.py start --mode mock

# 案例分析
python scripts/study.py case start --chapters 4-24 --count 1

# 论文辅导
python scripts/study.py paper --topic 企业数字化转型

# 学习状态
python scripts/study.py dashboard

# 薄弱分析
python scripts/study.py status

# 错题复习
python scripts/study.py review
```

## 个人备考画像

画像文件：`assets/profile/learner_profile.json`

当前画像记录这些内容：

- 考试目标：考试名称、目标批次、目标日期、备考策略。
- 学习时间：每日可学分钟数、工作日/周末时间、偏好学习时段。
- 当前基础：学习阶段、薄弱科目、薄弱章节、自信度。
- 学习偏好：一问一答、任务强度、偏好训练模式。
- 目标分数：综合知识、案例分析、论文三科目标分数。

画像会影响这些命令；其中 `profile` 会展示静态画像和动态校准，`plan` / `dashboard` 会把最近错题、低分章节、案例/论文评分纳入任务排序：

```bash
python scripts/study.py profile
python scripts/study.py profile-update "我每天能学1小时，论文最弱，优先保过"
python scripts/study.py plan
python scripts/study.py dashboard
python scripts/study.py sprint --days 14
```

例如：画像里当前每日可学时间为 75 分钟，`plan` 会自动把默认练习题量调到 8 题，并优先安排薄弱章节、案例分析和论文训练；如果最近作答集中错在某个知识点或主观题评分偏低，会把这些动态薄弱项提前。

自然语言更新画像已经支持。直接说“我每天能学1小时，论文最弱，优先保过”时会先预览识别字段；确认要写入时，说“保存到画像：我每天能学1小时，论文最弱，优先保过”。如果内容包含身份证、账号、密码、手机号、邮箱、token 等敏感信息，写入会被拦截。

动态校准只读取 `assets/questions/progress.json` 和 `assets/questions/archive.json`，不会把身份证、账号、密码、联系方式等敏感信息写入画像；作答记录不足时会显示待校准提示，不会凭空判断薄弱项。

## 预览与记录边界

- `--dry-run` 或 `--no-write-session`：用于开始训练类命令，只预览题目和 session id，不写入 `assets/questions/sessions/`，因此不能直接提交答案。
- `--no-record`：用于提交答案、案例或论文评分时只批改不入学习进度；自然语言 `ask --no-record` 也会避免自动创建 session 或写入画像。

## 一问一答触发提示词

安装成 Skill 后，优先直接这样问：

| 场景 | 直接提问 |
|------|----------|
| 查看画像 | 查看我的备考画像 |
| 预览画像更新 | 我每天能学1小时，论文最弱，优先保过 |
| 保存画像更新 | 保存到画像：我每天能学1小时，论文最弱，优先保过 |
| 更新学习时间 | 更新画像：我工作日能学1小时，周末能学2小时 |
| 更新考试目标 | 保存到画像：目标批次是2026年下半年，优先保过 |
| 查看设置 | 我的学习设置是什么？ |
| 查看目标 | 我的备考目标是什么？ |
| 今日学习 | 今天我该学什么？ |
| 个性化计划 | 根据我的画像安排今天学习 |
| 每日计划 | 给我安排今日计划 |
| 冲刺计划 | 给我14天冲刺计划 |
| 薄弱项冲刺 | 根据我的薄弱项做冲刺安排 |
| 正式题训练 | 给我出5道第12章正式入库题 |
| 案例训练 | 开始第12章正式案例背诵训练 |
| 冲刺资料训练 | 练5个130个活动 |
| 全资料检索 | 全资料检索 服务目录设计 |
| 查标准规范 | 查资料 ISO20000 服务级别管理 |
| 提交答案 | 我的答案是 A B C D A |

底层等价命令是 `python scripts/study.py ask "<你的请求>"`，只在排查或手动测试时需要使用；需要 JSON 时再加 `--format json`。

## 项目结构

```
spm-study/
├── SKILL.md                # Skill 定义文件（入口）
├── CLAUDE.md               # 项目详细说明
├── references/             # 教材内容（24 章 markdown）
├── assets/router_examples.json # 自然语言路由回归样例表
├── assets/profile/         # 个人备考画像
├── assets/questions/       # 题库、作答记录、错题归档
├── scripts/                # 学习脚本（study.py 为 CLI 总入口）
└── agents/                 # Codex UI 元数据
```

`scripts/study.py` 保留极薄 CLI 启动入口；拆出的学习助手内部模块集中放在 `scripts/study_modules/`：

- `scripts/study_modules/common.py`：会话路径、dry-run、命令展示、JSON 简化、文本规范化和到期复习条目等通用工具。
- `scripts/study_modules/settings.py`：路径常量、默认输出、论文主题、评分/质量规则常量。
- `scripts/study_modules/cli.py`：argparse 命令注册、子命令参数和默认输出格式。
- `scripts/study_modules/profile.py`：个人备考画像、画像自然语言更新、动态画像校准。
- `scripts/study_modules/router.py`：`ask` 自然语言意图识别和高风险表达边界。
- `scripts/study_modules/ask.py`：自然语言请求执行编排、结果组合和 Markdown 渲染。
- `scripts/study_modules/materials.py`：考试指南、内部资料、VIP/冲刺资料、候选题和备份 PDF 入口。
- `scripts/study_modules/mastery.py`：知识点掌握度、覆盖率统计和专项补练建议。
- `scripts/study_modules/session_flow.py`：`start`/`submit`/`review`/`continue`/`drill` 练习会话闭环。
- `scripts/study_modules/case.py`：正式案例训练、案例渲染、主观题自动估分和提交记录。
- `scripts/study_modules/paper.py`：论文选题训练、内部论文专题参考、草稿评分和提交记录。
- `scripts/study_modules/past_exam.py`：历年真题选择题、案例、论文题目训练入口。
- `scripts/study_modules/standards.py`：标准规范列表、条款检索和专项训练入口。
- `scripts/study_modules/quality.py`：题库质量审计、自动修复预览和安全修复规则。
- `scripts/study_modules/reports.py`：学习状态、每日计划、驾驶舱、成熟度评分、周/月报和冲刺计划。
- `scripts/study_modules/search_training.py`：全资料检索、冲刺资料训练库、背诵卡/候选题/案例采分点训练。
- `scripts/study_modules/regression.py`：内置 smoke/regression 用例、路由样例回归和 Skill 摘要新鲜度检查。

自然语言路由的高风险表达维护在 `assets/router_examples.json`。新增或调整 `ask` 路由时，先把“真题/候选题/查资料/画像写入”等边界样例补进这里，再运行 regression。

`SKILL.md` 的“当前资产”统计块由 `scripts/update_skill_summary.py` 自动生成。更新题库、真题、标准规范、VIP、冲刺资料或检索索引后，运行：

```bash
python scripts/update_skill_summary.py
python scripts/update_skill_summary.py --check
```

F 盘备份 PDF 的增强解析优先使用本机 `D:\表\pdf-skill\parse_pdf_compare.py`。当前已把 21 个历年真题 PDF 和 24 个模拟题 PDF 解析为 Markdown，结果索引见 `references/pdf-skill-parsed/index.md`；`diagnostics/` 仅保存 2023 问题 PDF 的多解析器对比报告，不纳入全资料检索。

常用维护命令：

```powershell
python D:\表\pdf-skill\parse_pdf_compare.py doctor --format pdf --json
python D:\表\pdf-skill\parse_pdf_compare.py batch "F:\备份项目\2023年上半年" --parser pymupdf4llm --format md --output-dir "E:\AI\Skill\spm-study\spm-study\references\pdf-skill-parsed\past-exams-pymupdf4llm\2023年上半年"
python scripts\build_search_index.py --write --format markdown
```

## 依赖

- Python 3.10+

## License

MIT
