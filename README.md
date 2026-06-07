# AI Knowledge Base Platform

AI 知识库管理平台，用于企业知识的生产、管理与消费。项目支持文档导入、知识检索、专家 Agent 问答、自动提炼知识、技能目录展示与任务/审计记录查询。

## 项目概览

本项目围绕企业知识流转构建，核心目标是让用户和 Agent 都能参与知识的生产与消费，形成“知识沉淀 → 知识管理 → 智能问答 → 自动提炼 → 再沉淀”的闭环。

### 核心能力
- 知识生产：支持文档导入、手动维护知识元数据、自动提炼知识缺口
- 知识管理：支持知识检索、创建/编辑/删除、状态管理、归档/审核
- 知识消费：支持通用问答、专家 Agent 问答、Skill 目录、Agent 推荐
- 闭环能力：支持自动学习任务、问答记录、审计记录、知识热度统计

## 技术栈

### 前端
- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn 风格 UI 组件

### 后端
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL / 兼容关系型数据库
- DeepSeek 接口（可选，用于生成式问答）

## 目录结构

```text
.
├── app/                 # 后端 FastAPI 应用
├── alembic/             # 数据库迁移
├── frontend/            # 前端 Next.js 应用
├── scripts/             # 初始化脚本
├── README.md
└── 启动文档.md
```

## 快速启动

### 1. 后端

```bash
pip install -r requirements.txt
python scripts/init_db.py
uvicorn app.main:app --reload
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

### 3. 数据库迁移

```bash
alembic upgrade head
```

## 环境变量

### 后端
- `DATABASE_URL`：数据库连接地址
- `DEEPSEEK_API_KEY`：DeepSeek API Key
- `DEEPSEEK_BASE_URL`：DeepSeek 接口地址
- `DEEPSEEK_MODEL`：模型名
- `DEEPSEEK_THINKING_ENABLED`：是否启用思考模式

### 前端
- `NEXT_PUBLIC_API_BASE`：后端 API 基地址

## 核心页面

### 1. 知识库管理
- 文档上传
- 知识条目管理
- 状态筛选/审核/归档
- 知识热度统计

### 2. 助手与技能
- 查看可用 Skill 目录
- 一键创建专家 Agent
- 给 Agent 绑定 skills
- 查看 Agent 绑定的知识域与技能

### 3. 问答与分流
- 通用问答入口
- 专家 Agent 问答
- 通用问答可推荐合适的 Agent
- 支持问答记录与操作记录联动

### 4. 自动学习
- 自动提炼知识缺口
- 自动生成知识草稿
- 任务重试与任务监控

## 架构说明

简要架构已整理在 `架构说明.md` 中，包含：
- 前后端分层
- 知识生产/消费流程
- Agent 与 Skill 的关系
- 数据流与闭环

## 交付说明

### 可演示主线
- 知识上传与管理
- 专家 Agent 创建与问答
- 通用问答推荐 Agent
- 自动学习与知识提炼
- 审计/问答记录联动

### 建议提交前检查
- 确认数据库迁移已执行
- 确认前后端可本地启动
- 确认核心页面无 500/404
- 确认 README 与架构说明齐全

## 备注

如果你希望先看更详细的启动步骤，可参考 `启动文档.md`。
