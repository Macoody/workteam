# WorkTeam / 徐东摆地摊服务器部署清单

这份清单用于把本地开发好的版本放到服务器上，让团队成员访问同一个线上地址。

## 1. 准备项目和配置

```bash
cd /opt/workteam    # 替换成服务器上的实际项目目录
git pull
cp .env.example .env
chmod 600 .env
```

生成生产环境 `SECRET_KEY`：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

编辑 `.env`，至少填好：

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@db.example.supabase.co:5432/postgres
SECRET_KEY=replace-with-a-long-random-string
BUSINESS_TIMEZONE=Asia/Shanghai
UPLOAD_DIR=/app/uploads
```

如果数据库密码里有 `@`、`#`、`:` 等特殊字符，请先做 URL 编码。

## 2. 构建并启动

```bash
docker compose up -d --build
docker compose logs -f backend
```

后端镜像会从根目录 `Dockerfile` 构建；前端镜像会从 `frontend/Dockerfile` 构建，不需要在服务器上手动提前生成 `frontend/dist`。

## 3. 健康检查

```bash
curl http://127.0.0.1:8001/health
```

期望返回：

```json
{"status":"ok","version":"1.0.0"}
```

## 4. 浏览器验证

打开：

```text
http://服务器IP:3000/login
```

依次检查：

- 登录
- 成员管理
- 项目列表
- 项目看板
- 新建任务
- 领取任务
- 延期
- 完成任务
- 文档编辑
- 任务关联文档

如果已经绑定域名，把域名反向代理到服务器前端端口 `3000`。

## 5. 运维注意

- `.env` 不要提交到仓库，也不要复制给无关人员。
- `uploads/` 是持久化上传目录，重启服务时不要删除。
- 换数据库或换服务器时，只需要更新 `.env` 并重启服务。
- 如果后端启动失败，优先看 `docker compose logs backend` 里的数据库连接和配置错误。
