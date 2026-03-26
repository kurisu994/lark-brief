# lark-brief 前端

`frontend` 是 lark-brief 的 Web 控制台，基于 Next.js App Router，提供简报列表、详情查看、统计分析和全文搜索能力，并通过同源 API 代理与后端 FastAPI 通信。

## 技术栈

- Next.js 16（App Router）
- React 19 + TypeScript（`strict: true`）
- Tailwind CSS v4 + HeroUI v3
- Recharts（统计图表）
- next-themes（明暗主题切换）

## 功能概览

- 首页（`app/page.tsx`）
	- 展示简报运行记录列表（分页）
	- 展示 KPI（总期数、最新日期、最新新闻数、最新成功率）
	- 支持手动触发生成简报，并轮询生成状态
- 简报详情页（`app/brief/[date]/page.tsx`）
	- 读取当日 Markdown 简报内容并按时间线卡片渲染
	- 展示运行信息（状态、新闻数、成功源、耗时）
	- 展示各资讯源近期成功/失败情况
- 统计页（`app/stats/page.tsx`）
	- 展示总运行次数、平均成功率、平均耗时、平均新闻数
	- 展示新闻数趋势（柱状图）与成功率趋势（面积图）
	- 展示源健康度表格（含近期状态点阵）
- 搜索页（`app/search/page.tsx`）
	- 按关键词检索历史简报
	- 返回匹配日期、匹配次数和摘要片段
- 全局能力
	- 顶部导航（`components/navbar.tsx`）
	- 中英双语（`lib/i18n.tsx`，默认中文，localStorage 持久化）
	- 明暗主题切换（`app/providers.tsx` + `next-themes`）

## 目录结构

```text
frontend/
├── app/
│   ├── api/[...path]/route.ts      # 通用 API 代理（转发到后端）
│   ├── brief/[date]/page.tsx       # 简报详情页
│   ├── search/page.tsx             # 搜索页
│   ├── stats/page.tsx              # 统计页
│   ├── globals.css                 # 主题变量与全局样式
│   ├── layout.tsx                  # 根布局（Navbar + Providers）
│   ├── page.tsx                    # 首页
│   └── providers.tsx               # Theme + I18n Provider
├── components/
│   └── navbar.tsx                  # 顶部导航栏
├── lib/
│   ├── api.ts                      # API 类型与请求封装
│   └── i18n.tsx                    # 国际化实现
├── Dockerfile                      # 前端镜像（多阶段构建）
├── next.config.ts                  # Next.js 配置（standalone 输出）
└── package.json
```

## API 通信设计

前端默认通过同源 `/api/*` 请求数据，再由 Next.js Route Handler 代理到后端：

- 代理入口：`app/api/[...path]/route.ts`
- 后端地址：`BACKEND_URL`（默认 `http://localhost:8080`）

`lib/api.ts` 的请求基地址为：

- `NEXT_PUBLIC_API_URL` 未设置时：使用相对路径（推荐，走同源代理）
- `NEXT_PUBLIC_API_URL` 已设置时：直接请求指定地址（可绕过同源代理）

## 本地开发

在 `frontend` 目录执行：

```bash
pnpm install
pnpm dev
```

默认访问：`http://localhost:3000`

常用命令：

```bash
pnpm lint
pnpm build
pnpm start
```

## 环境变量

- `BACKEND_URL`
	- 用于 `app/api/[...path]/route.ts` 的服务端代理目标
	- 默认值：`http://localhost:8080`
- `NEXT_PUBLIC_API_URL`
	- 用于浏览器侧请求前缀
	- 默认空字符串（即同源）

## Docker 构建与运行

`Dockerfile` 采用三阶段构建：

1. `deps`：安装依赖（pnpm）
2. `builder`：执行 `pnpm build`
3. `runner`：仅拷贝 `standalone` 产物 + `public` + `.next/static`

运行容器默认监听：`3000`

## 样式与设计约定

- 全局设计令牌定义于 `app/globals.css` 的 CSS 变量（浅色与深色两套）
- 公共 UI 原子类如 `card`、`btn-primary`、`table-dark` 在同文件集中维护
- 页面采用卡片化布局，强调数据可读性与状态可视化

## 已实现 API 对应

`lib/api.ts` 已封装：

- `fetchBriefs` / `fetchBriefDetail`
- `fetchStatsOverview` / `fetchStatsTrend` / `fetchSourcesHealth`
- `searchBriefs`
- `triggerGenerate` / `fetchGenerateStatus`
