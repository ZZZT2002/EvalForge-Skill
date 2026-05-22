"""全局配置：模式开关、阈值、评分权重、模型名"""
import os

# ---------- 1. 评测模式与目标 Agent ----------
EVAL_MODE = os.getenv("EVAL_MODE", "MOCK")          # "MOCK" / "REAL"
TARGET_AGENT = os.getenv("TARGET_AGENT", "deepseek")  # "deepseek" / "openai" / "both"

# ---------- 2. API 容错 ----------
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # 秒

# ---------- 3. 质量控制阈值 ----------
HUMAN_CHECK_RATE = 0.20      # 自动质检通过后再抽 20% 人工
BADCASE_THRESHOLD = 70.0     # Agent 得分 < 此值进 badcase 池
DECAY_THRESHOLD = 92.0       # Agent 在某 task 上 ≥ 此值视为过拟合

# ---------- 4. 判分权重（PROJECT.md §2.2） ----------
SCORE_WEIGHTS = {
    "tool_recall": 0.30,
    "tool_order": 0.30,
    "argument_accuracy": 0.40,
}

# ---------- 5. 难度分布（PROJECT.md §3.4） ----------
DIFFICULTY_DISTRIBUTION = {
    "normal": 0.60,
    "boundary": 0.25,
    "adversarial": 0.15,
}

# ---------- 6. Embedding 去重 ----------
EMBEDDING_MODEL = "paraphrase-MiniLM-L3-v2"
DEDUP_THRESHOLD = 0.85

# ---------- 7. API Key（从环境变量读取） ----------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# ---------- 8. 路径常量 ----------
DATA_DIR = "data"
SEEDS_PATH = f"{DATA_DIR}/seeds.json"
BADCASES_PATH = f"{DATA_DIR}/badcases.json"
HUMAN_REVIEW_LOG_PATH = f"{DATA_DIR}/human_review_log.json"
MOCK_RESPONSES_PATH = f"{DATA_DIR}/mock_responses.json"
VERSION_HISTORY_DIR = f"{DATA_DIR}/version_history"
REPORTS_DIR = f"{DATA_DIR}/reports"
