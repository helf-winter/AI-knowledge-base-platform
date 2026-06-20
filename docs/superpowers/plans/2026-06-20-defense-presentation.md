# AI 企业知识库管理平台答辩 PPT Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在原模板风格和可编辑对象基础上交付 15 页 AI 企业知识库管理平台答辩 PPT。

**Architecture:** 先对 33 页模板建立完整审计，再将 15 页答辩叙事逐页映射到原模板页面。通过 artifact-tool 生成模板继承副本、编辑继承对象、渲染全套页面并执行模板保真检查。

**Tech Stack:** PowerPoint PPTX、`@oai/artifact-tool`、Node.js、模板检查与保真脚本。

---

### Task 1: 固化模板审计与内容来源

**Files:**
- Create: 外部临时工作区 `tmp/template-audit.txt`
- Create: 外部临时工作区 `tmp/source-notes.txt`
- Read: `docs/guides/答辩PPT大纲与系统演示指南.md`
- Read: `ppt/模板.pptx`

- [ ] **Step 1: 记录全部 33 页模板的章节转折、版式类型、字体和色彩规则**
- [ ] **Step 2: 将 15 页答辩事实、完成项和待完善项写入来源台账**
- [ ] **Step 3: 对照指南确认没有新增未经验证的指标、Logo、截图或客户信息**

### Task 2: 建立 15 页模板映射

**Files:**
- Create: 外部临时工作区 `tmp/template-frame-map.json`
- Create: 外部临时工作区 `tmp/deviation-log.txt`
- Create: 外部临时工作区 `tmp/template-starter.pptx`

- [ ] **Step 1: 为每个输出页选择一个原模板页，并记录叙事角色**
- [ ] **Step 2: 以 shape ID 标记需要重写或删除的继承对象**
- [ ] **Step 3: 运行 `validate_template_plan.mjs`，预期结果为映射有效**
- [ ] **Step 4: 运行 `prepare_template_starter_deck.mjs`，预期生成 15 页 starter PPTX 与预览**

### Task 3: 编辑继承页面并导出

**Files:**
- Create: 外部临时工作区 `tmp/edit-defense-deck.mjs`
- Create: `ppt/AI企业知识库管理平台答辩.pptx`

- [ ] **Step 1: 用 `PresentationFile.importPptx` 导入 starter PPTX**
- [ ] **Step 2: 按映射重写继承文本框，保留模板字体、字号、段落和位置**
- [ ] **Step 3: 对不再需要的示例图片或占位对象执行映射中声明的删除**
- [ ] **Step 4: 用 `PresentationFile.exportPptx` 导出最终 PPTX**

### Task 4: 全量视觉与结构 QA

**Files:**
- Create: 外部临时工作区 `tmp/preview/`
- Create: 外部临时工作区 `tmp/layout/final/`
- Create: 外部临时工作区 `tmp/qa/visual-qa.txt`

- [ ] **Step 1: 渲染 15 页 PNG、布局 JSON 和总览图**
- [ ] **Step 2: 逐页检查溢出、裁切、换行、对齐、页眉和章节节奏**
- [ ] **Step 3: 修正发现的问题并重新渲染受影响页面**
- [ ] **Step 4: 运行 `check_template_fidelity.mjs`，修复所有保真失败**
- [ ] **Step 5: 验证最终文件非空、页数为 15、字体和占位符检查通过**
