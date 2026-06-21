# Defense AI Reference Materials Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 生成一份系统完整事实底稿和一份覆盖答辩高频问题、技术追问与质疑问题的参考回答文档，供 AI 大模型模拟答辩。

**Architecture:** 先从课题要求、当前代码、README、架构与演示文档抽取唯一事实口径，形成系统知识底稿；再按业务、技术、权限、AI、部署、测试和质疑等主题生成答辩题库。两份文档均明确区分已完成、基础版和待完善能力。

**Tech Stack:** Markdown、PowerShell、ripgrep、Git

---

### Task 1: 建立可验证的系统事实清单

**Files:**
- Read: `docs/reference/课题要求.md`
- Read: `README.md`
- Read: `docs/guides/架构说明.md`
- Read: `docs/guides/启动文档.md`
- Read: `docs/guides/演示文档.md`
- Read: `app/models/*.py`
- Read: `app/api/*.py`
- Read: `app/services/*.py`
- Read: `frontend/src/app/**/page.tsx`
- Read: `docker-compose.yml`
- Read: `tests/test_*.py`

- [ ] **Step 1: 提取课题必做项与加分项**

Run:

```powershell
Get-Content -Raw "docs/reference/课题要求.md"
```

Expected: 得到知识生产、管理、消费和 Agent/Skill 加分项的原始要求。

- [ ] **Step 2: 盘点实际功能与 API**

Run:

```powershell
rg -n "APIRouter|@router\.|class .*Service|class .*Agent|def .*search|def .*review" app
```

Expected: 输出认证、文档、检索、问答、审核、自动学习、Agent 和 Skill 的实现入口。

- [ ] **Step 3: 盘点数据、部署和验证证据**

Run:

```powershell
rg -n "class .*\(Base\)|services:|pytest|knowledge_space|owner_id|embedding" app docker-compose.yml tests
```

Expected: 输出核心数据模型、五个 Docker 服务、知识空间和测试覆盖证据。

### Task 2: 编写系统完整介绍与答辩知识库

**Files:**
- Create: `docs/reference/系统完整介绍与答辩知识库.md`

- [ ] **Step 1: 建立文档目录与事实使用说明**

文档开头必须包含：用途、AI 回答规则、可跳转目录、一句话项目定位、已完成/基础版/待完善标记规则。

- [ ] **Step 2: 编写业务、用户和功能章节**

覆盖：课题背景、目标用户、角色与部门的区别、页面功能、知识生产/管理/消费、审核治理、自动学习、专家 Agent、Skill 和知识整合。

- [ ] **Step 3: 编写架构、数据与流程章节**

覆盖：Next.js/FastAPI/PostgreSQL/pgvector/BGE-m3/DeepSeek/Redis/Celery、Document + Chunk、上传解析、混合检索、RAG、发布审核、访问申请、反馈与自动学习数据流。

- [ ] **Step 4: 编写目录、启动、演示、测试与边界**

覆盖：项目顶层目录、后端分层、前端路由、本地与 Docker 启动、演示账号、验证命令、已知限制、安全表达和后续优化。

### Task 3: 编写答辩问题预测与参考回答

**Files:**
- Create: `docs/reference/答辩问题预测与参考回答.md`

- [ ] **Step 1: 建立分类题库目录**

按设计文档的 12 个主题建立标题，题目编号全局唯一，便于 AI 检索和引用。

- [ ] **Step 2: 编写基础和功能问答**

覆盖：项目定位、课题对应、用户价值、页面、知识生产、检索、问答、审核、个人/公有/部门空间、Agent、Skill 和自动学习。

- [ ] **Step 3: 编写技术和深挖问答**

覆盖：前后端分工、数据库、Chunk、BGE-m3、pgvector、混合检索、RAG、多轮上下文、Redis/Celery、大文件续跑、Docker、数据持久化和异常 fallback。

- [ ] **Step 4: 编写压力型与质疑型问答**

覆盖：为什么不只做普通 RAG、为什么不用 Next.js 全栈、AI 是否可靠、管理员是否越权、语义检索是否真实、大文件为什么失败、Agent/Skill 是否只是包装、哪些尚未完成以及个人贡献。

每题使用以下统一格式：

```markdown
### Q001：问题

**参考回答：** 30–60 秒口语化回答。

**追问补充：** 关键实现细节和技术取舍。

**回答边界：** 仅在容易夸大或混淆时添加。
```

### Task 4: 交叉校验两份文档

**Files:**
- Verify: `docs/reference/系统完整介绍与答辩知识库.md`
- Verify: `docs/reference/答辩问题预测与参考回答.md`

- [ ] **Step 1: 检查占位符、空章节和 Markdown 问题**

Run:

```powershell
rg -n "TODO|TBD|请添加|添加文字|占位" "docs/reference/系统完整介绍与答辩知识库.md" "docs/reference/答辩问题预测与参考回答.md"
git diff --check -- "docs/reference/系统完整介绍与答辩知识库.md" "docs/reference/答辩问题预测与参考回答.md"
```

Expected: `rg` 无匹配，`git diff --check` 无输出。

- [ ] **Step 2: 检查题库数量、编号和必备主题**

Run:

```powershell
rg -c "^### Q[0-9]{3}" "docs/reference/答辩问题预测与参考回答.md"
rg -n "BGE-m3|pgvector|DeepSeek|Redis|Celery|knowledge_space|Agent|Skill|Docker|OCR|管理员|个人知识" "docs/reference/*.md"
```

Expected: 题库不少于 80 题，所有必备主题均有匹配。

- [ ] **Step 3: 核对完成度边界**

手动对照 `README.md` 的“完成情况与边界”、`docs/guides/演示文档.md` 的限制章节和当前代码，确认 OCR、MinIO、Skill 外部化、独立专家对话、版本差异/回滚均未被表述为完整能力。

- [ ] **Step 4: 确认文件存在且不误改其他文件**

Run:

```powershell
Get-Item "docs/reference/系统完整介绍与答辩知识库.md", "docs/reference/答辩问题预测与参考回答.md" | Select-Object Name, Length
git status -sb
```

Expected: 两份文档存在且具有实际内容，工作区无非预期改动。
