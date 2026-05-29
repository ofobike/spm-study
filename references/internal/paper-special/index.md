# 2025系规论文专题索引

> 来源：`07.2025系规论文专题（第2版）`
> 用途：为 `scripts/study.py paper`、`paper submit` 和自然语言论文请求提供内部评分标准、写作框架和范文导航。

## 文件清单

| 类型 | 文件 | 用途 |
|---|---|---|
| 学习建议 | `references/internal/paper-special/01-论文学习建议与注意事项.md` | 考情判断、评分标准、扣分风险、写作避坑 |
| 框架格式 | `references/internal/paper-special/02-论文框架与格式.md` | 角色定位、摘要模板、正文结构、甲乙方视角 |
| 范文 | `references/internal/paper-special/03-信息系统规划论文-政务.md` | 政务信息化、一网通办、数据共享 |
| 范文 | `references/internal/paper-special/03-信息系统规划论文-医院.md` | 医院信息化、业务协同、医疗数据治理 |
| 范文 | `references/internal/paper-special/03-信息系统规划论文-制造.md` | 制造业数字化、生产协同、系统整合 |

## 评分标准

论文满分 75 分，训练脚本使用百分制自动评分，可按 `百分制分数 * 0.75` 粗略换算到考试分。内部资料给出的五个评分维度：

| 维度 | 权重 | 检查重点 |
|---|---:|---|
| 切合题意 | 30% | 紧扣题目关键词，回应全部子题目，避免跑题 |
| 应用深度与水平 | 20% | 教材方法论、独立工作能力、理论转实践 |
| 实践性 | 20% | 项目背景可信，本人职责明确，措施可执行 |
| 表达能力 | 15% | 逻辑清晰，表达严谨，条理分明 |
| 综合能力与分析能力 | 15% | 问题分析、方案论证、经验总结和持续改进 |

## 写作框架

- 角色逻辑：用管理思维落地规划，用规划视角优化管理。
- 摘要建议：200-300 字，覆盖项目背景、本人角色、核心方法、关键措施和量化效果。
- 正文建议：2200-2500 字左右，90 分钟左右完成。
- 正文结构：背景介绍、理论认识、具体做法、效果总结。

## 自动化接入

- 论文训练：`python scripts/study.py paper --topic 信息系统规划 --format markdown`
- 论文参考：`python scripts/study.py paper-ref --topic 信息系统规划 --scenario 政务 --format markdown`
- 论文评分：`python scripts/study.py paper submit --topic 信息系统规划 --draft draft.md --format markdown`
- 一问一答：`python scripts/study.py ask "给我信息系统规划政务论文范文参考" --format markdown`
