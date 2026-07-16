# 徐东摆地摊服务器交接 README

这份文档给后续多个 Codex session / 接手人共同阅读。每次开始线上相关工作，先读这里，再读 `HANDOFF_DEPLOY.md`。

## 1. 当前线上信息

- 应用服务器：`39.99.42.171`
- 线上访问域名：`http://new.xh-tech.top/login`
- 服务器部署目录：`/opt/workteam`
- 前端容器：`workteam_frontend`
- 后端容器：`workteam_backend`
- 前端端口：服务器 `3000 -> 80`
- 后端端口：服务器 `8001 -> 8000`
- 当前数据库：Supabase PostgreSQL
- 数据库主机：`db.gpurcghatfhuwgzenloy.supabase.co:5432`

不要把服务器密码、数据库密码、JWT 密钥写进这个文档。需要时从用户提供的临时上下文或本机安全备注里获取。

## 2. 先确认不要动错服务器

已知还有一台“马超生产 workteam”服务器，备注里明确写过不要动。除非用户明确授权，不要连接或修改那台生产服务器。

本项目当前应操作：

```bash
ssh root@39.99.42.171
cd /opt/workteam
```

## 3. 线上现状

当前服务器上的前端是 nginx 容器，静态目录通过宿主机挂载：

```text
/opt/workteam/workteam_dist -> /usr/share/nginx/html
```

容器检查：

```bash
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep workteam
docker inspect workteam_frontend --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'
```

后端健康检查：

```bash
curl http://127.0.0.1:8001/health
```

域名页面检查：

```bash
curl -fsS http://new.xh-tech.top/login | sed -n '1,40p'
```

## 4. 只发布前端页面改动

如果只改了 `frontend/src`、样式、Logo、前端路由等，不需要重建后端，也不要动数据库。

本地构建：

```bash
cd /Users/xiaohemacmini/dev/workteam/frontend
npm run build
```

打包前端产物：

```bash
cd /Users/xiaohemacmini/dev/workteam
tar -czf /tmp/workteam-frontend-dist.tar.gz -C frontend/dist .
```

上传到服务器：

```bash
scp /tmp/workteam-frontend-dist.tar.gz root@39.99.42.171:/tmp/workteam-frontend-dist.tar.gz
```

服务器上备份并替换：

```bash
cd /opt/workteam
stamp=$(date +%Y%m%d_%H%M%S)
mkdir -p backups
tar -czf "backups/workteam_dist_${stamp}.tar.gz" workteam_dist
find workteam_dist -mindepth 1 -maxdepth 1 -exec rm -rf {} +
tar -xzf /tmp/workteam-frontend-dist.tar.gz -C workteam_dist
docker restart workteam_frontend
rm -f /tmp/workteam-frontend-dist.tar.gz
```

验证：

```bash
curl -fsS http://new.xh-tech.top/login | grep 'index-'
curl -fsS http://new.xh-tech.top/api/auth/me
```

`/api/auth/me` 未登录时返回 `401` 是正常的，说明 API 代理到了后端。

## 5. 完整 Docker 发布

只有在后端代码、依赖、Dockerfile、nginx 配置或 compose 配置有变化时，才做完整发布。

服务器上执行：

```bash
cd /opt/workteam
docker compose up -d --build
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep workteam
curl http://127.0.0.1:8001/health
```

注意：

- 完整发布前先确认 `.env` 存在且正确。
- 不要覆盖 `.env`。
- 不要删除 `uploads/`。
- 不要随意重建或清空数据库。

## 6. 回滚前端

如果前端发布后页面异常，使用最近的备份回滚：

```bash
cd /opt/workteam
ls -lh backups/workteam_dist_*.tar.gz | tail
rm -rf workteam_dist.rollback
mkdir workteam_dist.rollback
tar -xzf backups/workteam_dist_YYYYMMDD_HHMMSS.tar.gz -C workteam_dist.rollback
find workteam_dist -mindepth 1 -maxdepth 1 -exec rm -rf {} +
cp -a workteam_dist.rollback/workteam_dist/. workteam_dist/
docker restart workteam_frontend
```

然后重新访问：

```bash
curl -fsS http://new.xh-tech.top/login | sed -n '1,40p'
```

## 7. 常见坑

- 公网 `8001` 可能因安全组或防火墙不通；优先用服务器内侧 `curl http://127.0.0.1:8001/health` 验证后端。
- 域名 `new.xh-tech.top` 应解析到 `39.99.42.171`。
- `/health` 是后端健康检查；域名走前端 nginx 时，业务接口通常从 `/api/...` 进入。
- 前端容器必须能通过 Docker 网络访问 `workteam_backend:8000`。
- 如果只改前端，优先静态发布，不要为了页面改动重启后端。
- 发布前后都要确认页面实际引用的新 `index-*.js` 和对应页面 bundle。

## 8. 多 session 协作记录规范

每个 session 做完线上相关工作后，在下面追加一条记录，写清楚：

- 日期时间
- 做了什么
- 改了哪些文件或服务
- 如何验证
- 是否留下风险或待办

### 发布记录

#### 2026-07-09

- 操作：更新首页、登录页和 Logo，并发布到 `39.99.42.171`。
- 主要文件：
  - `frontend/src/views/Dashboard.vue`
  - `frontend/src/views/Login.vue`
  - `frontend/src/assets/logo-xudong.svg`
  - `frontend/src/assets/main.css`
- 发布方式：本地 `npm run build`，上传 `frontend/dist`，替换 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 验证：
  - `http://new.xh-tech.top/login` 返回新构建 `index-DMVOwMnd.js`
  - 登录页 bundle 包含“项目摊位 / 任务货架 / 文档箱”
  - 服务器内侧 `curl http://127.0.0.1:8001/health` 返回 `{"status":"ok","version":"1.0.0"}`
  - `http://new.xh-tech.top/api/auth/me` 未登录返回 `401 Not authenticated`
- 备注：本次没有改数据库，没有重建后端。

#### 2026-07-09 在线状态

- 操作：新增成员在线状态。用户登录后前端每 30 秒发送心跳；关闭网页或退出登录会写离线；异常断开时后端按 90 秒心跳超时判离线。
- 主要文件：
  - `app/models/models.py`
  - `app/schemas/schemas.py`
  - `app/core/database.py`
  - `app/core/config.py`
  - `app/routers/auth.py`
  - `frontend/src/stores/auth.js`
  - `frontend/src/utils/presence.js`
  - `frontend/src/components/AppShell.vue`
  - `frontend/src/views/Members.vue`
  - `frontend/src/views/Dashboard.vue`
  - `frontend/src/views/Kanban.vue`
  - `frontend/src/views/Tasks.vue`
  - `frontend/src/views/WorkLogs.vue`
- 数据库变更：
  - `users.is_online`
  - `users.last_offline_time`
- 发布方式：
  - 前端：发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`。
  - 后端：服务器外网 `pip install` 很慢，没有重建依赖镜像；沿用旧 `workteam-backend:latest` 镜像，挂载 `/opt/workteam/workteam_backend:/app` 启动新代码容器。
- 验证：
  - `http://new.xh-tech.top/login` 返回新构建 `index-DReA2yUh.js`
  - `POST http://new.xh-tech.top/api/auth/presence/heartbeat` 未登录返回 `401 Not authenticated`
  - 前端 bundle 包含在线状态逻辑
  - 服务器内侧 `curl http://127.0.0.1:8001/health` 返回 `{"status":"ok","version":"1.0.0"}`
- 备注：
  - 线上当前实际后端容器依赖旧镜像 + 代码挂载，不是纯镜像内代码。后续如果要恢复纯镜像发布，建议先在服务器配置稳定的 pip 镜像源，再重建镜像。

#### 2026-07-09 手机适配

- 操作：优化手机端访问体验。小屏下侧边栏改为顶部身份栏 + 底部导航；首页卡片、看板、任务表格、成员页、日志页和登录页增加手机布局。
- 主要文件：
  - `frontend/src/assets/main.css`
  - `frontend/src/views/Dashboard.vue`
  - `frontend/src/views/Login.vue`
  - `frontend/src/views/Kanban.vue`
  - `frontend/src/views/Tasks.vue`
  - `frontend/src/views/Members.vue`
  - `frontend/src/views/WorkLogs.vue`
- 发布方式：本地 `npm run build`，只发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 验证：
  - 本地前端构建通过。
  - 线上登录页应返回新构建 `index-B6z29YgC.js` 和 `index-ox0TqATc.css`。
- 备注：本次没有改后端，没有改数据库。

#### 2026-07-10 mac 登录排查

- 操作：排查 `mac` 账号登录问题。账号存在且启用，密码哈希格式正常；线上登录日志有 `401 Unauthorized`，表示提交的密码不匹配。同步修复了几个容易让登录后体验异常的问题。
- 主要文件：
  - `app/core/database.py`
  - `app/routers/auth.py`
  - `app/routers/projects.py`
  - `app/routers/kanban.py`
  - `app/routers/documents.py`
  - `app/routers/worklogs.py`
  - `frontend/src/stores/auth.js`
  - `frontend/src/views/Login.vue`
- 修复内容：
  - 登录和注册用户名自动去掉前后空格。
  - 历史大写角色 `ADMIN` 也按管理员处理。
  - 补齐 `documents.last_editor_id` 运行时 schema，避免登录后首页/文档接口 500。
- 发布方式：
  - 后端：同步代码到 `/opt/workteam/workteam_backend` 并重启 `workteam_backend`。
  - 前端：发布 `frontend/dist` 到 `/opt/workteam/workteam_dist` 并重启 `workteam_frontend`。
- 备注：本次没有重置 `mac` 密码；如用户确认，可单独执行密码重置。

#### 2026-07-10 mac 密码重置

- 操作：按用户要求重置 `mac` 账号密码。
- 验证：
  - `POST /api/auth/login` 返回 `200`。
  - 返回用户为 `mac`，角色为 `admin`。
- 备注：不要在文档中记录明文密码。

#### 2026-07-10 在线状态前端修复

- 操作：修复成员在线状态显示异常。后端 `/api/auth/users` 已经会按心跳超时归一化 `is_online`，前端不再用浏览器本地时间和 `last_active_time` 二次判断，避免服务器时区与浏览器解析时区不一致导致在线成员显示为离线。
- 主要文件：
  - `frontend/src/utils/presence.js`
- 发布方式：本地 `npm run build`，只发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 验证：
  - 线上 `/api/auth/users` 可返回 `is_online: true` 的成员。
  - 前端构建通过。

#### 2026-07-10 文档标题修改

- 操作：文档中心增加标题修改能力。列表卡片增加“改名”，文档编辑页顶部增加标题输入和“保存标题”按钮。
- 主要文件：
  - `app/routers/documents.py`
  - `frontend/src/views/Documents.vue`
  - `frontend/src/views/DocEditor.vue`
- 发布方式：
  - 后端：同步 `app/routers/documents.py` 到 `/opt/workteam/workteam_backend` 并重启 `workteam_backend`。
  - 前端：发布 `frontend/dist` 到 `/opt/workteam/workteam_dist` 并重启 `workteam_frontend`。
- 验证：
  - 后端语法检查通过。
  - 前端构建通过。
  - 上线后用临时文档验证创建、改名、删除链路。

#### 2026-07-10 文档浏览记录聚合

- 操作：优化文档“浏览和编辑历史”。同一成员在 12 小时内多次浏览同一篇文档时，只显示最新一次浏览时间，并在“浏览”标签后显示本窗口内阅读次数，例如 `浏览（3）`。
- 主要文件：
  - `app/routers/documents.py`
  - `app/schemas/schemas.py`
  - `frontend/src/views/DocEditor.vue`
- 发布方式：
  - 后端：同步 `app/routers/documents.py` 和 `app/schemas/schemas.py` 到 `/opt/workteam/workteam_backend` 并重启 `workteam_backend`。
  - 前端：发布 `frontend/dist` 到 `/opt/workteam/workteam_dist` 并重启 `workteam_frontend`。
- 验证：
  - 后端语法检查通过。
  - 前端构建通过。
  - 本地聚合函数测试通过：同一用户 12 小时内浏览合并计数，超过 12 小时另起记录。

#### 2026-07-10 任务实际完成时间

- 操作：修复点击“完成任务”后仍显示期望交付时间的问题。新增任务实际完成时间字段 `tasks.completed_at`，点击完成时写入当前业务时间；待验收/已完成状态下页面优先显示“完成 MM-DD HH:mm”，交付时间记录继续保留原始/延期时间。
- 主要文件：
  - `app/models/models.py`
  - `app/schemas/schemas.py`
  - `app/core/database.py`
  - `app/routers/tasks.py`
  - `frontend/src/views/Kanban.vue`
  - `frontend/src/views/Tasks.vue`
  - `frontend/src/views/Dashboard.vue`
- 发布方式：
  - 后端：同步相关后端文件到 `/opt/workteam/workteam_backend` 并重启 `workteam_backend`，启动时自动补 `tasks.completed_at`。
  - 前端：发布 `frontend/dist` 到 `/opt/workteam/workteam_dist` 并重启 `workteam_frontend`。
- 验证：
  - 后端语法检查通过。
  - 前端构建通过。
  - 上线后用临时任务验证完成时间为点击完成时刻，交付时间保持原值。

#### 2026-07-10 已完成任务行样式

- 操作：任务列表中状态为“已完成”的整行增加浅绿色底色，并将主要文字调整为浅灰色，便于和未完成任务区分。
- 主要文件：
  - `frontend/src/views/Tasks.vue`
- 发布方式：本地 `npm run build`，只发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 验证：前端构建通过。

#### 2026-07-10 成员离线时间时区修复

- 操作：修复成员在线后离线时间显示为服务器 UTC 时间的问题。认证和在线状态写入统一使用业务时区 `Asia/Shanghai`，避免出现 `07-10 14:56` 这类比北京时间慢 8 小时的显示。
- 前端增强：
  - 增加 `pagehide` 和 `visibilitychange` 离线上报，提升手机切后台、关闭页面时的离线时间准确性。
  - 页面重新可见时立即补一次在线心跳。
- 主要文件：
  - `app/routers/auth.py`
  - `frontend/src/stores/auth.js`
- 发布方式：
  - 后端：同步 `app/routers/auth.py` 到 `/opt/workteam/workteam_backend` 并重启 `workteam_backend`。
  - 前端：发布 `frontend/dist` 到 `/opt/workteam/workteam_dist` 并重启 `workteam_frontend`。
- 验证：
  - 后端语法检查通过。
  - 业务时间函数返回北京时间。
  - 前端构建通过。
  - 上线后临时测试成员离线上报返回 `last_offline_time: 2026-07-10T23:07:30`，与当前北京时间一致。
  - 线上成员状态抽查：`mac` 的活跃时间和离线时间已写入北京时间。
- 备注：历史已写入的旧 UTC 离线时间不会自动批量改写；成员重新上线/离线或超时归一化后会写入新的北京时间。

#### 2026-07-10 成员任务、导航和时间修复综合发布

- 操作：发布本轮成员任务查看、任务列表状态/排序、文档时间修正、导航顺序和工作日志命名等改动。
- 主要文件：
  - `app/routers/documents.py`
  - `app/routers/tasks.py`
  - `app/schemas/schemas.py`
  - `frontend/src/components/AppShell.vue`
  - `frontend/src/router/index.js`
  - `frontend/src/views/Members.vue`
  - `frontend/src/views/Tasks.vue`
  - `frontend/src/views/WorkLogs.vue`
  - `frontend/src/data/versionHistory.js`
- 发布方式：
  - 后端：打包本地 `main.py`、`app/`、`requirements.txt`、`Dockerfile`，替换 `/opt/workteam/workteam_backend` 后重启 `workteam_backend`。
  - 前端：本地 `npm run build`，上传 `frontend/dist`，替换 `/opt/workteam/workteam_dist` 后重启 `workteam_frontend`。
- 服务器备份：
  - `backups/workteam_backend_20260710_232019.tar.gz`
  - `backups/workteam_dist_20260710_232019.tar.gz`
- 验证：
  - 本地后端语法检查通过。
  - 本地前端构建通过。
  - 服务器内侧 `curl http://127.0.0.1:8001/health` 返回 `{"status":"ok","version":"1.0.0"}`。
  - 线上 `http://new.xh-tech.top/login` 返回新构建 `index-BlyhLO5R.js`。
  - 线上版本包包含 `v0.10` 和“导航名称和顺序调整”。
  - 线上 `AppShell` 包中 `/logs` 位于 `/versions` 前，显示为“工作日志 / 版本更新”。
  - `http://new.xh-tech.top/api/auth/me` 未登录返回 `401 Not authenticated`，接口代理正常。
- 备注：本次未修改 `.env`，未删除 `uploads/`，未清空或重建数据库。

#### 2026-07-10 总览我的任务统计拆分

- 操作：总览页“我的任务”统计不再显示未完成和已完成的总和，改为拆分显示“未完成”和“已完成”，并突出未完成数量、弱化已完成任务。
- 主要文件：
  - `frontend/src/views/Dashboard.vue`
  - `frontend/src/data/versionHistory.js`
- 发布方式：本地 `npm run build`，只发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 服务器备份：
  - `backups/workteam_dist_20260710_233043.tar.gz`
- 验证：
  - 本地前端构建通过。
  - 线上 `http://new.xh-tech.top/login` 返回新构建 `index-CmfvyurY.js`。
  - 线上版本包包含 `v0.11` 和“总览我的任务统计拆分”。
  - 线上 Dashboard 包和 CSS 包包含 `my-task-stat-open`、`my-task-stat-done` 等统计拆分样式。
  - `http://new.xh-tech.top/api/auth/me` 未登录返回 `401 Not authenticated`，接口代理正常。
- 备注：本次没有改后端，没有改数据库。

#### 2026-07-10 项目卡片显示未完成负责人

- 操作：项目列表卡片取消“创建于”日期，改为展示项目内未完成任务的负责人名单，方便在外层快速看到项目里有哪些人有任务。
- 主要文件：
  - `frontend/src/views/Projects.vue`
  - `frontend/src/data/versionHistory.js`
- 发布方式：本地 `npm run build`，只发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 服务器备份：
  - `backups/workteam_dist_20260710_233908.tar.gz`
- 验证：
  - 本地前端构建通过。
  - 线上 `http://new.xh-tech.top/login` 返回新构建 `index-BkSBpk1h.js`。
  - 线上版本包包含 `v0.12` 和“项目卡片显示未完成负责人”。
  - 线上 Projects 包包含“未完成负责人”，且不再包含“创建于”。
  - `http://new.xh-tech.top/api/auth/me` 未登录返回 `401 Not authenticated`，接口代理正常。
- 备注：本次没有改后端，没有改数据库。

#### 2026-07-11 文档中心搜索

- 操作：文档中心新增搜索功能，可按文档标题和正文内容搜索。
- 主要文件：
  - `app/routers/documents.py`
  - `frontend/src/views/Documents.vue`
  - `frontend/src/data/versionHistory.js`
- 发布方式：
  - 后端：备份并同步 `app/routers/documents.py` 到 `/opt/workteam/workteam_backend/app/routers/documents.py`，容器内语法检查通过后重启 `workteam_backend`。
  - 前端：本地 `npm run build`，发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 服务器备份：
  - `backups/workteam_documents_router_20260711_125540.tar.gz`
  - `backups/workteam_dist_20260711_125540.tar.gz`
- 验证：
  - 本地后端语法检查通过。
  - 本地前端构建通过。
  - 服务器内侧 `curl http://127.0.0.1:8001/health` 返回 `{"status":"ok","version":"1.0.0"}`。
  - 线上 `http://new.xh-tech.top/login` 返回新构建 `index-DH86Stsy.js`。
  - 线上版本包包含 `v0.16` 和“文档中心搜索”。
  - 线上 Documents 包包含“搜索标题或内容”。
  - `http://new.xh-tech.top/api/documents?q=test` 未登录返回 `401 Not authenticated`，接口代理正常。
- 备注：本次没有改数据库。

#### 2026-07-10 全系统业务时间统一北京时间

- 操作：排查后端、数据库连接、前端展示和前端提交时间，用户可见和业务记录统一使用 `Asia/Shanghai`。
- 后端修正：
  - 新增统一业务时间工具 `app/core/timezone.py`。
  - 数据库连接启动时设置会话时区：PostgreSQL 使用 `Asia/Shanghai`，MySQL/MariaDB 使用 `+08:00`。
  - 模型默认 `created_at`、`updated_at`、评论、附件、文档活动、工作日志等时间由后端按北京时间生成，数据库 `CURRENT_TIMESTAMP/now()` 只作为兜底。
  - 任务交付时间、延期时间、完成时间、文档编辑/浏览时间、成员在线/离线时间、工作日志日期都在后端归一为北京时间。
  - API 返回的成员、项目、任务、文档、工作日志、附件、评论等时间字段统一转成北京时间。
- 前端修正：
  - 新增 `frontend/src/utils/time.js`，所有时间展示按北京时间格式化。
  - 任务和看板的交付/延期时间提交不再使用 `toISOString()`，避免被转成 UTC。
  - 首页、成员、任务、看板、文档、项目、工作日志的时间排序和展示改为北京时间。
  - 工作日志“今天”和提交时间按北京时间计算。
- 主要文件：
  - `app/core/timezone.py`
  - `app/core/database.py`
  - `app/models/models.py`
  - `app/routers/auth.py`
  - `app/routers/tasks.py`
  - `app/routers/documents.py`
  - `app/routers/worklogs.py`
  - `app/routers/projects.py`
  - `app/services/recurring_tasks.py`
  - `frontend/src/utils/time.js`
  - `frontend/src/utils/presence.js`
  - `frontend/src/views/Dashboard.vue`
  - `frontend/src/views/DocEditor.vue`
  - `frontend/src/views/Documents.vue`
  - `frontend/src/views/Kanban.vue`
  - `frontend/src/views/Members.vue`
  - `frontend/src/views/Projects.vue`
  - `frontend/src/views/Tasks.vue`
  - `frontend/src/views/WorkLogs.vue`
- 发布方式：
  - 后端：同步上述后端文件到 `/opt/workteam/workteam_backend` 并重启 `workteam_backend`。
  - 前端：发布 `frontend/dist` 到 `/opt/workteam/workteam_dist` 并重启 `workteam_frontend`。
- 服务器备份：
  - `backups/workteam_backend_before_beijingtime_20260710_233157.tar.gz`
  - `backups/workteam_dist_before_beijingtime_20260710_233157.tar.gz`
- 验证：
  - 后端语法检查通过。
  - 北京时间工具验证：`UTC 2026-07-10 15:00` 会转为 `2026-07-10 23:00`。
  - 前端构建通过。
  - 线上后端健康检查返回 `{"status":"ok","version":"1.0.0"}`。
  - 线上后端 `business_now` 返回 `2026-07-10 23:32:26`，数据库 `SELECT NOW()` 返回 `2026-07-10 23:32:28`。
  - 线上前端入口为新构建 `index-CmfvyurY.js`。
  - 线上接口验证：通过任务创建接口提交 `2026-07-10T15:00:00Z`，返回 `due_date: 2026-07-10T23:00:00`、`delivery_dates[0]: 2026-07-10T23:00:00`。
  - 临时测试用户、项目、任务已清理。
- 备注：JWT 登录令牌的 `exp` 仍使用 UTC，这是协议内部安全时间，不展示给用户，也不参与业务时间显示。

#### 2026-07-15 数字员工管理板块

- 操作：新增数字员工项目管理，集中记录 AI 手机资产、客户信息、付款信息、关联手机和服务跟进。
- 主要文件：
  - `app/models/models.py`
  - `app/schemas/schemas.py`
  - `app/routers/digital_employees.py`
  - `main.py`
  - `frontend/src/views/DigitalEmployees.vue`
  - `frontend/src/components/AppShell.vue`
  - `frontend/src/router/index.js`
  - `frontend/src/data/versionHistory.js`
- 数据库变更：
  - 新增 `digital_phones`
  - 新增 `digital_customers`
  - 新增 `digital_service_items`
  - 新增 `digital_service_records`
  - 预置默认服务项：人设录入、数字人录入、声音克隆。
- 发布方式：
  - 后端：备份 `/opt/workteam/workteam_backend`，发布新后端代码，容器内语法检查和路由加载检查通过后重启 `workteam_backend`。
  - 前端：本地 `npm run build`，发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 服务器备份：
  - `backups/workteam_backend_20260715_193319.tar.gz`
  - `backups/workteam_dist_20260715_193319.tar.gz`
- 验证：
  - 本地后端语法检查通过。
  - 本地前端构建通过。
  - 服务器内侧 `curl http://127.0.0.1:8001/health` 返回 `{"status":"ok","version":"1.0.0"}`。
  - 容器内 `digital_employees` 路由加载到 14 个接口。
  - 线上 `/api/digital-employees/overview` 未登录返回 `401 Not authenticated`，说明新接口已注册并进入认证链路。
  - 线上 `/digital-employees` 返回新构建 `index-BaehEgDv.js`。
  - 线上前端包包含“数字员工”和版本 `v0.17`。
  - 容器内确认四张新表均已存在。
- 备注：本次没有覆盖 `.env`，没有删除 `uploads/`。

#### 2026-07-15 手机颜色下拉选择

- 操作：数字员工登记/编辑手机时，颜色由手动输入改为下拉选择。
- 主要文件：
  - `frontend/src/views/DigitalEmployees.vue`
  - `frontend/src/data/versionHistory.js`
- 发布方式：
  - 前端：本地 `npm run build`，发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 服务器备份：
  - `backups/workteam_dist_20260715_215637.tar.gz`
- 验证：
  - 本地前端构建通过。
  - 线上 `http://new.xh-tech.top/login` 返回新构建 `index-i_mBfGWM.js`。
  - 线上 DigitalEmployees 包包含“请选择颜色”和“白色”。
  - 线上版本包包含 `v0.20`。
  - 服务器内侧 `curl http://127.0.0.1:8001/health` 返回 `{"status":"ok","version":"1.0.0"}`。
- 备注：本次只改前端，没有改数据库。

#### 2026-07-16 客户设备号记录

- 操作：数字员工客户管理新增“设备号”字段，并支持列表展示和搜索。
- 主要文件：
  - `app/models/models.py`
  - `app/schemas/schemas.py`
  - `app/core/database.py`
  - `app/routers/digital_employees.py`
  - `frontend/src/views/DigitalEmployees.vue`
  - `frontend/src/data/versionHistory.js`
- 数据库变更：
  - `digital_customers.device_number`
- 发布方式：
  - 后端：备份并发布后端代码，容器内语法检查通过后重启 `workteam_backend`。
  - 前端：本地 `npm run build`，发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 服务器备份：
  - `backups/workteam_backend_20260716_130211.tar.gz`
  - `backups/workteam_dist_20260716_130211.tar.gz`
- 验证：
  - 本地后端语法检查通过。
  - 本地前端构建通过。
  - 服务器内侧 `curl http://127.0.0.1:8001/health` 返回 `{"status":"ok","version":"1.0.0"}`。
  - 容器内确认 `digital_customers.device_number` 已存在。
  - 线上 DigitalEmployees 包包含“设备号”。
  - 线上版本包包含 `v0.21`。
  - 线上 `/api/digital-employees/customers` 未登录返回 `401 Not authenticated`，接口认证链路正常。
- 备注：本次没有覆盖 `.env`，没有删除 `uploads/`。

#### 2026-07-15 手机型号下拉选择

- 操作：数字员工登记/编辑手机时，手机型号由手动输入改为下拉选择。
- 主要文件：
  - `frontend/src/views/DigitalEmployees.vue`
  - `frontend/src/data/versionHistory.js`
- 发布方式：
  - 前端：本地 `npm run build`，发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 服务器备份：
  - `backups/workteam_dist_20260715_202020.tar.gz`
- 验证：
  - 本地前端构建通过。
  - 线上 `http://new.xh-tech.top/login` 返回新构建 `index-ZZe90rWo.js`。
  - 线上 DigitalEmployees 包包含 `Redmi note 15 pro` 和“请选择手机型号”。
  - 线上版本包包含 `v0.18`。
  - 服务器内侧 `curl http://127.0.0.1:8001/health` 返回 `{"status":"ok","version":"1.0.0"}`。
- 备注：本次只改前端，没有改数据库。

#### 2026-07-15 手机激活码记录

- 操作：数字员工手机登记/编辑新增“激活码”字段，并在手机列表绑定信息中展示。
- 主要文件：
  - `app/models/models.py`
  - `app/schemas/schemas.py`
  - `app/core/database.py`
  - `app/routers/digital_employees.py`
  - `frontend/src/views/DigitalEmployees.vue`
  - `frontend/src/data/versionHistory.js`
- 数据库变更：
  - `digital_phones.activation_code`
- 发布方式：
  - 后端：备份并发布后端代码，容器内语法检查通过后重启 `workteam_backend`。
  - 前端：本地 `npm run build`，发布 `frontend/dist` 到 `/opt/workteam/workteam_dist`，重启 `workteam_frontend`。
- 服务器备份：
  - `backups/workteam_backend_20260715_202552.tar.gz`
  - `backups/workteam_dist_20260715_202552.tar.gz`
- 验证：
  - 本地后端语法检查通过。
  - 本地前端构建通过。
  - 服务器内侧 `curl http://127.0.0.1:8001/health` 返回 `{"status":"ok","version":"1.0.0"}`。
  - 容器内确认 `digital_phones.activation_code` 已存在。
  - 线上 DigitalEmployees 包包含“激活码”。
  - 线上版本包包含 `v0.19`。
  - 线上 `/api/digital-employees/phones` 未登录返回 `401 Not authenticated`，接口认证链路正常。
- 备注：本次没有覆盖 `.env`，没有删除 `uploads/`。
