# 徐东摆地摊团队协作平台

这是一个给小团队共用的项目协作系统，包含登录、成员、项目、看板、任务、文档和工作日志。

## 多人协作先读

如果是接手线上部署、服务器排查或多个 session 共同工作，请先读：

- `SERVER_README.md`：当前服务器、上线流程、验证、回滚和发布记录
- `HANDOFF_DEPLOY.md`：系统结构、业务规则和更完整的交接说明

## 本地开发

1. 复制环境变量样例并填写数据库和登录密钥：

```bash
cp .env.example .env
```

2. 启动后端：

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

如果本机 `8001` 已经被占用，可以换一个端口，例如：

```bash
uvicorn main:app --host 127.0.0.1 --port 8011 --reload
```

3. 启动前端：

```bash
cd frontend
npm install
npm run dev
```

后端端口不是 `8001` 时，同步指定前端代理目标：

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:8011 npm run dev
```

本地访问地址：`http://localhost:5173`

## 服务器部署

服务器上准备好 Docker 和 Docker Compose 后，在项目根目录放好 `.env`，然后执行：

```bash
docker compose up -d --build
```

默认访问地址：

- 前端：`http://服务器IP:3000`
- 后端健康检查：`http://服务器IP:8001/health`

上传文件会持久化在项目根目录的 `uploads/`，不要在重启服务时删除这个目录。
