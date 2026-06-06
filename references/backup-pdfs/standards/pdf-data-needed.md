# 标准规范库需补充 PDF / 文本清单

- 来源：`references/backup-pdfs/manifest.json`
- 用途：补齐 `assets/questions/standards_training.json` 的标准规范专项训练库。
- 原则：优先提供文字层正常 PDF、官方网页正文、Word/Markdown 文本；扫描件需能稳定 OCR，不用低清截图。

## 这次已补

- GBT 29264-2012 信息技术服务 分类与代码：已使用 `references/pdf-skill-parsed/standards-ocr/GBT-29264-2012-信息技术服务-分类与代码.md`，结构化 8 条款。
- 中华人民共和国招标投标法：已使用 `references/pdf-skill-parsed/standards-ocr/中华人民共和国招标投标法.md`，结构化 65 条款。
- 中华人民共和国政府采购法：已使用 `references/pdf-skill-parsed/standards-ocr/中华人民共和国政府采购法.md`，结构化 72 条款。

## 本轮按要求跳过

- GBT 28827.1-2012 信息技术服务 运行维护 第1部分：通用要求：本轮按用户要求跳过，不列入当前需补数据。
- GBT 28827.2-2012 信息技术服务 运行维护 第2部分：交付规范：本轮按用户要求跳过，不列入当前需补数据。
- GBT 28827.3-2012 信息技术服务 运行维护 第3部分：应急响应规范：本轮按用户要求跳过，不列入当前需补数据。

## 还需要你提供的数据

1. GB 24405.1-2009 信息技术 服务管理 第1部分：规范
   - 当前状态：low_text，文本 0 字，中文 0 字，条款标记 0，数字标题 0。
   - 当前 PDF：`F:\备份项目\07-标准规范库\GB 24405.1-2009 信息技术 服务管理 第1部分：规范.pdf`
   - 建议提供：请提供文字层正常或高清扫描版标准 PDF；若只有扫描版，建议提供可 OCR 的 300dpi 以上 PDF。
   - 当前文本源：`references/backup-pdfs/standards/GB-24405.1-2009-信息技术-服务管理-第1部分：规范.md`
2. GB∕T 28448-2019 信息安全技术网络安全等级保护测评要求 2022-11-29 113936 1
   - 当前状态：missing_text_source，文本 0 字，中文 0 字，条款标记 0，数字标题 0。
   - 当前 PDF：`F:\备份项目\07-标准规范库\GB∕T 28448-2019 信息安全技术网络安全等级保护测评要求 2022-11-29 113936 1【耗时整理‖免费分享：CuNlOVE.Cn】.pdf`
   - 建议提供：请提供文字层正常或高清扫描版标准 PDF；若只有扫描版，建议提供可 OCR 的 300dpi 以上 PDF。
3. ISO20000-2信息技术服务管理实施指南
   - 当前状态：missing_text_source，文本 0 字，中文 0 字，条款标记 0，数字标题 0。
   - 当前 PDF：`F:\备份项目\07-标准规范库\ISO20000-2信息技术服务管理实施指南.pdf`
   - 建议提供：请提供文字层正常或高清扫描版标准 PDF；若只有扫描版，建议提供可 OCR 的 300dpi 以上 PDF。

## 接入后重建命令

```bash
python scripts/import_standards_training.py --write --format markdown
python scripts/validate_questions.py
python scripts/update_skill_summary.py
python scripts/build_search_index.py --write --format markdown
```
