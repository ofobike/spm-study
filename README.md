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

```bash
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
python scripts/study.py dashboard

# 薄弱分析
python scripts/study.py status

# 错题复习
python scripts/study.py review
```

## 项目结构

```
spm-study/
├── SKILL.md                # Skill 定义文件（入口）
├── CLAUDE.md               # 项目详细说明
├── references/             # 教材内容（24 章 markdown）
├── assets/questions/       # 题库、作答记录、错题归档
├── scripts/                # 学习脚本（study.py 为总入口）
└── agents/                 # Codex UI 元数据
```

## 依赖

- Python 3.10+

## License

MIT
