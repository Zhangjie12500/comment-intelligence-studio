# Comment Intelligence Studio

Bilibili & YouTube 评论智能分析平台。输入视频链接，自动抓取评论并生成分析报告。

## 架构

```
comment-intelligence-studio/
├── backend/          # FastAPI 后端 (端口 8010)
│   ├── main.py
│   ├── routes/jobs.py
│   ├── services/
│   └── storage/      # 任务数据持久化
├── frontend/         # React + Vite 前端 (端口 5173)
│   ├── src/
│   │   ├── lib/api.js        # API 客户端
│   │   ├── components/       # UI 组件
│   │   └── App.jsx           # 主应用
│   └── vite.config.js
├── .env              # 项目根目录 .env（优先级最高）
└── start_backend.bat # Windows 后端启动脚本
```

## 环境配置

在项目根目录（与 backend/ 平级）创建 `.env` 文件：

```env
# 必须（至少配置一个）
BILIBILI_COOKIE=your_bilibili_cookie_here

# 可选（YouTube 支持）
YOUTUBE_API_KEY=your_youtube_api_v3_key_here

# 可选（AI 分析功能）
OPENAI_API_KEY=your_openai_api_key_here
```

**说明：**
- 根目录 `.env` 优先级最高
- `backend/.env` 作为兜底
- 至少需要 `BILIBILI_COOKIE` 才能抓取 B站评论
- YouTube 评论需要 `YOUTUBE_API_KEY`

## 启动后端

**方式一：双击运行**
```
start_backend.bat
```

**方式二：命令行**
```bash
cd comment-intelligence-studio
python -m uvicorn backend.main:app --port 8010
```

后端地址：`http://127.0.0.1:8010`

健康检查：
```bash
curl http://127.0.0.1:8010/api/health
```

## 启动前端

```bash
cd comment-intelligence-studio/frontend
npm install   # 仅首次或依赖变更时
npm run dev
```

前端地址：`http://localhost:5173`

## API 测试

### 创建任务

```bash
curl -X POST http://127.0.0.1:8010/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"urls":["https://www.bilibili.com/video/BV1xx411c7XD"],"limit":20,"force_refresh":false,"include_replies":true}'
```

### 查询任务

```bash
# 替换 YOUR_JOB_ID
curl http://127.0.0.1:8010/api/jobs/YOUR_JOB_ID
```

### B站测试

```python
import requests, time
BASE = 'http://127.0.0.1:8010'
URLS = ['https://www.bilibili.com/video/BV1GJ411x7h7']
r = requests.post(f'{BASE}/api/jobs', json={'urls': URLS, 'limit': 20, 'force_refresh': True, 'include_replies': True})
job_id = r.json()['job_id']
for _ in range(60):
    j = requests.get(f'{BASE}/api/jobs/{job_id}').json()
    if all(t['status'] in ('done','failed') for t in j['tasks']): break
    time.sleep(2)
print(j)
```

### YouTube 测试

```python
import requests, time
BASE = 'http://127.0.0.1:8010'
URLS = ['https://www.youtube.com/watch?v=dQw4w9WgXcQ']
r = requests.post(f'{BASE}/api/jobs', json={'urls': URLS, 'limit': 20, 'force_refresh': True, 'include_replies': True})
job_id = r.json()['job_id']
for _ in range(90):
    j = requests.get(f'{BASE}/api/jobs/{job_id}').json()
    if all(t['status'] in ('done','failed') for t in j['tasks']): break
    time.sleep(2)
print(j)
```

## 前端功能

- 多链接输入（B站 + YouTube，每行一个）
- 参数配置（limit / force_refresh / include_replies）
- 任务状态实时轮询（每 2 秒）
- Task 卡片展示（platform / video_id / status / source / counts / error）
- 下载按钮（JSON / Markdown / PDF）
- 分析结果展示（Stance Chart / Top Comments / Clusters / Controversies）
- 错误信息顶部醒目展示

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | React 19 + Vite 6 |
| CSS | Tailwind CSS v4 |
| 图表 | Apache ECharts |
| 图标 | Lucide React |
| 后端 | FastAPI + Uvicorn |
| 爬虫 | yt-dlp + requests |
