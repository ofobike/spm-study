# 冲刺资料训练化索引

> 说明：本库来自冲刺资料 OCR/抽取文本，只作为背诵卡、案例采分点和模拟候选题源，不是历年真题，不自动混入正式章节题库。

## 总览

- 背诵卡：558
- 模拟选择候选题：15
- 案例采分点训练：234
- 输出：`assets\questions\sprint_training.json`

## 类型分布
- 130个活动：141
- 关键成功因素与风险控制：56
- 金色考点：188
- 记忆口诀：40
- 综合模考题：1
- 规划冲刺资料：132

## 使用方式

- `python scripts/study.py sprint-training cards --kind activities --count 5 --format markdown`
- `python scripts/study.py sprint-training start --count 5 --format markdown`
- `python scripts/study.py sprint-training case --kind csf-risk --count 3 --format markdown`
