# 部署指南 — Comment Intelligence Studio

本文档提供将项目部署到公网的完整步骤。

---

## 架构概览

```
用户浏览器
    │
    ├── https://your-frontend.vercel.app   (前端，静态托管)
    │
    └── https://your-backend.onrender.com  (后端，FastAPI)

本地环境额外：
    └── http://localhost:5173  (前端开发服务器)
    └── http://localhost:8010  (后端 API 开发服务器)
```

---

## 第一步：准备密钥

> ⚠️ **安全警告**：不要把包含真实密钥的 `.env` 文件提交到 GitHub。

1. **B站 Cookie**（必须）
   - 打开 Chrome，登录 B站
   - 按 F12 → Network → 随便点一个 B站 API 请求
   - 在 Request Headers 里找到 `Cookie:` 字段
   - 复制完整 Cookie 值（很长，包含 `SESSDATA=` 等）

2. **YouTube API Key**（必须）
   - 打开 [Google Cloud Console](https://console.cloud.google.com/)
   - 新建项目 → 启用 **YouTube Data API v3**
   - 凭据 → 创建 API Key
   - 复制 Key

3. **OpenAI API Key**（可选，不影响基础功能）
   - 访问 [platform.openai.com](https://platform.openai.com/)
   - API Keys → 创建新密钥
   - 用于 AI 分析总结；不配置则使用本地规则

---

## 第二步：部署后端 → Render（推荐）

Render 比 Railway 更稳定，免费套餐足够日常使用。

### 2.1 上传代码到 GitHub

```bash
cd "d:\Cursor Demo\comment-intelligence-studio"

git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/comment-intelligence-studio.git
git push -u origin main
```

### 2.2 创建 Render Web Service

1. 打开 [render.com](https://render.com/) → Sign Up（用 GitHub 登录）
2. Dashboard → **New +** → **Web Service**
3. Connect your GitHub repo `comment-intelligence-studio`
4. 配置如下：

| 配置项 | 值 |
|--------|-----|
| Name | `comment-intelligence-backend` |
| Region | `Oregon` |
| Branch | `main` |
| Root Directory | 留空（仓库根目录） |
| Runtime | `Python 3.11` |
| Build Command | `pip install -r backend/requirements.txt` |
| Start Command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |

5. **Environment Variables**（点击 Add Environment Variable，逐条添加）：

| Key | Value |
|-----|-------|
| `YOUTUBE_API_KEY` | 你的 YouTube API Key |
| `BILIBILI_COOKIE` | 你的 B站 Cookie |
| `OPENAI_API_KEY` | 你的 OpenAI Key（可选） |
| `CORS_ORIGINS` | `https://your-frontend.vercel.app`（等前端部署完再填） |
| `PYTHON_VERSION` | `3.11` |

6. 点击 **Create Web Service**

### 2.3 等待构建（约 2~3 分钟）

构建日志会显示：
```
pip install -r backend/requirements.txt
   -> Installing collected packages: fastapi, uvicorn, ...
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
   Application startup complete.
```

### 2.4 记录后端地址

部署成功后，Render 会给你一个 URL：
```
https://comment-intelligence-backend.onrender.com
```

验证后端是否正常：
```
https://comment-intelligence-backend.onrender.com/api/health
```
应返回：
```json
{"ok": true, "jobs": 0}
```

---

## 第三步：部署前端 → Vercel

### 3.1 修改 `frontend/.env.production`

打开 `frontend/.env.production`，把 `https://comment-intelligence.onrender.com/api`
替换为你在第二步拿到的真实后端地址：

```env
VITE_API_BASE_URL=https://your-backend-xxxx.onrender.com/api
```

### 3.2 更新 Render 的 CORS_ORIGINS

回到 Render Dashboard → 你的 Web Service → Environment：

把 `CORS_ORIGINS` 改成你的 Vercel 域名（下一步会拿到）：

```
CORS_ORIGINS=https://your-frontend.vercel.app
```

### 3.3 Vercel 部署

**方式一：Vercel CLI（推荐，最简单）**

```bash
# 在项目根目录下，不是 frontend 下
cd "d:\Cursor Demo\comment-intelligence-studio"

# 安装 Vercel CLI
npm i -g vercel

# 登录（弹出浏览器）
vercel login

# 部署到预览环境
vercel

# 回答交互问题：
# ? Set up and deploy? <Yes>
# ? Which scope? <your-username>
# ? Link to existing project? <No>
# ? Project name? comment-intelligence-studio
# ? Directory? ./frontend
# ? Override settings? <No>

# 部署成功后会显示预览 URL，例如：
# https://comment-intelligence-studio.vercel.app

# 如果满意，部署到生产：
vercel --prod
```

**方式二：Vercel 网页（不需要 CLI）**

1. 打开 [vercel.com](https://vercel.com/) → Sign Up（GitHub 登录）
2. Import Project → 选择 `comment-intelligence-studio` 仓库
3. 配置：

| 配置项 | 值 |
|--------|-----|
| Framework Preset | `Vite` |
| Root Directory | `./frontend` |
| Build Command | `npm install && npm run build` |
| Output Directory | `dist` |
| Install Command | `npm install` |

4. **Environment Variables**：

| Key | Value |
|-----|-------|
| `VITE_API_BASE_URL` | `https://your-backend-xxxx.onrender.com/api` |

5. 点击 **Deploy**

### 3.4 记录前端地址

Vercel 部署完成后得到：
```
https://comment-intelligence-studio.vercel.app
```

这就是你的公网访问地址。

---

## 第四步：最终配置

### 4.1 回到 Render，更新 CORS_ORIGINS

Render Dashboard → Backend → Environment：

```
CORS_ORIGINS=https://comment-intelligence-studio.vercel.app
```

点击 **Save Changes**，Render 会自动重启后端。

### 4.2 添加 Vercel 到 CORS 白名单（备用）

如果用 Vercel 的自动分配的 `.vercel.app` 域名（带分支名），后端 `CORS_ORIGINS` 需要包含所有可能的子域名。

为了方便，可以设置通配符方式（Render 支持）：
```
CORS_ORIGINS=https://comment-intelligence-studio.vercel.app,https://comment-intelligence-studio-*.vercel.app
```

---

## 第五步：验证部署

用浏览器打开你的 Vercel 前端 URL：

```
https://comment-intelligence-studio.vercel.app
```

### 手动测试 API

```bash
# 测试健康检查
curl https://your-backend-xxxx.onrender.com/api/health

# 测试创建任务
curl -X POST https://your-backend-xxxx.onrender.com/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"urls":["https://www.bilibili.com/video/BV1GJ411x7h7"],"limit":5,"force_refresh":true,"include_replies":false}'
```

### 前端功能检查清单

- [ ] 页面正常加载，无白屏
- [ ] 输入 B站链接，点击"开始分析"
- [ ] 任务状态从"等待中"变为"抓取中"
- [ ] 完成后饼图展示立场分布
- [ ] JSON / Markdown / PDF 下载按钮可用
- [ ] 控制台无 CORS 报错
- [ ] 控制台无 JavaScript 报错

---

## 第六步：自定义域名（可选）

### Vercel 添加自定义域名

1. Vercel Dashboard → 你的项目 → Settings → Domains
2. 添加你的域名（如 `comment.example.com`）
3. 按提示在 DNS 添加 CNAME 记录
4. 等待验证通过（约 5 分钟）

### Render 自定义域名

1. Render Dashboard → 你的 Web Service → Settings → Custom Domains
2. 添加你的域名
3. DNS 添加 CNAME 指向 `comment-intelligence-backend.onrender.com`

---

## 本地开发指南

```bash
# 克隆后安装依赖
git clone https://github.com/YOUR_USERNAME/comment-intelligence-studio.git
cd comment-intelligence-studio

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install

# 启动后端（端口 8010）
cd ..
uvicorn backend.main:app --port 8010 --reload

# 启动前端（新终端）
cd frontend
npm run dev
```

前端开发服务器地址：`http://localhost:5173`

---

## 故障排查

### 1. CORS 报错

```
Access to fetch at 'https://backend.onrender.com/api/jobs' from origin
'https://frontend.vercel.app' has been blocked by CORS policy
```

**解决**：确认 Render 后端的环境变量 `CORS_ORIGINS` 包含你的 Vercel 域名，并重启后端。

### 2. 后端 500 错误

查看 Render 构建日志：
Dashboard → 你的 Web Service → Logs

常见原因：
- `YOUTUBE_API_KEY` 未设置
- `BILIBILI_COOKIE` 未设置（登录 B站后才能抓评论）
- 依赖安装失败（检查 `requirements.txt`）

### 3. 前端 API 请求超时

Render 免费套餐有冷启动（约 30 秒休眠）。第一次请求后端会等待唤醒，这是正常的。

### 4. B站评论抓取失败

检查：
- B站 Cookie 是否过期（Cookie 有时效，建议 30 天更新一次）
- Cookie 是否有 `SESSDATA` 字段
- B站视频是否为私有/删稿件

### 5. YouTube 429 配额超限

YouTube Data API 有每日配额（默认 10000 units/天）。超额后：
- 等待次日配额重置
- 申请更高配额（需要 Google Cloud Billing 绑定信用卡）

---

## 更新部署

代码更新后：

```bash
# 本地提交
git add .
git commit -m "Fix bug"
git push

# Vercel 自动检测到 GitHub push，自动重新部署
# Render 也可开启 Auto-Deploy from GitHub
```

---

## 费用说明

| 服务 | 套餐 | 限制 |
|------|------|------|
| Vercel | Hobby (免费) | 100GB 带宽/月，休眠不降级 |
| Render | Free | 冷启动 30s，15 分钟无活动休眠，750h/月 |
| Railway | Hobby (免费) | $5 免费额度/月，休眠后需手动唤醒 |
