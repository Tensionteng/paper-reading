# ArXiv Paper Reader (Web)

基于你的 [arxiv-paper-reader skill](https://github.com/Tensionteng/csu-oss-skills/tree/main/arxiv-paper-reader) 构建的实验室论文阅读工具。

输入 arXiv 链接，自动下载 LaTeX 源码，解析结构后通过 Kimi API 生成**结构化中文阅读报告**（非全文翻译），方便实验室快速了解论文核心内容。

---

## 功能

- 输入 arXiv 链接，自动生成结构化中文阅读报告
- 重复检测：已存在的论文直接提示并跳转
- 左侧论文列表，支持标题/作者/arXiv ID 搜索
- 报告包含：论文概览、研究背景、方法总结、实验结果、伪代码、总结
- 公式自动渲染（KaTeX），图片自动提取
- 每篇论文独立 URL（`/paper/{arxiv_id}`），方便实验室分享
- 删除 / 重试 / 实时状态显示

---

## 技术栈

- **后端**: FastAPI + SQLite + uv
- **前端**: Vite + React + Tailwind CSS + KaTeX
- **LLM**: Moonshot AI (Kimi) API（兼容 OpenAI 格式，可更换）
- **部署**: 单容器 Docker（可选）

---

## 环境准备

服务器上需要已安装：

```bash
# Python 3.10+
python3 --version

# uv（Python 包管理器）
which uv || pip3 install --user uv

# Node.js 18+ 和 npm
node --version   # v18+
npm --version
```

---

## 1. 配置环境变量

```bash
cd /home/tengshiyuan/code/arxiv-paper-web
cp .env.example .env
```

编辑 `.env`：

```bash
# 必填：Moonshot AI (Kimi) API Key
# 获取地址：https://platform.moonshot.cn/
MOONSHOT_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 选填：模型选择（默认 kimi-k2.5）
MOONSHOT_MODEL=kimi-k2.5
```

**关于 API Key**：
- 登录 [Moonshot 开放平台](https://platform.moonshot.cn/) → 账户管理 → API Key 管理
- 当前代码默认使用 `kimi-k2.5`（256k 上下文，2026 年 1 月发布的最新模型）

---

## 2. 安装依赖

### 后端

```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 前端

```bash
cd frontend
npm install
```

---

## 3. 启动服务（VSCode 端口转发方式）

### 步骤 3.1：启动后端

在 VSCode 终端（已 SSH 连接到服务器）中执行：

```bash
cd /home/tengshiyuan/code/arxiv-paper-web/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

**说明**：
- `--reload`：开发模式下代码修改后自动重启
- `--host 0.0.0.0`：允许内网访问
- 端口 8000 可能被其他服务占用，这里使用 8002
- 保持这个终端运行，不要关闭

### 步骤 3.2：启动前端

**新开一个 VSCode 终端**，执行：

```bash
cd /home/tengshiyuan/code/arxiv-paper-web/frontend
npm run dev
```

**说明**：
- 前端 dev server 默认运行在 `http://0.0.0.0:5173`
- 已配置 `host: '0.0.0.0'`，支持内网访问
- 已配置代理：`/api` 和 `/images` 会自动转发到后端的 `localhost:8002`
- 保持这个终端运行，不要关闭

### 步骤 3.3：VSCode 端口转发

在 VSCode 左侧活动栏点击 **"端口"** 图标（或按 `Ctrl+Shift+P` 搜索 "Ports: Focus on Ports View"），然后：

1. 点击 **"转发端口"**（或 `+` 号）
2. 输入 `5173`，回车
3. （可选）再添加 `8002`，方便直接调试后端 API

VSCode 会自动把服务器的端口转发到你本地的 `localhost`：

| 服务器端口 | 本地地址 | 用途 |
|-----------|---------|------|
| 5173 | `http://localhost:5173` | 前端页面（**必转**） |
| 8002 | `http://localhost:8002` | 后端 API（可选，调试用） |

### 步骤 3.4：访问

在本机浏览器打开：

```
http://localhost:5173
```

即可看到前端页面。由于 vite proxy 已配置，前端页面内的 API 请求会自动被代理到后端，**不需要额外配置跨域**。

---

## 4. 使用说明

### 提交论文

1. 在顶部输入框粘贴 arXiv 链接，例如：
   ```
   https://arxiv.org/abs/2307.09288
   ```
   或直接输入 ID：
   ```
   2307.09288
   ```
2. 点击"提交"
3. 如果论文已存在，会提示并跳转
4. 左侧列表会出现新论文，状态为 `processing`
5. 约 10-30 秒后状态变为 `done`，点击即可查看报告

### 报告内容

生成的报告包含以下章节（中文）：
- **论文概览**：核心贡献 bullet points
- **研究背景与动机**：问题定义、相关工作
- **方法**：核心思路、关键公式（保留 `$...$`）
- **实验结果**：关键指标表格、与 SOTA 对比
- **伪代码**：算法流程（如有）
- **总结**：贡献、局限性、未来方向

### 失败重试

如果某篇论文处理失败（状态 `failed`），在阅读页右上角点击刷新图标即可重试。

---

## 5. 更换 LLM 模型

代码使用 OpenAI 兼容的 SDK，更换模型只需修改 `.env`：

| 厂商 | `MOONSHOT_BASE_URL` | `MOONSHOT_MODEL` |
|------|---------------------|------------------|
| **Kimi (默认)** | `https://api.moonshot.cn/v1` | `kimi-k2.5` |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat` |
| **智谱 GLM** | `https://open.bigmodel.cn/api/paas/v4/` | `glm-4` |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o` |

修改 `.env` 后，**重启后端**（`Ctrl+C` 后重新运行 `uvicorn`）即可生效。

**注意**：如果换到不兼容 OpenAI 格式的 API（如原生 Claude），需要修改 `backend/app/services/llm_service.py`。

---

## 6. Docker 部署（可选）

如果你后续想部署到服务器给全实验室用（不依赖 VSCode 转发）：

```bash
cd /home/tengshiyuan/code/arxiv-paper-web
docker compose up --build -d
```

访问 `http://<服务器IP>:8081`

（`docker-compose.yml` 中端口映射为 `8081:8000`，因为 8000 和 8080 可能已被占用）

---

## 项目结构

```
arxiv-paper-web/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── routers/papers.py    # REST API（提交/列表/详情/删除/重试）
│   │   ├── services/
│   │   │   ├── arxiv_service.py # 下载 arXiv + 图片提取
│   │   │   ├── latex_parser.py  # LaTeX 结构解析（复用你的 skill）
│   │   │   └── llm_service.py   # Kimi API 调用
│   │   └── ...
│   └── pyproject.toml           # uv 依赖管理
├── frontend/
│   ├── src/
│   │   ├── components/          # SubmitForm, PaperList, PaperViewer
│   │   └── pages/               # HomePage, PaperPage
│   └── package.json
├── Dockerfile
├── docker-compose.yml
└── .env
```

---

## 常见问题

**Q: 前端页面打不开？**
- 检查 VSCode 端口转发是否已添加 5173
- 检查 `npm run dev` 是否在运行
- 检查防火墙/安全组是否放行 5173（如果是直接公网访问）

**Q: 提交论文后一直显示 processing？**
- 检查后端 `uvicorn` 是否在运行
- 检查 `.env` 里的 `MOONSHOT_API_KEY` 是否有效
- 查看后端终端日志是否有报错

**Q: 图片显示不出来？**
- 图片存储在 `./data/images/{arxiv_id}/`
- 确保后端在运行，因为 `/images` 路由由后端提供

**Q: 公式显示为源码？**
- 确保网络能加载 `https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css`
- 如果是内网隔离环境，需要把 KaTeX CSS 下载到本地
