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
- **个人备考画像**：记录考试目标、每日可学时间、薄弱科目/章节、目标分数和学习偏好，并驱动每日计划
- **历年真题**：2017-2024 年真题结构化训练库
- **标准规范**：网络安全法、密码法、ISO20000 等专项训练
- **内部资料**：三色笔记、思维导图、论文专题、案例背诵

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

下面这些命令是底层脚本入口，主要用于开发、调试、回归测试或需要精确控制参数时使用：

```bash
# 自然语言入口
python scripts/study.py ask "今天我该学什么" --format markdown

# 查看个人备考画像
python scripts/study.py profile --format markdown

# 章节练习
python scripts/study.py start --chapters 12 --count 5

# 提交答案
python scripts/study.py submit --session practice_xxx --answers "A B C D A"

# 模拟考试
python scripts/study.py start --mode mock

# 案例分析
python scripts/study.py case start --chapters 4-24 --count 1

# 论文辅导
python scripts/study.py paper --topic 企业数字化转型

# 学习状态
python scripts/study.py dashboard --format markdown

# 薄弱分析
python scripts/study.py status --format markdown

# 错题复习
python scripts/study.py review --format markdown
```

## 个人备考画像

画像文件：`assets/profile/learner_profile.json`

当前画像记录这些内容：

- 考试目标：考试名称、目标批次、目标日期、备考策略。
- 学习时间：每日可学分钟数、工作日/周末时间、偏好学习时段。
- 当前基础：学习阶段、薄弱科目、薄弱章节、自信度。
- 学习偏好：一问一答、任务强度、偏好训练模式。
- 目标分数：综合知识、案例分析、论文三科目标分数。

画像会影响这些命令：

```bash
python scripts/study.py profile --format markdown
python scripts/study.py profile-update "我每天能学1小时，论文最弱，优先保过" --format markdown
python scripts/study.py plan --format markdown
python scripts/study.py dashboard --format markdown
python scripts/study.py sprint --days 14 --format markdown
```

例如：画像里当前每日可学时间为 75 分钟，`plan` 会自动把默认练习题量调到 8 题，并优先安排薄弱章节、案例分析和论文训练。

自然语言更新画像已经支持。直接说“我每天能学1小时，论文最弱，优先保过”时会先预览识别字段；确认要写入时，说“保存到画像：我每天能学1小时，论文最弱，优先保过”。如果内容包含身份证、账号、密码、手机号、邮箱、token 等敏感信息，写入会被拦截。

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

底层等价命令是 `python scripts/study.py ask "<你的请求>" --format markdown`，只在排查或手动测试时需要使用。

## 项目结构

```
spm-study/
├── SKILL.md                # Skill 定义文件（入口）
├── CLAUDE.md               # 项目详细说明
├── references/             # 教材内容（24 章 markdown）
├── assets/profile/         # 个人备考画像
├── assets/questions/       # 题库、作答记录、错题归档
├── scripts/                # 学习脚本（study.py 为总入口）
└── agents/                 # Codex UI 元数据
```

## 依赖

- Python 3.10+

## License

MIT
