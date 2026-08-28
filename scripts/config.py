"""集中配置：路径、开关与网络参数。

保存目录优先级：环境变量 BBC6_SAVE_DIR > DEFAULT_SAVE_DIR（工作目录下的 downloads/）。
"""

import os
from pathlib import Path

# ---------- 路径 ----------
DEFAULT_SAVE_DIR = Path("downloads")            # 节目保存目录（相对当前工作目录）
SAVE_DIR_ENV = "BBC6_SAVE_DIR"                  # 覆盖保存目录的环境变量名
JSON_FILE = "6minute_english_episodes.json"     # 元数据 JSON（生成于工作目录）

# ---------- 下载行为 ----------
MAX_ITEMS = 20            # 每次最多处理条数（按日期升序取前 N 条；None = 不限）
EXTRACT_AUDIO_FROM_VIDEO = True   # 是否用 ffmpeg 从视频提取音频
KEEP_VIDEO_AFTER_EXTRACT = False  # 提取音频后是否保留原视频

# ---------- 网络参数 ----------
REQUEST_TIMEOUT = 20              # 请求超时（秒）
RETRIES = 3                       # 请求失败重试次数
RETRY_BACKOFF = 2                 # 重试基础间隔（秒），按重试次数线性递增
DOWNLOAD_CHUNK_SIZE = 8192        # 媒体下载分块大小（字节）
REQUEST_INTERVAL = 1.5            # 逐期处理之间的间隔（秒），避免请求过密

# ---------- 外部工具 ----------
FFMPEG_TIMEOUT = 600              # ffmpeg 单次转码超时（秒）
YTDLP_TIMEOUT = 600               # yt-dlp 单次下载超时（秒）

# ---------- 日志 ----------
JSON_GENERATOR_LOG = "json_generator.log"
DOWNLOADER_LOG = "downloader.log"

# ---------- 输出语言 ----------
OUTPUT_LANGUAGE = "zh"             # 终端输出语言："zh"（默认）或 "en"
LANGUAGE_ENV = "BBC6_LANG"         # 覆盖输出语言的环境变量名

# ---------- HTTP ----------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def get_save_dir() -> Path:
    """返回节目保存目录（Path）。优先读环境变量 BBC6_SAVE_DIR。"""
    return Path(os.environ.get(SAVE_DIR_ENV, str(DEFAULT_SAVE_DIR)))


def get_language() -> str:
    """返回输出语言（"zh" 或 "en"）。环境变量优先，非法值回退 "zh"。"""
    value = os.environ.get(LANGUAGE_ENV, OUTPUT_LANGUAGE).strip().lower()
    return value if value in ("zh", "en") else "zh"
