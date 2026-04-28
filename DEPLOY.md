# ViewLens 部署指南

本文档说明如何将 ViewLens 前后端部署到云端服务。

## 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    Vercel Frontend                      │
│  https://comment-intelligence-studio-xxx.vercel.app   │
└─────────────────────┬───────────────────────────────────┘
                      │ HTTP 请求 (API 调用)
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   Render Backend                         │
│  https://comment-intelligence-backend.onrender.com      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  FastAPI     │  │  评论抓取    │  │  AI 分析     │  │
│  │  (端口 8010) │  │  B站/YouTube│  │  OpenAI API  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 一、部署后端到 Render

### 1. 创建 Render 账号

访问 [render.com](https://render.com) 并注册账号（可用 GitHub 登录）。

### 2. 连接 GitHub 仓库

1. 在 Render Dashboard 点击 "New +" → "Web Service"
2. 选择你的 GitHub 仓库
3. 配置以下设置：

| 配置项 | 值 |
|--------|-----|
| Name | `comment-intelligence-backend` |
| Region | Oregon (或离你最近的) |
| Branch | `main` |
| Root Directory | `backend` |
| Runtime | Python 3.11 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |

### 3. 配置环境变量

在 Render 控制台添加以下环境变量（点击 "Environment" → "Add Environment Variable"）：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `OPENAI_API_KEY` | `sk-xxxxx` | OpenAI API 密钥（从 openai.com 获取） |
| `OPENAI_BASE_URL` | `https://turingai.plus/v1` | API 中转地址（如果使用中转） |
| `OPENAI_MODEL` | `gpt-4o-mini` | 默认模型 |
| `YOUTUBE_API_KEY` | `AIza...` | YouTube API 密钥（可选，用于 YouTube 视频） |
| `BILIBILI_COOKIE` | `buvid3=xxx` | B站 Cookie（用于抓取 B站评论） |
| `CORS_ORIGINS` | 见下方 | 允许的前端域名 |

**CORS_ORIGINS 值（重要！）**：

```
https://comment-intelligence-studio-zhangjie12500s-projects.vercel.app,http://localhost:5173,http://127.0.0.1:5173
```

> 注意：将第一个域名替换为你实际的 Vercel 前端地址。

### 4. 部署

1. 点击 "Create Web Service"
2. 等待构建完成（约 2-3 分钟）
3. 部署成功后，访问 `https://comment-intelligence-backend.onrender.com/api/health` 确认后端正常运行

### 5. 验证后端

```bash
# 健康检查
curl https://comment-intelligence-backend.onrender.com/api/health

# AI 健康检查
curl https://comment-intelligence-backend.onrender.com/api/ai/health
```

## 二、部署前端到 Vercel

### 1. 创建 Vercel 账号

访问 [vercel.com](https://vercel.com) 并注册账号（可用 GitHub 登录）。

### 2. 导入项目

1. 点击 "New Project"
2. 选择你的 GitHub 仓库
3. 配置以下设置：

| 配置项 | 值 |
|--------|-----|
| Framework Preset | Vite |
| Root Directory | `./` 或 `frontend` |
| Build Command | `npm run build` |
| Output Directory | `dist` |

### 3. 配置环境变量

在 Vercel 控制台点击 "Environment Variables" 添加：

| 变量名 | 值 |
|--------|-----|
| `VITE_API_BASE_URL` | `https://comment-intelligence-backend.onrender.com/api` |

> 注意：将 URL 替换为你实际的 Render 后端地址（不带末尾斜杠）。

### 4. 部署

1. 点击 "Deploy"
2. 等待部署完成
3. 访问你获得的 Vercel URL 确认部署成功

## 三、测试清单

部署完成后，按以下顺序测试：

### 1. 测试后端健康检查

在浏览器中打开：
```
https://comment-intelligence-backend.onrender.com/api/health
```

应返回：
```json
{"status": "ok", "service": "ViewLens backend", "jobs": 0}
```

### 2. 测试 AI 健康检查

```
https://comment-intelligence-backend.onrender.com/api/ai/health
```

应返回（如果配置了 OpenAI API Key）：
```json
{"enabled": true, "model": "gpt-4o-mini", "status": "ok"}
```

或（如果未配置）：
```json
{"enabled": false, "error": "OPENAI_API_KEY 未配置", "status": "error"}
```

### 3. 测试 Vercel 前端

1. 打开你的 Vercel 前端 URL
2. 输入一个视频链接测试分析功能
3. 打开浏览器 DevTools → Network，确认请求地址不是 localhost，而是 Render 后端地址

### 4. 验证跨域请求

如果请求成功，说明 CORS 配置正确。如果失败，检查：
- 后端 `CORS_ORIGINS` 是否包含你的 Vercel 前端地址
- Render 部署日志中是否有 CORS 相关错误

## 四、本地开发

### 启动后端

```bash
cd comment-intelligence-studio
cd backend

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env
# 编辑 .env 填入你的 API Key

# 启动后端
python -m uvicorn backend.main:app --port 8010 --reload
```

### 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 本地环境变量

前端 `.env.development` 已配置本地后端地址：
```
VITE_API_BASE_URL=http://localhost:8010/api
```

## 五、常见问题

### Q: 后端显示 "OPENAI_API_KEY 未配置"？

确保在 Render 环境变量中正确配置了 `OPENAI_API_KEY`。

### Q: 前端提示 "无法连接云端后端服务"？

1. 检查 Render 后端是否正常运行
2. 检查 Vercel 的 `VITE_API_BASE_URL` 是否正确配置
3. 检查后端 `CORS_ORIGINS` 是否包含你的 Vercel 前端地址
4. Redeploy 前端（在 Vercel 控制台点击 "Redeploy"）

### Q: B站评论抓取失败？

1. 检查 `BILIBILI_COOKIE` 是否配置
2. Cookie 是否过期（需要定期更新）
3. 检查 B站账号是否被限制

### Q: YouTube 评论抓取失败？

1. 检查 `YOUTUBE_API_KEY` 是否配置
2. 检查 API Key 是否有 YouTube Data API v3 权限
3. 检查 API 配额是否用尽

### Q: 免费版 Render 休眠？

Render 免费版在 15 分钟无活动后会休眠，唤醒需要 30 秒 - 1 分钟。首次请求时会有冷启动延迟。

## 六、环境变量速查表

### Render 后端环境变量

| 变量名 | 是否必需 | 说明 |
|--------|----------|------|
| `OPENAI_API_KEY` | 推荐 | OpenAI API 密钥 |
| `OPENAI_BASE_URL` | 可选 | API 中转地址 |
| `OPENAI_MODEL` | 可选 | 模型名称，默认 gpt-4o-mini |
| `YOUTUBE_API_KEY` | YouTube 必需 | YouTube API v3 密钥 |
| `BILIBILI_COOKIE` | B站必需 | B站登录 Cookie |
| `CORS_ORIGINS` | 必须 | 允许的前端域名 |
| `PORT` | 自动 | Render 自动提供 |

### Vercel 前端环境变量

| 变量名 | 是否必需 | 说明 |
|--------|----------|------|
| `VITE_API_BASE_URL` | 必须 | 后端 API 地址 |

## 七、修改后重新部署

### 重新部署后端

Render 会自动检测 Git 推送并重新部署。如需手动触发：
1. 登录 Render Dashboard
2. 点击你的后端服务
3. 点击 "Manual Deploy" → "Deploy latest commit"

### 重新部署前端

1. 登录 Vercel Dashboard
2. 点击你的前端项目
3. 点击 "Deployments" → 选择最新部署旁边的 "..." → "Redeploy"

> 注意：修改环境变量后必须重新部署才能生效！
