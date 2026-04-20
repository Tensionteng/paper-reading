# ArXiv Paper Reader

一个基于 LLM Agent 的 arXiv 论文阅读工具。输入 arXiv 链接，自动下载 LaTeX 源码并生成**结构化中文阅读报告**，帮助快速理解论文核心内容。

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.13+-blue" alt="Python 3.13+">
  <img src="https://img.shields.io/badge/Node-18+-green" alt="Node 18+">
  <img src="https://img.shields.io/badge/React-18-61DAFB?logo=react" alt="React 18">
  <img src="https://img.shields.io/badge/Tailwind-3-06B6D4?logo=tailwindcss" alt="Tailwind CSS">
</p>

---

## 功能特性

- **智能阅读报告** — 基于 LLM Agent 逐步阅读论文，生成包含背景、方法、实验、总结的结构化中文报告
- **LaTeX 原生解析** — 直接解析论文 LaTeX 源码，准确提取公式、图片、表格
- **自动图片提取** — 支持 PDF/PNG/JPG/EPS 外部图片，以及 TikZ 内联图形的编译提取
- **公式渲染** — 基于 KaTeX，完美渲染行内和独立公式
- **论文管理** — 左侧列表支持搜索，单篇论文独立 URL，可删除/重试
- **暗黑模式** — 支持跟随系统偏好自动切换，也可手动切换
- **多模型兼容** — OpenAI 兼容接口，可更换 Kimi / DeepSeek / GLM / OpenAI 等

---

## 快速开始

### 环境要求

- Python 3.13+
- Node.js 18+
- [uv](https://github.com/astral-sh/uv)（Python 包管理器）

系统工具（图片处理需要）：

```bash
# Ubuntu/Debian
sudo apt install poppler-utils texlive inkscape
```

### 1. 配置

```bash
cp .env.example .env
```

编辑 `.env`，填入 API Key：

```bash
# 必填：LLM API Key
MOONSHOT_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 选填：模型（默认 kimi-k2.5）
MOONSHOT_MODEL=kimi-k2.5
```

### 2. 安装依赖

```bash
# 后端
cd backend
uv venv
source .venv/bin/activate
uv pip install -e .

# 前端
cd ../frontend
npm install
```

### 3. 启动

```bash
# 终端 1：后端
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# 终端 2：前端
cd frontend
npm run dev
```

前端默认运行在 `http://localhost:5173`，API 代理已配置，无需处理跨域。

---

## 使用说明

1. 在顶部输入框粘贴 arXiv 链接或 ID，如 `https://arxiv.org/abs/2307.09288`
2. 点击"提交"，后台自动下载并解析论文
3. 左侧列表查看状态，`processing` → `done` 后即可阅读
4. 点击论文标题进入独立阅读页，URL 可直接分享

---

## 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | FastAPI, SQLAlchemy (SQLite), Pydantic, uv |
| **前端** | Vite, React 18, TypeScript, Tailwind CSS, KaTeX |
| **Agent 框架** | kosong（Tool-use Agent 循环） |
| **LLM** | Moonshot Kimi（OpenAI 兼容，可更换） |
| **部署** | Docker Compose（可选） |

---

## 更换 LLM 模型

修改 `.env` 即可切换不同厂商：

| 厂商 | `MOONSHOT_BASE_URL` | `MOONSHOT_MODEL` |
|------|---------------------|------------------|
| **Kimi (默认)** | `https://api.moonshot.cn/v1` | `kimi-k2.5` |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat` |
| **智谱 GLM** | `https://open.bigmodel.cn/api/paas/v4/` | `glm-4` |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o` |

---

## Docker 部署

```bash
docker compose up --build -d
```

访问 `http://<host>:8081`

---

## 项目结构

```
arxiv-paper-web/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── routers/papers.py    # REST API
│   │   ├── services/
│   │   │   ├── arxiv_service.py # 下载 + 图片提取
│   │   │   ├── latex_parser.py  # LaTeX 结构解析
│   │   │   └── agent_service.py # LLM Agent 生成报告
│   │   └── ...
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/          # 表单、列表、阅读器、主题切换
│   │   └── pages/               # 首页、独立论文页
│   └── package.json
├── Dockerfile
├── docker-compose.yml
└── .env
```

---

## License

MIT
