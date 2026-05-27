"""
配置文件
"""
import os

class Settings:
    # 数据库
    DB_HOST = "8.149.232.175"
    DB_PORT = 58306
    DB_USER = "root"
    DB_PASSWORD = "Pwhpr7fe5V14ljC69RIMz8H5R1zTogFh"
    DB_NAME = "machao_workteam"
    DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

    # JWT
    SECRET_KEY = "workteam_secret_key_2026_machao"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天

    # 文件上传
    UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

settings = Settings()