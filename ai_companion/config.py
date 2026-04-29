# AI伴侣 - 配置文件

import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 加载 .env 文件
load_dotenv(BASE_DIR / ".env")

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"  # 或 deepseek-coder

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite://{BASE_DIR}/data/ai_companion.db")

# 向量数据库配置
VECTOR_DB_PATH = str(BASE_DIR / "data" / "chroma_db")

# 服务配置
API_HOST = "0.0.0.0"
API_PORT = 8001
DEBUG = True

# 安全配置
BLOCKED_WORDS = [
    "自杀", "自残", "杀人", "爆炸", "毒品",
    "我想死", "活着没意义", "结束自己"
]

CRISIS_RESPONSE = """
我非常关心你，你现在很不容易。如果你正在经历困难时刻，请立刻联系专业帮助：

心理援助热线：400-161-9995
北京心理危机研究与干预中心：010-82951332
生命热线：400-821-1215

你值得被帮助，请给自己一个机会。
"""