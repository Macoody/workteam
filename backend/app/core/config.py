"""
应用配置
所有敏感配置（数据库连接、JWT 密钥）都从环境变量读取，不再硬编码。
本地开发请在项目根目录的 .env 文件中填入对应变量；.env 已被 .gitignore 忽略。
"""
import os
from urllib.parse import quote_plus
from pathlib import Path
from dotenv import load_dotenv

# 在模块加载时一次性读取 .env（仅在文件存在时生效；不影响容器内 env_file 注入）
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_BACKEND_ROOT / ".env")


class Settings:
    # 数据库连接 URL：优先读取 DATABASE_URL；如果服务器仍使用 DB_HOST/DB_USER 等变量，
    # 则自动拼 MySQL 连接串，兼容旧容器环境。
    # 示例: postgresql+psycopg://user:password@host:5432/dbname
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    if not DATABASE_URL and os.getenv("DB_HOST"):
        DB_HOST: str = os.getenv("DB_HOST", "")
        DB_PORT: str = os.getenv("DB_PORT", "3306")
        DB_USER: str = os.getenv("DB_USER", "root")
        DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
        DB_NAME: str = os.getenv("DB_NAME", "")
        DATABASE_URL = (
            f"mysql+pymysql://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
            f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )

    # JWT 配置
    # 启动时校验 SECRET_KEY 存在；如缺失则抛错，避免弱密钥意外上线
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))
    )

    # 文件上传目录（容器内默认 /app/uploads；本地开发用项目根目录下的 uploads）
    UPLOAD_DIR: str = os.getenv(
        "UPLOAD_DIR",
        str(_BACKEND_ROOT / "uploads"),
    )
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(100 * 1024 * 1024)))

    # 业务时区：datetime.now() 在业务代码里使用这个时区生成"本地时间"
    # 数据库统一存 TIMESTAMP WITH TIME ZONE，业务层假设写入时间为该时区
    BUSINESS_TIMEZONE: str = os.getenv("BUSINESS_TIMEZONE", "Asia/Shanghai")

    # 微信小程序登录配置。正式上线前把 AppID/AppSecret 配到服务器环境变量中；
    # 本地开发如需绕过微信 code2Session，可显式开启 WECHAT_DEV_LOGIN_ENABLED。
    WECHAT_MINI_APP_ID: str = os.getenv("WECHAT_MINI_APP_ID", "")
    WECHAT_MINI_APP_SECRET: str = os.getenv("WECHAT_MINI_APP_SECRET", "")
    WECHAT_DEV_LOGIN_ENABLED: bool = os.getenv(
        "WECHAT_DEV_LOGIN_ENABLED", "false"
    ).strip().lower() in {"1", "true", "yes", "on"}

    def validate(self) -> None:
        """启动时校验关键配置；失败则抛错，避免带病上线。"""
        if not self.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL 未配置。请在 .env 或环境变量中设置，例如：\n"
                "  DATABASE_URL=postgresql+psycopg://user:password@host:5432/dbname"
            )
        if not self.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY 未配置。出于安全考虑，禁止空密钥启动。"
                "请在 .env 或环境变量中设置一个足够长的随机字符串。"
            )


settings = Settings()
