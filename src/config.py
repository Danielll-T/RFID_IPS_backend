import os

# 项目根目录（上两级目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SQLite 数据库路径，可通过环境变量覆盖
DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(BASE_DIR, "data", "positioning.db")
)

# 日志级别，可选 DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Web API 配置
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# 调试模式开关
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# 其他全局常量，可以在这里继续添加
# 例如：
# MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
# RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))