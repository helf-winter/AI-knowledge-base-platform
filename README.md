# AI 企业知识库管理平台

面向企业知识生产、知识管理和知识消费的 AI 工作台。项目支持文档导入、知识检索、知识条目管理、专家 Agent、一键问答、问答记录、审计日志和自动学习闭环。

## 项目亮点

- 知识生产：支持上传 PDF、Word、Markdown、文本、图片、表格等文件，并自动解析为可检索知识片段。
- 知识管理：支持知识条目的创建、编辑、审核、归档、删除和状态筛选。
- 知识消费：右下角 AI 问答助手支持多轮会话，优先基于知识库回答，知识不足时自动切换通用回答。
- 知识扩充：当问答发现知识缺口时，用户可确认扩充，系统会优先追加到相近知识库，必要时再创建新文档。
- 自动学习：从低置信度问答和反馈中发现知识缺口，形成可处理的自动学习任务。
- 文档预览：支持 txt 原文、Markdown 渲染、CSV 表格、PDF 原文件内嵌预览，并保留关键词高亮。
- 可观测与追踪：支持问答记录、引用来源、Trace ID、任务状态和审计日志。

## 最新功能说明

### AI 问答助手

- 不再手动选择“通用问答”或“知识库 Agent”，系统会自动先检索知识库，再按需切换通用回答。
- 问答以聊天流形式展示，关闭助手后不会中断 AI 思考，回答完成后会弹出完成提示。
- 悬浮按钮支持拖动，拖动不会误触发打开；助手面板支持拖拽和拉伸调整大小。
- 回答来源按回答中的引用序号展示，可点击跳转到对应知识文档，并带上高亮关键词。
- 对知识库无法覆盖的问题，回答结尾会出现“是否扩充该知识内容”，用户可选择暂不或扩充。

### 知识库与文档详情

- 知识库列表支持上传、检索、按文档查看详情、删除文档。
- 文档详情页提供“返回知识库”按钮，便于从详情页回到列表。
- 全文预览按文件类型展示：
  - txt：保留原始换行和空格。
  - md：渲染标题、列表、加粗等基础 Markdown 格式。
  - csv：按表格方式展示，支持基础 CSV 引号和逗号解析。
  - pdf：优先展示原 PDF 文件，原文件不可用时展示解析文本。
- 文档详情同时展示元数据、处理任务、chunk 列表和命中关键词高亮。

### 首页与自动学习

- 首页仪表盘展示文档数量、知识条目、自动学习缺口、任务状态和最近问答。
- `/tasks` 页面提供自动学习入口，可触发知识缺口分析、查看任务状态、重试失败任务。
- `/conversations` 页面保留问答记录本身，不再混入操作记录跳转。

## 技术栈

### 后端

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL / pgvector 兼容向量检索
- DeepSeek Chat API

### 前端

- Next.js 15
- React 18
- TypeScript
- Tailwind CSS
- lucide-react

## 目录结构

```text
.
├── app/                 # FastAPI 后端应用
├── alembic/             # 数据库迁移
├── frontend/            # Next.js 前端应用
├── scripts/             # 初始化脚本
├── README.md            # 项目说明
├── 启动文档.md           # 本地启动说明
└── 演示文档.md           # 课题演示路径
```

## 本地启动

### 1. 后端

```bash
pip install -r requirements.txt
alembic upgrade head
python scripts/init_db.py
uvicorn app.main:app --reload
```

后端默认地址：

```text
http://127.0.0.1:8000
```

`.env` 至少需要配置：

```env
DATABASE_URL=postgresql+psycopg://用户名:密码@localhost:5432/数据库名
DEEPSEEK_API_KEY=你的 DeepSeek Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

如果暂时不配置 `DEEPSEEK_API_KEY`，系统会回退到基于检索片段的回答。

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：

```text
http://127.0.0.1:3000
```

`frontend/.env.local`：

```env
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

## 核心页面

- `/`：首页仪表盘，展示文档、知识条目、自动学习、任务和最近问答。
- `/documents`：知识库检索、文档上传、文档详情入口。
- `/skills`：Skill 能力目录和一键创建专家助手。
- 右下角浮动助手：自动判断知识库是否足够回答；不足时自动通用补答，并可一键扩充知识库。
- `/tasks`：自动学习入口、知识缺口建议和任务监控。
- `/admin`：知识条目创建、编辑、审核、归档和删除。
- `/conversations`：问答记录、置信度、Trace ID 和引用来源。
- `/audit`：用户操作审计日志。

## 推荐演示流程

1. 登录 `admin / 123456`，进入首页查看整体仪表盘。
2. 进入 `/documents` 上传 txt、md、csv、pdf 等文档，检查解析状态。
3. 点击文档进入详情页，验证不同文件类型的全文预览和返回知识库入口。
4. 使用右下角 AI 问答助手提问，例如“VPN 如何申请”，观察知识库回答、通用补答和来源跳转。
5. 对知识不足的问题点击“扩充”，再回到知识库查看新增或追加的知识内容。
6. 进入 `/tasks` 触发自动学习，查看知识缺口分析和任务状态。
7. 进入 `/conversations` 查看多轮问答记录、Trace ID 和引用来源。

## 演示账号

初始化脚本通常会创建：

```text
admin / 123456
```

## 验证命令

```bash
python -m compileall app
cd frontend
npm run build
```

更完整的课堂/答辩演示路径见 [演示文档.md](./演示文档.md)。
