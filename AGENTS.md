# ArXiv Paper Reader (Web)

本项目是一个实验室内部使用的 arXiv 论文阅读工具。用户输入 arXiv 链接或 ID，系统自动下载论文 LaTeX 源码、解析结构，并通过 LLM（默认 Moonshot Kimi）生成**结构化中文阅读报告**（非全文翻译），方便实验室成员快速了解论文核心内容。

主要功能：
- 提交 arXiv 链接，后台异步生成中文阅读报告
- 左侧论文列表，支持标题/作者/arXiv ID 搜索
- 报告包含：论文概览、研究背景、方法总结、实验结果、伪代码、总结
- 公式自动渲染（KaTeX），图片自动提取与展示
- 每篇论文独立 URL（`/paper/{arxiv_id}`），方便分享
- 支持删除、重试、实时状态显示

---

## 技术栈

- **后端**: Python 3.13+, FastAPI, SQLAlchemy (SQLite), Pydantic, uv
- **前端**: Vite + React 18 + TypeScript + Tailwind CSS + KaTeX
- **LLM / Agent**: Moonshot AI (Kimi) API（OpenAI 兼容格式），内部 Agent 框架 `kosong`
- **PDF / 图片处理**: PyMuPDF (fitz), pdftoppm, pdflatex, inkscape
- **部署**: Docker Compose（单容器）

---

## 项目结构

```
arxiv-paper-web/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 应用入口与生命周期
│   │   ├── config.py            # Pydantic Settings，读取 .env 配置
│   │   ├── database.py          # SQLAlchemy engine / session / Base
│   │   ├── models.py            # SQLAlchemy ORM 模型（Paper）
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── logger.py            # 统一日志（控制台 + 文件）
│   │   ├── routers/
│   │   │   └── papers.py        # REST API：提交/列表/详情/删除/重试
│   │   └── services/
│   │       ├── arxiv_service.py # 下载 arXiv LaTeX 源码、图片提取与转换
│   │       ├── latex_parser.py  # LaTeX 结构解析（标题/作者/章节/图表/公式）
│   │       ├── llm_service.py   # 直接调用 Kimi API 生成报告（旧路径，仍保留）
│   │       └── agent_service.py # 基于 kosong 的 Tool-use Agent，逐步阅读论文并生成报告（当前主路径）
│   ├── data/                    # 运行时数据（SQLite DB、LaTeX 源码、图片、日志）
│   └── pyproject.toml           # uv 依赖管理
├── frontend/
│   ├── src/
│   │   ├── main.tsx             # React 入口
│   │   ├── App.tsx              # 路由配置（/ 和 /paper/:arxivId）
│   │   ├── index.css            # Tailwind + KaTeX + markdown-body 样式
│   │   ├── lib/
│   │   │   └── api.ts           # Axios 封装与 API 类型定义
│   │   ├── pages/
│   │   │   ├── HomePage.tsx     # 首页：左侧列表 + 右侧阅读器
│   │   │   └── PaperPage.tsx    # 独立论文页（支持直接分享 URL）
│   │   └── components/
│   │       ├── SubmitForm.tsx   # 顶部 arXiv 提交表单
│   │       ├── PaperList.tsx    # 左侧论文列表与搜索
│   │       └── PaperViewer.tsx  # 右侧 Markdown 报告渲染
│   ├── index.html               # 页面模板（加载 KaTeX CDN CSS）
│   ├── vite.config.ts           # Vite 配置（含开发代理 /api -> localhost:8002）
│   ├── tailwind.config.js
│   ├── tsconfig.json            # strict mode，noUnusedLocals
│   └── package.json
├── .env                         # 环境变量（API Key 等，不提交 Git）
├── .env.example                 # 环境变量模板
├── Dockerfile                   # 多阶段构建：前端 build → Python 后端
└── docker-compose.yml           # 端口映射 8081:8000
```

---

## 构建与运行命令

### 开发环境

**1. 后端**

```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -e .
# 同时需要安装 kosong（Agent 框架，未写入 pyproject.toml）
uv pip install kosong

uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

**2. 前端**

```bash
cd frontend
npm install
npm run dev
# 默认监听 0.0.0.0:5173
# /api 和 /images 自动代理到 localhost:8002
```

前端开发服务器已通过 `vite.config.ts` 配置代理，无需额外处理跨域。

**3. 访问**

- 开发时通常通过 VSCode 端口转发 `5173` 到本地浏览器访问。
- 也可以直接公网访问（需放行对应端口）。

### 生产部署（Docker）

```bash
docker compose up --build -d
```

访问 `http://<服务器IP>:8081`。Docker 内部后端运行在 8000 端口，外部映射到 8081。

在生产模式下，FastAPI 会挂载 `frontend/dist` 作为静态文件，并兜底返回 `index.html`（SPA 模式）。

---

## 代码组织与模块划分

### 后端 (`backend/app/`)

- **main.py**: FastAPI 实例创建、CORS 中间件、路由注册、静态文件挂载。启动时自动创建 SQLite 表。
- **config.py**: `Settings` 类使用 `pydantic-settings` 读取项目根目录的 `.env`。所有路径基于 `PROJECT_ROOT` 计算，确保无论从哪启动 uvicorn 都能找到正确路径。
- **database.py**: 单例 `engine` + `SessionLocal` + `get_db()` 生成器，供 FastAPI 依赖注入使用。
- **models.py**: 仅一个 `Paper` 表，字段涵盖 arxiv_id、title、title_zh、authors、abstract、report_md、raw_sections（JSON）、images（JSON）、status（pending/processing/done/failed）、error_msg 等。
- **schemas.py**: Pydantic v2 模型，`from_attributes = True` 用于 ORM 序列化。
- **routers/papers.py**: 
  - `POST /api/papers/` — 提交论文，启动后台 `BackgroundTasks` 处理
  - `GET /api/papers/` — 列表 + 搜索（title / title_zh / arxiv_id）
  - `GET /api/papers/{arxiv_id}` — 详情（含 report_md）
  - `DELETE /api/papers/{arxiv_id}` — 删除论文及其关联文件（图片、LaTeX）
  - `POST /api/papers/{arxiv_id}/retry` — 重置状态并重新处理
- **services/arxiv_service.py**: 核心流水线。`ArxivService.process_paper()` 负责：下载/复用 LaTeX → 找主 tex → 解析 → 提取图片 → 调用 Agent 生成报告。图片提取支持 PDF/PNG/JPG/EPS 外部文件，以及 tikz 内联图形的编译（通过 `pdflatex`）。
- **services/latex_parser.py**: 纯文本正则解析器，递归处理 `\input` / `\include`，提取 documentclass、title、authors、abstract、sections、figures、tables、algorithms、equations。
- **services/agent_service.py**: 当前主生成路径。基于 `kosong` 框架构建 Tool-use Agent，提供三个工具：`read_section`（读取章节）、`view_image`（查看图片，base64 编码传给多模态 LLM）、`write_report`（写出最终报告）。Agent 最多执行 30 步，逐步阅读后生成 Markdown 报告。
- **services/llm_service.py**: 旧路径，直接通过 OpenAI SDK 一次性调用 Kimi API 生成报告。代码保留但未在主线中使用。

### 前端 (`frontend/src/`)

- **api.ts**: Axios 实例，baseURL 为 `/api`。定义 `Paper` / `PaperDetail` 接口和 `paperApi` 方法。
- **HomePage.tsx**: 三栏布局的上半部分（SubmitForm）+ 下半部分左右分栏（PaperList + PaperViewer）。通过 `refreshTrigger` 状态触发列表刷新。
- **PaperPage.tsx**: 独立路由 `/paper/:arxivId`，可直接通过 URL 访问单篇论文。加载时调用 API 获取详情。
- **PaperList.tsx**: 左侧列表，带搜索框。对 `processing` / `pending` 状态的论文每 5 秒轮询刷新。
- **PaperViewer.tsx**: 使用 `react-markdown` + `remark-math` + `rehype-katex` 渲染 Markdown 报告。将相对图片路径 `./xxx.png` 替换为 `/images/{arxiv_id}/xxx.png`。
- **index.css**: Tailwind 指令 + `.markdown-body` 的详细样式（标题卡片、表格、代码块、引用块、图片圆角阴影等）。

---

## 数据流与业务逻辑

1. 用户提交 arXiv 链接或 ID → 后端提取 arxiv_id → 查重（DB 中已存在则直接返回）→ 创建 `pending` 记录 → 启动后台任务。
2. 后台任务：
   - 下载 LaTeX 源码（`https://arxiv.org/e-print/{arxiv_id}`），若已下载则复用。
   - 找到主 tex 文件（含 `\documentclass`），用 `LatexParser` 解析结构。
   - 提取图片：外部图片（PDF/PNG/JPG/EPS）转换/复制为 PNG；tikz 图形调用 `pdflatex` 编译后转 PNG。
   - 调用 `PaperAgent`（kosong Agent）：Agent 通过工具逐步读取章节、查看图片，最终生成结构化中文报告。
   - 报告存回 `report_md`，状态变为 `done`。若失败则状态 `failed` 并记录 `error_msg`。
3. 前端列表轮询 `processing` / `pending` 论文，完成后用户可点击查看报告。

---

## 开发规范

### Python

- 项目未配置显式的 linter/formatter（如 ruff、black），代码风格相对简洁直观。
- 使用 `from __future__ import annotations`（agent_service.py）。
- 日志统一通过 `app.logger.setup_logger()` 创建，输出到控制台和 `backend/data/app.log`。
- 所有外部 I/O（下载、LLM 调用）均记录 info/error 日志，方便排查。
- 后台任务中手动创建 `SessionLocal()`，因为 `BackgroundTasks` 不在请求上下文中，无法使用 `Depends(get_db)`。

### TypeScript / React

- `tsconfig.json` 启用 `strict: true`、`noUnusedLocals: true`、`noUnusedParameters: true`。不允许未使用的变量/参数。
- 组件使用函数式组件 + Hooks。
- 前端路由使用 `react-router-dom` v6。
- 图标统一使用 `lucide-react`。
- API 调用集中封装在 `lib/api.ts`，组件中直接使用。

---

## 环境变量与配置

所有配置通过项目根目录 `.env` 提供，由 `backend/app/config.py` 读取。

必填：
- `MOONSHOT_API_KEY` — Moonshot AI API Key

选填：
- `MOONSHOT_MODEL` — 默认 `kimi-k2.5`（支持 reasoning / vision / 256k 上下文）
- `MOONSHOT_BASE_URL` — 默认 `https://api.moonshot.cn/v1`

因为使用 OpenAI 兼容 SDK，理论上可更换为 DeepSeek、智谱 GLM、OpenAI 等，只需修改 `.env` 中的 base_url 和 model。

数据库、文件路径等也有默认值，通常无需修改：
- `DATABASE_URL` — 默认 `sqlite:///.../backend/data/papers.db`
- `PAPERS_DIR` / `IMAGES_DIR` / `LATEX_DIR` — 默认在 `backend/data/` 下
- `MAX_WORKERS` — 默认 2

---

## 部署注意事项

### Docker 部署

`Dockerfile` 采用多阶段构建：
1. `node:20-alpine` 构建前端（`npm run build`）
2. `python:3.10-slim` 运行后端，复制前端 `dist` 产物

运行时安装系统包 `poppler-utils`（提供 `pdftoppm`），并安装 `uv` 管理 Python 依赖。

注意：容器内未预装 `pdflatex` 和 `inkscape`。如果论文包含 tikz 图形或 EPS 图片，Docker 部署可能会跳过这些图片的转换。开发环境需要确保宿主机安装了 `texlive` 和 `inkscape` 才能完整支持。

### 数据持久化

`docker-compose.yml` 将 `./data` 挂载到容器的 `/app/data`，确保数据库和下载的文件在容器重建后保留。

---

## 安全与权限

- **无用户认证/授权**：实验室内部工具，所有人均可访问、提交、删除。
- **CORS**：`allow_origins=["*"]`，开发便利但公网部署需注意。
- **API Key**：通过 `.env` 管理，**切勿提交到 Git**（已加入 `.gitignore`）。
- **文件操作**：删除论文时会级联删除 `backend/data/images/{arxiv_id}` 和 `backend/data/latex/{arxiv_id}` 目录。
- **LaTeX 编译**：`_compile_tikz_figure` 在临时目录中调用 `pdflatex`，有一定安全风险（执行外部命令），但在内部可控环境中使用。

---

## 外部依赖与系统工具

除 `pyproject.toml` / `package.json` 中的依赖外，以下系统工具在运行时是必需的：

| 工具 | 用途 | 安装方式 |
|------|------|----------|
| `pdftoppm` | EPS → PNG 转换 | `apt install poppler-utils` |
| `pdflatex` | tikz 图形编译 | `apt install texlive`（完整版） |
| `inkscape` | EPS 备选转换 | `apt install inkscape` |

Agent 框架 `kosong` 未写入 `pyproject.toml`，需要单独安装：
```bash
uv pip install kosong
```

---

## Agent 行为规范

### 前台启动服务

**除非用户明确指示在后台运行，否则所有服务（后端 uvicorn、前端 Vite dev server 等）必须在当前终端前台启动。**

禁止在后台静默启动进程，否则用户无法找到对应的进程号（PID），导致端口被占用且无法自行停止。如果用户需要同时运行前后端，应指导用户开启多个终端窗口分别执行。

### 提交信息规范

所有 Git commit message 必须遵循**约定式提交（Conventional Commits）**规范，格式如下：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

常用的 `type` 包括：

| Type | 含义 |
|------|------|
| `feat` | 新功能 / 新特性 |
| `fix` | 修复 Bug |
| `docs` | 仅文档更新 |
| `style` | 代码格式调整（不影响逻辑） |
| `refactor` | 代码重构（既不修复 bug 也不添加功能） |
| `perf` | 性能优化 |
| `test` | 添加或修改测试 |
| `chore` | 构建过程、工具、依赖等杂项 |

示例：
- `feat: add TikZ figure compilation via pdflatex`
- `fix: resolve port conflict when restarting uvicorn`
- `docs: update AGENTS.md with agent behavior guidelines`

---

## 常见问题排查

- **前端页面空白/打不开**：检查 Vite dev server 是否运行、VSCode 端口转发是否添加 5173、防火墙是否放行。
- **提交后一直 processing**：检查后端 uvicorn 是否在运行、`.env` 中 `MOONSHOT_API_KEY` 是否有效、查看 `backend/data/app.log`。
- **图片显示不出来**：图片由后端 `/images` 路由提供，确保后端在运行，且图片存在于 `backend/data/images/{arxiv_id}/`。
- **公式显示为源码**：确保浏览器能加载 `https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css`。内网隔离环境需下载到本地并修改 `frontend/index.html`。
