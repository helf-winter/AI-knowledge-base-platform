# AI 企业知识库管理平台

面向企业内部知识生产、治理和智能消费的 AI 知识管理平台。系统将分散的文档、员工经验和问答记录转化为可检索、可追溯、可审核的知识资产，并通过 AI 问答、专家 Agent、Skill 和自动学习闭环提供智能服务。

本项目定位为具备企业知识治理能力的完整演示原型，不只是文档上传工具或普通 RAG 问答页面。

## 核心能力

### 1. 知识生产

- 上传 PDF、Word、Markdown、TXT、CSV、Excel 和图片等文件。
- 文档自动解析、Chunk 切分并使用本地 BGE-m3 生成语义向量。
- 支持在页面中手动创建个人知识。
- AI 问答知识不足时，可由用户确认后补充为个人知识。
- 根据低置信度回答和用户反馈发现知识缺口，生成待审核知识草稿。
- 大文件进入 Redis + Celery 后台队列，页面展示排队、解析、成功和失败状态，并支持重试或继续解析。

### 2. 知识管理

- 通过 `personal`、`public`、`department` 区分个人、公有和部门知识空间。
- 用户创建或上传的知识默认属于个人空间，仅本人可访问。
- 个人知识发布到公有知识库前必须提交审核。
- 管理员可以审核访问申请和发布申请，AI 只提供建议，不自动审批。
- 普通员工可以对公有知识提交问题或修改建议，由管理员处理。
- 支持知识类别、标签、文件类型、知识空间和适用岗位等组合筛选。
- 知识整合 Agent 可发现相似文档，调用 DeepSeek 生成带来源和冲突说明的整合草稿，审核后创建新文档，原文档默认保留。
- 支持问答记录、Trace ID、来源引用和关键操作审计。

### 3. 知识检索

- 关键词检索：补充精确词和标题匹配。
- 语义检索：本地 BGE-m3 生成 1024 维向量，PostgreSQL pgvector 执行相似度检索。
- 标签筛选：支持类别、标签、知识空间、文件类型和适用岗位筛选。
- 权限过滤：检索和 RAG 只召回当前用户有权访问的知识。
- 混合排序：综合语义相似度、关键词匹配和基础重排结果。

### 4. 知识消费

- 全局 AI 问答助手支持多轮连续对话和按用户隔离的消息缓存。
- 优先基于企业知识回答，知识不足时自动使用通用回答兜底。
- 回答展示引用来源，可跳转到原文并高亮相关内容。
- 用户可对回答标记“有帮助”或“无帮助”，反馈可进入自动学习闭环。
- 可根据选定知识范围生成专家 Agent 配置。
- Skill 能力包括知识检索、文档总结、流程提取、知识对比、知识缺口发现和发布草稿生成。

## 系统架构

```text
浏览器
  -> Next.js 15 + React 18 + TypeScript
  -> FastAPI
     |- 身份认证与角色权限
     |- 知识管理与审核
     |- Search / RAG
     |- Agent / Skill
     |- 自动学习与审计
     `- Celery 后台任务
  -> PostgreSQL + pgvector
  -> Redis
  -> 本地 BGE-m3
  -> DeepSeek API
```

### 技术栈

| 层级 | 技术 |
|---|---|
| 前端 | Next.js 15、React 18、TypeScript、Tailwind CSS、TanStack Query、Zustand |
| 后端 | FastAPI、SQLAlchemy、Pydantic、Alembic |
| 数据库 | PostgreSQL 16、pgvector |
| 后台任务 | Redis、Celery |
| AI 生成 | DeepSeek API，异常时提供规则 fallback |
| 语义向量 | 本地 BGE-m3、sentence-transformers |
| 部署 | Docker Compose、本地 Windows 启动脚本 |

## 项目结构

```text
.
|- app/                       # FastAPI 后端、模型、服务、Agent 与 Skill
|- alembic/                   # 数据库迁移
|- frontend/                  # Next.js 前端
|- scripts/                   # 初始化、向量重建、分类标签补全等脚本
|- tests/                     # 后端单元测试
|- docs/
|  |- guides/                 # 启动、架构、演示和答辩文档
|  `- reference/              # 课题要求与设计参考
|- data/uploads/              # 本地上传文件（开发环境）
|- docker-compose.yml         # 容器服务编排
|- Dockerfile.backend         # 后端与 Worker 镜像
|- start.bat                  # Windows 双击启动入口
`- start.ps1                  # 本地启动逻辑
```

## 环境准备

### 本地开发环境

- Windows 10/11
- Conda 环境：`knowledge-base`
- Python 3.11 或项目当前兼容版本
- Node.js 18+
- PostgreSQL，并安装 `vector` 扩展
- Redis（大文件后台解析需要）
- 本地 BGE-m3 模型，默认路径：`D:/code/models/bge-m3`

确认 pgvector：

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

首次安装依赖：

```powershell
conda activate knowledge-base
python -m pip install -r requirements.txt

cd frontend
npm install
cd ..
```

### 环境变量

在项目根目录创建或修改 `.env`：

```env
DATABASE_URL=postgresql+psycopg://postgres:你的密码@localhost:5432/knowledge_base
REDIS_URL=redis://localhost:6379/0

DEEPSEEK_API_KEY=你的_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

EMBEDDING_PROVIDER=bge
EMBEDDING_MODEL_PATH=D:/code/models/bge-m3
EMBEDDING_DIMENSION=1024
BACKGROUND_PARSE_THRESHOLD_MB=20
MAX_UPLOAD_SIZE_MB=100
```

不要提交包含真实密码、数据库连接信息或 API Key 的 `.env`、`.env.production`。

## 本地一键启动

### 启动前

1. 确认 PostgreSQL 正在运行。
2. 确认数据库与 `.env` 中的 `DATABASE_URL` 一致。
3. 大文件后台解析需要 Redis 监听 `6379` 端口。
4. 首次运行或数据库结构变化后执行迁移：

```powershell
conda activate knowledge-base
alembic upgrade head
```

### 双击启动

直接双击项目根目录中的 `start.bat`，或者执行：

```powershell
.\start.bat
```

执行流程：

```text
start.bat
  -> 调用 start.ps1
  -> 检查 Conda 与 Node.js
  -> 使用 knowledge-base 环境启动 FastAPI
  -> Redis 可用时启动 Celery Worker
  -> 启动 Next.js
  -> 检查前后端健康状态
  -> 自动打开浏览器
```

脚本默认不会重复安装依赖。依赖发生变化时可执行：

```powershell
.\start.ps1 -InstallDeps
```

### 手动启动

后端：

```powershell
conda activate knowledge-base
alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Celery Worker（另开终端，先启动 Redis）：

```powershell
conda activate knowledge-base
celery -A app.worker.celery_app worker --pool=solo --loglevel=info
```

前端（另开终端）：

```powershell
cd frontend
$env:NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000"
npm run dev -- --hostname 127.0.0.1 --port 3000
```

## Docker Compose 启动

Docker Compose 会统一启动以下服务：

- `postgres`：PostgreSQL + pgvector
- `redis`：后台任务队列
- `backend`：FastAPI 后端
- `worker`：Celery 文档解析 Worker
- `frontend`：Next.js 前端

首次准备配置：

```powershell
Copy-Item .env.production.example .env.production
```

修改 `.env.production` 中的数据库密码、DeepSeek Key、本地模型路径和上传大小限制后启动：

```powershell
docker compose -p ai-kb --env-file .env.production up -d --build
```

查看状态：

```powershell
docker compose -p ai-kb --env-file .env.production ps
```

查看日志：

```powershell
docker compose -p ai-kb --env-file .env.production logs -f
```

停止服务但保留数据库和上传文件：

```powershell
docker compose -p ai-kb --env-file .env.production down
```

不要随意增加 `-v`，否则会删除 Compose 数据卷中的数据库和上传文件。

### 什么时候需要重新构建镜像

| 改动 | 操作 |
|---|---|
| Python、前端代码、`requirements.txt`、`package.json`、Dockerfile | `up -d --build` |
| 仅修改容器环境变量 | 通常执行 `up -d` 以重建受影响容器 |
| 仅修改数据库数据 | 不需要重建镜像 |
| 新增 Alembic 迁移 | 重启后端并确保执行 `alembic upgrade head` |
| 只想再次启动已有容器 | `docker compose -p ai-kb start` |

本项目近期修改了前后端代码、数据库迁移和依赖相关能力，因此再次使用 Docker 时需要执行：

```powershell
docker compose -p ai-kb --env-file .env.production up -d --build
```

该命令会更新镜像和容器，但不会删除已有命名数据卷。

## 访问地址

| 服务 | 地址 |
|---|---|
| 前端页面 | http://127.0.0.1:3000 |
| 后端服务 | http://127.0.0.1:8000 |
| API 文档 | http://127.0.0.1:8000/docs |
| 健康检查 | http://127.0.0.1:8000/health |

## 数据库初始化与迁移

数据库迁移用于将已有数据库结构升级到代码要求的最新版本：

```powershell
conda activate knowledge-base
alembic upgrade head
```

初始化脚本主要用于首次创建基础表：

```powershell
python scripts/init_db.py
```

已有项目优先使用 Alembic 迁移，不要用初始化脚本代替迁移。

常用维护脚本：

```powershell
# 重新生成已有 Chunk 的 BGE-m3 向量
python scripts/rebuild_embeddings.py

# 重新解析指定文档
python scripts/reparse_document.py --help

# 为历史文档补充知识类别和结构化标签
python scripts/backfill_knowledge_taxonomy.py --help
```

## 核心页面

| 路径 | 功能 |
|---|---|
| `/login` | 企业账号登录与首次改密 |
| `/` | 知识工作台和统计概览 |
| `/documents` | 知识上传、创建、检索、筛选和发布申请 |
| `/documents/{id}` | 文档预览、Chunk 与解析状态 |
| `/skills` | Skill 能力目录和专家 Agent 创建 |
| `/tasks` | 自动学习、知识缺口和任务状态 |
| `/conversations` | 问答记录、反馈、来源与 Trace ID |
| `/admin` | 管理员审核、内容治理和知识整合 |
| `/audit` | 关键操作审计 |

页面和后端接口均按用户角色与知识权限进行控制；隐藏前端菜单并不代替后端权限校验。

## 检查与验证

后端编译与测试：

```powershell
conda run -n knowledge-base python -m compileall app scripts
conda run -n knowledge-base python -m unittest discover -s tests -p "test_*.py" -v
```

前端构建：

```powershell
cd frontend
npm.cmd run build
```

数据库迁移状态：

```powershell
conda run -n knowledge-base alembic current
```

Docker 服务检查：

```powershell
docker compose -p ai-kb --env-file .env.production ps
docker compose -p ai-kb --env-file .env.production logs --tail 100 backend worker frontend
```

## 当前边界与后续优化

- 普通文本 PDF 可以解析，扫描版、水印严重或纯图片 PDF 仍需增强 OCR。
- 当前原始文件主要保存在本地目录或 Docker 数据卷，生产环境可迁移到 MinIO。
- 已支持后台解析、状态展示和继续解析，后续可增强分布式 Worker、任务优先级和更细粒度检查点。
- 当前使用轻量混合重排，后续可接入 Cross-Encoder 提高最终排序精度。
- Skill 目前主要在系统内部调用，后续可封装为带鉴权、限流和审计的外部 API 或插件。
- 已有知识状态和审核记录，后续可继续完善版本差异比较、回滚和灰度发布。

## 项目文档

- [启动文档](./docs/guides/启动文档.md)
- [架构说明](./docs/guides/架构说明.md)
- [演示文档](./docs/guides/演示文档.md)
- [答辩 PPT 大纲与系统演示指南](./docs/guides/答辩PPT大纲与系统演示指南.md)
- [课题要求](./docs/reference/课题要求.md)

## 安全说明

- 本项目面向企业内部账号体系，不建议开放匿名注册。
- 首次登录需要修改初始密码。
- AI 生成内容不会自动发布到公有知识库。
- 管理员不能随意查看用户未提交审核的个人知识。
- 提交代码前应确认 `.env`、`.env.production`、数据库文件和上传文件未被纳入 Git。
