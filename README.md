# PM Copilot Agent

## 功能简介

PM Copilot Agent 是一个面向产品方案工作的本地 Web 应用，支持知识库管理、Agent 规划、内外部调研、最终产品方案、业务流程图、交互原型和历史任务。

## 系统要求

- Git
- Python >= 3.10
- Node.js >= 20.19
- npm（随 Node.js 安装）

## 1. Clone

```powershell
git clone https://github.com/qikuansun-art/pm-copilot-agent.git
cd pm-copilot-agent
```

请将占位地址替换为项目实际 GitHub Clone URL。

## 2. Python 环境

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 3. 配置 .env

在项目根目录执行：

```powershell
Copy-Item .env.example .env
```

然后编辑根目录 `.env`，填写：

- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY`
- `LLM_BASE_URL`

`BACKEND_HOST`、`BACKEND_PORT` 和 `CORS_ORIGINS` 已提供本地开发默认值。不要提交包含真实密钥的 `.env`。

## 4. 启动 Backend

必须从项目根目录执行：

```powershell
uvicorn api.main:app --reload
```

启动后访问 API 文档：<http://127.0.0.1:8000/docs>

## 5. 安装 Frontend

打开另一个 PowerShell 终端：

```powershell
cd frontend
npm ci
```

## 6. Frontend 环境变量

在 `frontend` 目录执行：

```powershell
Copy-Item .env.example .env
```

默认配置为：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

如果后端地址发生变化，请同时检查根目录 `.env` 中的 `CORS_ORIGINS`。

## 7. 启动 Frontend

在 `frontend` 目录执行：

```powershell
npm run dev
```

打开：<http://localhost:5173/>

## 8. 日常启动

依赖安装完成后，不需要每次重新安装。

终端 1，在项目根目录：

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn api.main:app --reload
```

终端 2，在 `frontend` 目录：

```powershell
npm run dev
```

## 9. Git 同步

公司电脑开发完成后：

```powershell
git add .
git commit -m "..."
git push
```

家里电脑继续工作前：

```powershell
git pull
```

提交前请确认 `.env` 和本地数据库没有进入变更列表。

## 10. 本地数据

运行时会在项目 `data` 目录使用：

- `data/tasks.db`
- `data/knowledge.db`

它们默认不会上传 GitHub。新电脑首次运行会自动创建新的空数据库，项目启动不依赖旧电脑数据库。

Python 依赖目前由 `requirements.txt` 管理，后续建议增加 dependency lock，以提高跨机器构建的完全可复现性。

## 11. 常见问题

### A. `npm run dev` 提示找不到 package.json

请先进入前端目录：

```powershell
cd frontend
```

### B. `/docs` 打不开

确认 Backend 终端仍在运行，并检查是否从项目根目录执行了：

```powershell
uvicorn api.main:app --reload
```

### C. LLM 报配置错误

检查根目录 `.env` 中的 `LLM_PROVIDER`、`LLM_MODEL`、`LLM_API_KEY` 和 `LLM_BASE_URL`。

### D. 前端连不上后端

检查 `frontend/.env` 中的 `VITE_API_BASE_URL`，以及根目录 `.env` 中的 `CORS_ORIGINS`。修改前端环境变量后需要重新启动 Vite。

### E. PowerShell 不允许执行 Activate.ps1

可以只对当前 PowerShell 进程临时放开限制：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## New Computer Checklist

新电脑需要安装：

- Git
- Python >= 3.10
- Node.js >= 20.19（包含 npm）

需要从 GitHub 获取：

- 全部项目代码

需要手工配置：

- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY`
- `LLM_BASE_URL`

不需要从旧电脑复制：

- `.venv`
- `frontend/node_modules`
- `frontend/dist`
- `data/tasks.db`
- `data/knowledge.db`
