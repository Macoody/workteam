# 徐东摆地摊 系统交接文档

这份文档给下一位接手的工具或工程师使用，目标是让对方在最短时间内理解：

- 这个项目是做什么的
- 当前代码结构和主要入口
- 已经完成过哪些改造
- 现在本地如何运行
- 部署到服务器时要注意什么

## 1. 项目概况

这是一个轻量团队协作系统，品牌名已经从 `WorkTeam` 改成了 `徐东摆地摊`。

核心功能：

- 用户登录 / 注册 / 当前用户信息
- 成员管理：新增、编辑、停用成员
- 项目管理：创建、编辑、删除项目
- 项目看板：按项目查看任务流转
- 任务管理：任务编辑、评论、附件、交付时间、延期、完成流转
- 文档中心：文档列表、文档编辑、分享、自动保存

当前产品方向已经明显偏向“项目 + 看板 + 节点化任务 + 文档沉淀”。

## 2. 技术栈

后端：

- FastAPI
- SQLAlchemy
- MySQL
- JWT 鉴权

前端：

- Vue 3
- Vite
- Pinia
- Vue Router
- Element Plus
- Tiptap 富文本编辑器

## 3. 代码结构

### 后端

主要目录：

- `/Users/mac/workteam/main.py`
- `/Users/mac/workteam/app/core`
- `/Users/mac/workteam/app/models`
- `/Users/mac/workteam/app/routers`
- `/Users/mac/workteam/app/schemas`

关键文件：

- `/Users/mac/workteam/main.py`
  后端应用入口，挂载路由、静态目录、数据库初始化

- `/Users/mac/workteam/app/core/config.py`
  当前数据库、JWT、上传目录配置

- `/Users/mac/workteam/app/core/database.py`
  数据库连接与运行时补列逻辑

- `/Users/mac/workteam/app/models/models.py`
  SQLAlchemy 模型定义

- `/Users/mac/workteam/app/schemas/schemas.py`
  Pydantic 请求 / 响应模型

- `/Users/mac/workteam/app/routers/auth.py`
  登录、注册、成员管理

- `/Users/mac/workteam/app/routers/projects.py`
  项目管理和默认看板列创建

- `/Users/mac/workteam/app/routers/kanban.py`
  看板查询、列操作、任务移动

- `/Users/mac/workteam/app/routers/tasks.py`
  任务 CRUD、评论、附件、延期、领取、完成流转

- `/Users/mac/workteam/app/routers/documents.py`
  文档 CRUD、分享、文件资产

### 前端

主要目录：

- `/Users/mac/workteam/frontend/src/views`
- `/Users/mac/workteam/frontend/src/components`
- `/Users/mac/workteam/frontend/src/assets`
- `/Users/mac/workteam/frontend/src/stores`
- `/Users/mac/workteam/frontend/src/api`
- `/Users/mac/workteam/frontend/src/router`

关键文件：

- `/Users/mac/workteam/frontend/src/components/AppShell.vue`
  统一后台壳子布局，侧边栏、头部、页面容器都在这里

- `/Users/mac/workteam/frontend/src/assets/main.css`
  全局样式主文件

- `/Users/mac/workteam/frontend/src/router/index.js`
  前端路由

- `/Users/mac/workteam/frontend/src/views/Dashboard.vue`
  总览页

- `/Users/mac/workteam/frontend/src/views/Projects.vue`
  项目页

- `/Users/mac/workteam/frontend/src/views/Kanban.vue`
  项目看板页

- `/Users/mac/workteam/frontend/src/views/Tasks.vue`
  任务列表页

- `/Users/mac/workteam/frontend/src/views/Documents.vue`
  文档中心列表

- `/Users/mac/workteam/frontend/src/views/DocEditor.vue`
  文档编辑器

- `/Users/mac/workteam/frontend/src/views/Members.vue`
  成员管理

## 4. 当前主要业务规则

### 4.1 项目默认列

项目创建后会自动创建 4 个看板列：

- `待处理`
- `进行中`
- `待验收`
- `已完成`

定义位置：

- `/Users/mac/workteam/app/routers/projects.py`

### 4.2 任务当前结构

任务现在不是“优先级型任务”，而是“节点化任务”。

目前核心字段：

- `title`
- `description`
  前端显示名称是“当前节点描述”
- `node_output`
  前端显示名称是“节点产出”
- `linked_document_id`
  可关联文档中心里的文档
- `assignee_id`
- `due_date`
  前端显示名称是“交付时间”
- `delivery_dates`
  保存原始交付时间和延期后的时间链
- `completed_by`
  保存谁点过“完成任务”

模型定义位置：

- `/Users/mac/workteam/app/models/models.py`

### 4.3 交付时间规则

- 第一次可以设置交付时间
- 一旦设置后，不能直接改原时间
- 只能通过“延期”功能增加新的时间
- 最多保留 5 个时间点
- 前端默认只显示交付时间
- 点击“延期”按钮后，才会展开“延期时间”控件

接口逻辑位置：

- `/Users/mac/workteam/app/routers/tasks.py`

前端交互位置：

- `/Users/mac/workteam/frontend/src/views/Kanban.vue`
- `/Users/mac/workteam/frontend/src/views/Tasks.vue`

### 4.4 完成任务规则

- 普通成员点击“完成任务”后，任务会自动移到 `待验收`
- 用户名为 `mac` 的用户点击“完成任务”后，任务会自动移到 `已完成`

接口位置：

- `/Users/mac/workteam/app/routers/tasks.py`

### 4.5 领取任务规则

- 在项目看板中打开任务后，有“领取任务”按钮
- 点击后会自动：
  - 把当前登录人设为负责人
  - 把任务移到 `进行中`

接口位置：

- `POST /api/tasks/{task_id}/claim`
- 实现文件：`/Users/mac/workteam/app/routers/tasks.py`

### 4.6 关联文档规则

任务中的“关联文档”下拉菜单，现在列出的是文档中心的文档。

注意：

- 目前很多老文档 `project_id` 是空
- 所以前端已经改成直接拉 `/documents`，不再只按项目过滤

相关文件：

- `/Users/mac/workteam/frontend/src/views/Kanban.vue`
- `/Users/mac/workteam/frontend/src/views/Tasks.vue`

## 5. 已完成的重要改造

下面这些都是已经做完的，不需要重复判断。

### 品牌与界面

- 品牌名由 `WorkTeam` 改成了 `徐东摆地摊`
- 新增了 `徐东` 的 SVG Logo
- 全站改成统一后台壳子布局
- 看板、项目、任务、文档、总览页的视觉风格已统一

涉及文件：

- `/Users/mac/workteam/frontend/src/components/AppShell.vue`
- `/Users/mac/workteam/frontend/src/assets/main.css`
- `/Users/mac/workteam/frontend/src/assets/logo-xudong.svg`
- `/Users/mac/workteam/frontend/index.html`
- `/Users/mac/workteam/index.html`
- `/Users/mac/workteam/main.py`

### 成员管理

- 新增成员管理页面
- 支持添加成员
- 支持编辑成员
- 支持停用成员
- 支持给每个成员分配固定颜色

涉及文件：

- `/Users/mac/workteam/app/routers/auth.py`
- `/Users/mac/workteam/frontend/src/views/Members.vue`
- `/Users/mac/workteam/frontend/src/utils/userColors.js`

### 项目管理

- 看板不再在左侧单独列出
- 从项目页进入看板
- 项目支持编辑
- 只有用户名 `mac` 可以删除项目

涉及文件：

- `/Users/mac/workteam/app/routers/projects.py`
- `/Users/mac/workteam/frontend/src/views/Projects.vue`
- `/Users/mac/workteam/frontend/src/components/AppShell.vue`

### 文档中心

- 文档编辑器改为 Tiptap `EditorContent` 方式
- 文档支持自动保存
- 去掉手动保存按钮
- 已登录成员可编辑文档
- 文档中支持成员颜色高亮

涉及文件：

- `/Users/mac/workteam/app/routers/documents.py`
- `/Users/mac/workteam/frontend/src/views/DocEditor.vue`
- `/Users/mac/workteam/frontend/package.json`

### 任务和看板

- 去掉优先级主导的交互
- 新建任务统一从看板右上角绿色按钮进入
- 新建任务默认进入 `待处理`
- 任务支持领取、延期、完成流转
- 看板页显示当前项目的大标题

涉及文件：

- `/Users/mac/workteam/app/routers/tasks.py`
- `/Users/mac/workteam/app/routers/kanban.py`
- `/Users/mac/workteam/frontend/src/views/Kanban.vue`
- `/Users/mac/workteam/frontend/src/views/Tasks.vue`

### 总览页

- 近期任务会显示：
  - 项目名称
  - 成员颜色标签
  - 当前状态
  - 交付时间
- 状态标签颜色已和看板列颜色统一

涉及文件：

- `/Users/mac/workteam/frontend/src/views/Dashboard.vue`

## 6. 当前本地运行方式

### 后端

本地推荐命令：

```bash
cd /Users/mac/workteam
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

健康检查：

- `http://127.0.0.1:8001/health`

### 前端

本地推荐命令：

```bash
cd /Users/mac/workteam/frontend
/opt/homebrew/bin/node ./node_modules/vite/bin/vite.js --host 127.0.0.1
```

访问地址：

- `http://127.0.0.1:5173`

说明：

- 本地曾遇到 Codex 自带 Node 的 Rollup 原生模块签名问题
- 当前使用你机器上的 Homebrew Node 来跑 Vite
- 前端构建命令已经验证通过

构建命令：

```bash
cd /Users/mac/workteam/frontend
/opt/homebrew/bin/node ./node_modules/vite/bin/vite.js build
```

## 7. 数据库与配置现状

当前配置文件：

- `/Users/mac/workteam/app/core/config.py`

里面现在直接写了：

- MySQL 地址
- 端口
- 用户名密码
- JWT Secret

这对本地开发是可用的，但对服务器部署不理想。

### 部署前建议立刻处理

建议接手人优先把以下内容改成环境变量：

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `SECRET_KEY`

否则存在：

- 凭据硬编码风险
- 切换服务器环境不方便
- 后续多环境部署困难

## 8. 数据库兼容逻辑

系统目前没有完整迁移工具，采用了“运行时补列”方式兼容已有数据库。

逻辑位置：

- `/Users/mac/workteam/app/core/database.py`

目前会自动检查并补这些列：

- `users.color`
- `tasks.node_output`
- `tasks.linked_document_id`
- `tasks.delivery_dates`
- `tasks.completed_by`

这意味着：

- 老库启动后也能自动兼容到当前代码
- 但长期看仍然建议补正式迁移方案，如 Alembic

## 9. 服务器部署参考

项目已有：

- `/Users/mac/workteam/Dockerfile`
- `/Users/mac/workteam/docker-compose.yml`
- `/Users/mac/workteam/frontend/nginx.conf`

### 现有容器结构

后端：

- Python 容器
- 对外端口映射 `8001:8000`

前端：

- Nginx 容器
- 对外端口映射 `3000:80`
- `/api` 和 `/uploads` 都代理到后端容器 `workteam_backend:8000`

### 部署大致步骤

1. 安装 Docker / Docker Compose
2. 在服务器拉取项目代码
3. 准备环境变量或先改配置文件
4. 构建前端
5. 构建后端镜像
6. 启动 `docker-compose`
7. 检查数据库连通性
8. 检查 `/health`
9. 检查前端登录、项目、看板、文档功能

### 推荐部署流程

前端：

```bash
cd /path/to/workteam/frontend
npm install
npm run build
```

后端镜像：

```bash
cd /path/to/workteam
docker build -t workteam-backend:latest .
```

启动：

```bash
cd /path/to/workteam
docker-compose up -d
```

### 需要接手人重点核对的点

- 服务器是否能访问当前 MySQL
- `app/core/config.py` 里的数据库地址是否仍然有效
- 服务器上是否要改为环境变量配置
- `frontend/dist` 是否先构建好
- Nginx 代理是否正常转发 `/api`
- `uploads` 目录是否有持久化
- 服务器开放端口是否与 `docker-compose.yml` 一致

## 10. 我建议接手人先做的事情

如果目标是“部署到服务器并稳定上线”，建议按下面顺序处理：

1. 先阅读这份文档
2. 检查 `/Users/mac/workteam/app/core/config.py`
3. 把数据库和密钥改成环境变量
4. 在服务器上验证 MySQL 连通
5. 本地或服务器重新构建前端
6. 用 Docker Compose 起服务
7. 完成基本功能回归：
   - 登录
   - 成员管理
   - 项目列表
   - 进入项目看板
   - 新建任务
   - 领取任务
   - 延期
   - 完成任务
   - 文档编辑
   - 任务关联文档

## 11. 当前已知的技术债

- 配置硬编码在 `app/core/config.py`
- 没有正式数据库迁移体系
- 前端主包体积较大，Vite build 会提示 chunk size 偏大
- 任务完成规则目前强依赖用户名 `mac`
- 文档与项目的绑定还不够严格，老数据里很多文档没有 `project_id`

## 12. 如果只让接手人读一份文档

请直接让对方先读：

- `/Users/mac/workteam/HANDOFF_DEPLOY.md`

读完这份文档，对方应该就能快速知道：

- 系统整体结构
- 我已经做过哪些改造
- 当前任务 / 看板 / 文档的业务规则
- 本地怎么跑
- 服务器部署时应该先处理哪些问题
