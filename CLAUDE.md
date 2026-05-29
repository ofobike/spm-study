# 系统规划与管理师学习助手

软考高级「系统规划与管理师」（2025年第2版新大纲）备考学习助手 Skill。

## 项目结构

```
spm-study/
├── SKILL.md                          # Skill 定义文件（入口，功能描述和工作流程）
├── CLAUDE.md                         # 本文件
├── agents/openai.yaml                # Codex UI 元数据
├── references/                       # 教材内容（24章完整 markdown）
│   ├── index.md                      # 章节索引 + 关键词映射
│   ├── 第1章_信息系统与信息技术发展.md
│   ├── ...
│   └── 第24章_法律法规和标准规范.md
├── assets/questions/                 # 练习题库
    ├── config.json                   # 自动化脚本统一配置
    ├── index.json                    # 题目统计索引
    ├── archive.json                  # 错题归档 + 复习计划
    ├── progress.json                 # 完整作答记录、案例/论文提交记录和统计
    ├── sessions/                     # 练习和模拟考试 session
    ├── past_exams.json               # 2017-2024 历年真题结构化训练库
    ├── standards_training.json       # 07 标准规范库结构化训练库
    └── chapters/                     # 按章节分类的练习题（每章70题，共1680题）
        ├── chapter_01.json
        ├── ...
        └── chapter_24.json
├── references/zfx/                   # ZFX 全程班 OCR 提取结果（由 extract_zfx.py 生成）
│   ├── yibentong.md                  # 一本通 OCR 文本
│   ├── homework.md                   # 课后作业 OCR 文本
│   ├── morning.md                    # 晨读默写本 OCR 文本
│   ├── essay.md                      # 论文集 OCR 文本
│   ├── essay_mock.md                 # 论文模拟题 OCR 文本
│   └── case.md                       # 案例通 OCR 文本
├── references/internal/              # 2025新版内部资料索引和按需抽取文本
│   ├── index.md                      # 内部资料分类索引
│   ├── manifest.json                 # 结构化文件清单
│   ├── guide/                        # 学习指南：考试安排、学习建议、分值预测
│   ├── syllabus/                     # 大纲分析：考试范围、新老教材对比
│   ├── three-color-notes/            # 1-24章三色笔记抽取文本和章节导航
│   ├── mindmaps/                     # 1-24章思维导图抽取文本/SVG和章节导航
│   ├── paper-special/                # 论文专题抽取文本
│   ├── case-special/                 # 案例专题有答案/无答案抽取文本
│   ├── chapter-practice/             # 章节习题候选题源抽取文本
│   ├── vip-materials/                # F:\备份项目\vip材料 索引和精选抽取文本
│   └── sprint-materials/             # F:\备份项目 冲刺资料索引和精选抽取文本
└── scripts/
    ├── study.py                      # 学习闭环总入口（自然语言路由、连续答题、继续学习、掌握度、专项题单、错题根因、案例/论文复评、报告、回归、冲刺、成熟度、驾驶舱、审计/修复）
    ├── practice.py                   # 生成章节练习
    ├── mock_exam.py                  # 生成模拟考试
    ├── grade_answers.py              # 批改答案并可写入记录
    ├── due_review.py                 # 查询/标记到期复习
    ├── analyze_weakness.py           # 薄弱章节分析
    ├── enrich_question_metadata.py   # 生成题目元数据
    ├── import_standards_training.py  # 07 标准规范库条款和专项题结构化脚本
    ├── import_vip_materials.py       # VIP补充资料索引和精选抽取脚本
    ├── import_sprint_materials.py    # 冲刺补充资料索引和精选抽取脚本
    ├── validate_questions.py         # 题库、案例题、真题库、标准规范训练库和统计索引校验脚本
    ├── extract_zfx.py                # ZFX 全程班 PDF OCR 提取脚本
    └── import_internal_materials.py  # 内部资料索引和按需文本抽取脚本
```

## 外部参考资料（ZFX 全程班）

郑房新老师 2025 年第 2 版系统规划与管理师全程班资料，存放路径：`F:\备份项目\1、2025第2版 ZFX全程班\`

### 电子资料清单

| 资料 | 子路径 | 页数 | 用途 |
|------|--------|------|------|
| 一本通 V2.1 | `0 电子资料/__001-一本通/` | 795页 | 直播课件合集，24章核心知识点 |
| 课后作业 V1.3 | `0 电子资料/__002-课后作业/` | 293页 | 按章节练习题（有答案） |
| 晨读默写本 V1.2 | `0 电子资料/__004-晨读默写本/` | 98页 | 1-24章填空式背诵（有答案） |
| 论文集 V2.1 | `0 电子资料/__005-论文集/` | 114页 | 论文基础知识、题目和范文 |
| 论文模拟题 V1.3 | `0 电子资料/__005-论文集/` | 63页 | 论文模拟练习题 |
| 案例通 V1.2 | `0 电子资料/__006-案例通/` | 81页 | 案例分析专项（有答案） |

### 视频课程

| 类型 | 子路径 | 集数 | 讲师 |
|------|--------|------|------|
| 基础精讲 | `1 基础精讲视频（持续更新中）/` | 68+集（第1-18章） | 郑房新、苏苏 |
| 论文课 | `2 论文课（持续更新中）/` | 1+集 | 郑房新 |

### OCR 提取

所有 ZFX PDF 均为扫描图片，需 OCR 提取文字。使用 `scripts/extract_zfx.py` 提取，结果保存到 `references/zfx/` 目录。

```bash
python scripts/extract_zfx.py --list                              # 列出所有资料
python scripts/extract_zfx.py --source morning                    # 提取晨读默写本
python scripts/extract_zfx.py --source homework                   # 提取课后作业
python scripts/extract_zfx.py --source case                       # 提取案例通
python scripts/extract_zfx.py --source essay                      # 提取论文集
python scripts/extract_zfx.py --source yibentong --pages 1-50     # 提取一本通前50页
python scripts/extract_zfx.py                                    # 提取全部资料
```

## 内部参考资料（2025 新版）

本地内部资料路径：`F:\备份项目\00-25年新版内部资料（持续更新中）\2025高级系规备考资料`

### 分类

| 分类 | 输出位置 | 用途 |
|------|----------|------|
| 学习指南 | `references/internal/guide/` | 考试安排、科目规则、学习建议和分值预测 |
| 教材与大纲 | `references/internal/syllabus/` | 大纲分析、考试范围、新老教材对比 |
| 三色笔记 | `references/internal/three-color-notes/` | 1-24章高频知识点补充，含章节导航 |
| 思维导图 | `references/internal/mindmaps/` | 1-24章知识结构导航，含第24章SVG资源 |
| 章节习题 | `references/internal/chapter-practice/` | 千题闯关候选题源，已筛选 480 道正式入库，剩余候选题继续保留在 `structured/` |
| 案例专题 | `references/internal/case-special/` | 有答案版/无答案版案例背诵训练，已筛选 24 个正式背诵案例入库，剩余采分点保留在 `structured/` |
| 论文专题 | `references/internal/paper-special/` | 论文建议、框架格式和范文 |

### 导入命令

```bash
python scripts/import_internal_materials.py --source index
python scripts/import_internal_materials.py --source paper --extract-text
python scripts/import_internal_materials.py --source case --extract-text
python scripts/import_internal_materials.py --source questions --extract-text
```

导入策略：先索引，再小批量抽取。学习指南和大纲分析已经结构化为 markdown/json，并接入 `study.py exam-guide`、每日计划、驾驶舱和冲刺计划。论文专题可作为训练参考；章节习题和案例专题已完成一轮正式筛选入库，当前正式题库为 1680 道章节题（每章 70 道）和 62 个案例题（273 个子问题）。若新增抽取范围，先确认文件大小、是否可复制文本、是否需要 OCR，再更新 `references/internal/index.md` 和 `manifest.json`。

## 教材体系（24章）

| 篇 | 章节 | 考试重点 |
|----|------|----------|
| 基础篇 | 1-3章 | 选择题：概念定义和分类 |
| 方法篇 | 4-10章 | 选择题：各类系统规划方法 |
| 实践篇 | 11-17章 | 选择题+案例：IT服务管理实践 |
| 能力篇 | 18-23章 | 案例场景和行业规划补充 |
| 法规与标准 | 24章 | 选择题：法律法规和标准规范 |

## 考试科目

| 科目 | 题型 | 重点章节 |
|------|------|----------|
| 综合知识 | 选择题 | 全部24章 |
| 案例分析 | 主观题 | 第4-24章 |
| 论文 | 论文 | 第4-17章（新版大纲优先范围） |

## Skill 工作流程

### 1. 教材查询
- 根据用户问题关键词，通过 `references/index.md` 的关键词映射定位章节
- 读取对应章节 markdown 文件，搜索相关内容
- 给出总结答案并引用原文来源（章节和具体部分）

### 2. 练习题
- 优先使用 `scripts/study.py start` 生成章节练习并保存 session
- 用户作答后使用 `scripts/study.py submit` 给出解析
- 用户只说“我的答案是 A B C D”时，使用 `scripts/study.py ask` 自动提交最近未完成 session
- 用户说“继续刚才/继续上次”时，使用 `scripts/study.py continue`
- 默认完整作答写入 `progress.json`，答错题写入 `archive.json`

### 3. 错题归档与到期复习检查
- 错题记录到 `archive.json` 的 `archive` 数组，完整作答历史记录到 `progress.json`
- 每条错题记录：题目ID、章节、答错时间、错误次数
- 复习间隔基于艾宾浩斯遗忘曲线：第1天、第3天、第7天、第14天、第30天
- 当用户询问复习内容时，使用 `scripts/study.py review` 检查 `archive.json` 中需要复习的错题
- 本 Skill 不负责后台自动推送；只有在被调用时检查到期复习内容

### 4. 模拟考试
- 使用 `scripts/study.py start --mode mock` 从题库随机抽取 75 道题，模拟真实考试
- 按 `assets/questions/config.json` 的章节比例分配：基础篇9题、方法篇21题、实践篇21题、能力篇18题、法规篇6题
- 限时 150 分钟，评分并给出解析
- 详见 `assets/questions/mock_exam.md`
- 当前章节选择题未设置难度字段，综合知识模拟按章节比例抽题，不按难度比例抽题

### 5. 案例分析练习
- 从 `assets/questions/case_studies.json` 读取案例题
- 每个案例包含场景描述 + 3-5 道子问题
- 覆盖第 12、17-23 章（案例分析重点章节）
- `scripts/study.py case submit` 支持选择题自动批改和 short_answer 主观题估分
- 主观题评分输出 matched_points、missing_points、keyword_coverage、term_coverage、rubric 分项和二次补答建议
- rubric 覆盖采分点、关键术语、问题定位、措施可执行性、量化指标、结构完整性和答题充分度
- 同一个案例 session 多次提交会记录 attempt_no，并显示较上一轮的分数提升；测试时使用 `--no-record`

### 6. 薄弱环节分析
- 使用 `scripts/study.py status` 读取 `progress.json` 和 `archive.json`
- 如果没有完整作答记录，则按错题数量、错误次数和章节权重识别薄弱章节
- 只有具备完整作答记录时，才统计各章正确率
- 根据正确率给出个性化复习建议
- 详见 `assets/questions/weak_analysis.md`

### 7. 论文辅导
- 使用 `scripts/study.py paper --topic <主题>` 生成论文训练闭环
- 优先支持新版大纲第4-17章主题，也保留智慧城市、智慧园区、数字乡村、企业数字化转型、智能制造、新型消费作为补充场景
- 输出论文题目、摘要框架、正文结构、可用知识点、内部论文专题参考、常见扣分点、自评清单和后续练习命令
- 使用 `scripts/study.py paper-ref --topic <主题> --scenario 政务|医院|制造` 查看内部五维评分、框架格式和范文路径
- 使用 `scripts/study.py paper submit --topic <主题> --draft <文件>` 对论文草稿评分
- 评分维度：摘要、背景职责、规划架构、实施治理、主题知识点、效果改进；输出 75 分制估算和内部五维评分参考
- 多次提交同一主题会记录论文轮次，并输出较上一稿的分数和篇幅变化；测试时使用 `--no-record`

### 8. 知识点覆盖率
- 使用 `scripts/study.py coverage` 读取题库元数据和 `progress.json`
- 输出已练/未练知识点、覆盖率、低正确率知识点和建议补练命令
- 进度为空时不制造虚假薄弱点，只提示覆盖率为0并推荐先做章节练习

### 9. 知识点掌握度、专项题单与错题根因
- 使用 `scripts/study.py mastery` 计算每个知识点 0-100 掌握度
- 掌握度分为未接触、初学、不稳定、已掌握、精通
- 评分依据包括正确率、练习次数、最近表现和错题惩罚
- 使用 `scripts/study.py drill` 按薄弱知识点生成个人化专项题单
- 使用 `scripts/study.py root-cause` 将错题归因为审题、概念、场景迁移、流程顺序或辨析不足

### 10. 学习驾驶舱
- 使用 `scripts/study.py dashboard` 汇总当前学习状态
- 输出已答题、正确率、错题到期、覆盖率、平均掌握度、掌握度分布、薄弱章节、题库质量和今日建议

### 11. 自然语言路由
- 使用 `scripts/study.py ask "<自然语言请求>"` 识别意图并执行常见学习动作
- 支持今日学习、继续学习、连续答题、出题、专项题单、掌握度、错题根因、错题、案例、论文、覆盖率、审计、题库修复、周报/月报/考前诊断、回归测试、冲刺和成熟度

### 12. 冲刺备考与成熟度评分
- 使用 `scripts/study.py readiness` 输出备考成熟度评分
- 使用 `scripts/study.py sprint --days 14` 生成冲刺计划
- 成熟度维度包括覆盖率、掌握度、正确率、练习量、错题复习、案例提交、论文提交和模拟考试

### 13. 题库质量审计与修复
- 使用 `scripts/study.py audit` 只读检查题库质量
- 检查答案分布偏斜、难度失衡、解析过短、弱 knowledge_point、重复选项和模板化干扰项
- 审计只报告问题，不自动修改题库
- 使用 `scripts/study.py fix-quality` 预览保守修复，确认后使用 `--write`
- `--fix-options` 修模板化干扰项，`--rebalance-answers` 重排选项降低答案偏斜，`--rebalance-difficulty` 调整 hard 难度比例

### 14. 标准规范专项训练
- 07 标准规范库原始 PDF 索引在 `references/backup-pdfs/`，结构化训练资产在 `assets/questions/standards_training.json`
- 当前已结构化 7 个文档、494 条条款、74 道专项训练题；摘要见 `references/backup-pdfs/standards/structured-summary.md`
- 使用 `scripts/study.py standards list` 查看可训练文档和待 OCR 文档
- 使用 `scripts/study.py standards clauses --document 网络安全法` 查看条款摘要
- 使用 `scripts/study.py standards start --document ISO20000 --count 5` 生成标准规范专项训练 session
- 自然语言支持“给我出5道网络安全法标准规范题”“查看密码法条款”
- 标准规范训练题由条款生成，不是历年真题；答题提交走 `scripts/study.py submit` 和 `ask 我的答案是...`
- 更新该库时运行 `python scripts/import_standards_training.py --write --format markdown`，再跑 `validate_questions.py` 和 `regression`

### 15. 学习报告与自动回归
- 使用 `scripts/study.py report --period weekly|monthly|exam` 生成周报、月报或考前诊断
- 报告汇总驾驶舱、备考成熟度、掌握度、错题根因和下一步行动
- 使用 `scripts/study.py regression` 做自动回归测试
- regression 覆盖审计、驾驶舱、掌握度、成熟度、报告、内部资料、论文专题参考、自然语言路由、案例无记录评分和论文无记录评分
- 回归、演示、测试提交必须加 `--no-record`，避免污染 `progress.json` 和 `archive.json`

### 16. 内部资料使用
- 用户问“内部资料/2025新版资料/论文专题/案例背诵/千题闯关/三色笔记/思维导图”时，先看 `references/internal/index.md`
- 用户问“考试时间/考试科目/学习指南/大纲分析/分值预测/章节重点”时，使用 `scripts/study.py exam-guide --format markdown`
- 用户问“三色笔记/背诵笔记/高频笔记/思维导图/知识结构/章节速览”时，使用 `scripts/study.py internal --kind notes|mindmap --chapter <n> --format markdown`
- 用户问“VIP材料/VIP理论必背/一本通/VIP分章节练习题”时，使用 `scripts/study.py vip --kind all|theory-core|chapter-practice-answer|comprehensive --format markdown`
- 用户问“冲刺资料/金色考点/记忆口诀/临考押题/综合模考/关键成功因素/风险控制/130个活动/马军规划冲刺资料”时，使用 `scripts/study.py sprint-materials --kind all|gold-points|mnemonic|mock-exam|csf-risk|activities|sprint-guide --format markdown`
- 用户问“千题闯关/候选题/内部习题/新版习题”且只是预览资料时，使用 `scripts/study.py candidate --chapter <n> --count 5 --format markdown`
- 用户问“正式入库章节题/正式题库练习/用新版习题正式练习”时，使用 `scripts/study.py start --chapters <n> --tag 正式入库 --count 5 --format markdown`
- 用户问“案例背诵/案例默写/采分点背诵/案例采分点”且只是看采分点时，使用 `scripts/study.py recite --chapter <n> --count 5 --format markdown`
- 用户问“正式案例背诵训练/正式采分点训练/按案例题方式练案例专题”时，使用 `scripts/study.py case start --chapters <n> --source recitation --count 1 --format markdown`
- 每日计划、驾驶舱和冲刺计划应读取 `references/internal/guide/exam-guide.json` 和 `references/internal/syllabus/syllabus-analysis.json`
- 论文训练可读取 `references/internal/paper-special/`，再结合 `scripts/study.py paper`、`paper-ref` 或 `paper submit`
- 历年真题训练使用独立库 `assets/questions/past_exams.json`，当前结构化 415 道上午选择题、20 个下午案例、13 个论文题目；使用 `scripts/study.py past-exam start|case|paper --format markdown`
- 用户说“查看真题资料/真题解析”时优先用 `backup-pdfs` 看原始 PDF 索引；用户说“练/刷/做 真题、案例真题、论文真题”时用 `past-exam` 训练入口
- 标准规范训练使用独立库 `assets/questions/standards_training.json`；用户说“练/刷/出 标准规范/法律法规/网络安全法/密码法/ISO20000”时用 `standards start`，用户说“查看条款/条文”时用 `standards clauses`
- 2024 下半年真题来自扫描 PDF OCR 抽取，已保守结构化 39 道上午题、3 个案例、2 个论文题目；不要声明 2024 上午题完整 75 道，解析警告中仍有 choice_33、choice_34、choice_42 未入库
- 新版大纲分析显示论文范围为第4-17章，案例范围为第4-24章；不要再把第18-23章默认当作论文唯一核心范围
- 案例背诵已解析出 637 条候选默写题，其中 24 个正式背诵案例已进入 `assets/questions/case_studies.json`；`recite` 继续用于采分点候选预览
- 章节习题已解析出 7248 道候选题，其中 480 道已正式入库；继续提升前必须经过去重、答案分布处理、元数据补齐、`audit`、`validate_questions.py` 和 `regression`
- VIP 材料已接入 `references/internal/vip-materials/`：索引 5 个 PDF，抽取 2 个 markdown（分章节练习题有答案版、案例论文理论必背）；一本通、无答案版、三色笔记汇总版仅索引，避免重复和体量膨胀
- 冲刺资料已接入 `references/internal/sprint-materials/`：索引 6 个 PDF，均已抽取为 markdown；记忆口诀、金色考点、24年11月综合模考、关键成功因素/风险控制、130个活动由 EasyOCR 从扫描件识别，不能称为真题或正式题库

## 注意事项

1. 回答时必须标注引用来源（章节和具体部分）
2. 新版大纲下论文优先按第4-17章准备，案例分析按第4-24章覆盖；第18-23章仍是行业规划场景的重要补充
3. 第24章法律法规是选择题常考内容
4. 基础篇和方法篇主要在选择题中考
5. 教材内容基于 PDF 原文整理，如有疑问应以原书为准
6. 修改题库、配置或统计索引后运行 `scripts/validate_questions.py`，确保资产一致
7. 修改大量题目后可运行 `scripts/enrich_question_metadata.py --write --overwrite` 重算题目元数据
8. 内部资料抽取文本可能存在排版或提取误差，应保留来源路径并以原始 PDF/DOCX 为准

## 常用命令

```bash
python scripts/study.py start --chapters 12 --count 5 --format markdown
python scripts/study.py submit --session practice_YYYYMMDD_HHMMSS_xxxxxx --answers "A B C D A" --format markdown
python scripts/study.py review --format markdown
python scripts/study.py status --format markdown
python scripts/study.py plan --format markdown
python scripts/study.py start --mode wrong --count 5 --format markdown
python scripts/study.py case start --chapters 4-24 --count 1 --format markdown
python scripts/study.py start --mode mock --format markdown
python scripts/study.py start --chapters 21 --knowledge-point 数字化转型 --difficulty hard --count 3
python scripts/study.py paper --topic 企业数字化转型 --format markdown
python scripts/study.py paper-ref --topic 信息系统规划 --scenario 政务 --format markdown
python scripts/study.py paper submit --topic 企业数字化转型 --draft draft.md --format markdown
python scripts/study.py paper submit --topic 企业数字化转型 --draft draft.md --no-record --format markdown
python scripts/study.py coverage --format markdown
python scripts/study.py mastery --format markdown
python scripts/study.py continue --format markdown
python scripts/study.py drill --count 5 --format markdown
python scripts/study.py root-cause --format markdown
python scripts/study.py dashboard --format markdown
python scripts/study.py audit --format markdown
python scripts/study.py fix-quality --format markdown
python scripts/study.py fix-quality --fix-options --rebalance-answers --rebalance-difficulty --format markdown
python scripts/study.py ask "今天我该学什么" --format markdown
python scripts/study.py ask "给我出5道第12章题" --format markdown
python scripts/study.py ask "我的答案是 A B C D A" --format markdown
python scripts/study.py ask "继续刚才的练习" --format markdown
python scripts/study.py ask "我最薄弱的知识点是什么" --format markdown
python scripts/study.py exam-guide --format markdown
python scripts/study.py internal --kind notes --chapter 12 --format markdown
python scripts/study.py internal --kind mindmap --chapter 12 --format markdown
python scripts/study.py vip --kind theory-core --format markdown
python scripts/study.py ask "查看VIP理论必背材料" --format markdown
python scripts/study.py sprint-materials --kind sprint-guide --format markdown
python scripts/study.py ask "查看金色考点冲刺资料" --format markdown
python scripts/study.py candidate --chapter 12 --count 5 --format markdown
python scripts/study.py recite --chapter 12 --count 5 --format markdown
python scripts/study.py start --chapters 12 --tag 正式入库 --count 5 --format markdown
python scripts/study.py case start --chapters 12 --source recitation --count 1 --format markdown
python scripts/study.py ask "开始第12章正式案例背诵训练" --format markdown
python scripts/study.py past-exam start --year 2022 --count 5 --format markdown
python scripts/study.py past-exam case --year 2021 --format markdown
python scripts/study.py past-exam paper --year 2022 --format markdown
python scripts/study.py ask "给我出5道2022年真题" --format markdown
python scripts/study.py ask "做2021年案例真题" --format markdown
python scripts/study.py readiness --format markdown
python scripts/study.py sprint --days 14 --format markdown
python scripts/study.py report --period weekly --format markdown
python scripts/study.py report --period exam --format markdown
python scripts/study.py regression --format markdown
python scripts/import_internal_materials.py --source index
python scripts/import_internal_materials.py --source paper --extract-text
python scripts/import_internal_materials.py --source case --extract-text
python scripts/import_internal_materials.py --source questions --extract-text
python scripts/enrich_question_metadata.py --write --overwrite
python scripts/validate_questions.py
```

## 错题记录格式

```json
{
  "question_id": "ch01_q001",
  "chapter": "第1章",
  "wrong_answer": "A",
  "correct_answer": "B",
  "timestamp": "2025-01-20T10:30:00",
  "review_count": 0,
  "next_review": "2025-01-21T10:30:00"
}
```
