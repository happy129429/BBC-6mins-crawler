"""公共工具：文件名清洗、文字稿清理、媒体链接识别、请求重试、日志。"""

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import config

# ---------- 文字稿截断标记 ----------
MARKER1 = "Latest 6 Minute English"
MARKER2 = """Next
Find an
A-Z list of our programmes"""

# ---------- 媒体扩展名 ----------
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
VIDEO_EXTENSIONS = {".mp4", ".m4v", ".mov", ".webm", ".mkv"}

_MPD_URL_RE = re.compile(r"""https?://[^\s"'<>\\]+\.mpd[^\s"'<>\\]*""")


def sanitize_filename(name):
    """清洗为安全文件名：去空白、替换非法字符、限长 40。"""
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    if len(name) > 40:
        name = name[:40]
    return name.strip()


def parse_date(date_str):
    """解析 "23 Jul 2026" 风格日期；失败返回 None。"""
    try:
        return datetime.strptime(date_str, "%d %b %Y")
    except (ValueError, TypeError):
        return None


def clean_transcript(text):
    """截掉页面杂质（两个标记之后的内容）并压平多余空行。"""
    if not text:
        return ""
    if MARKER1 in text:
        text = text.split(MARKER1, 1)[0].strip()
    if MARKER2 in text:
        text = text.split(MARKER2, 1)[0].strip()
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\n\s*$', '', text)
    return text


def extract_text_content(soup):
    """从节目页提取文字稿正文并清理。"""
    content_div = soup.select_one('div[role="article"]')
    if not content_div:
        content_div = soup.select_one('div.text')
    if not content_div:
        content_div = soup.select_one('#bbcle-content')
    if not content_div:
        return ""
    for tag in content_div(["script", "style", "noscript"]):
        tag.decompose()
    raw_text = content_div.get_text(separator="\n", strip=True)
    return clean_transcript(raw_text)


def is_transcript_cleaned(folder_path):
    """检查 transcript.txt 是否已清理（不含截断标记）。"""
    text_path = Path(folder_path) / "transcript.txt"
    if not text_path.exists():
        return False
    try:
        content = text_path.read_text(encoding='utf-8')
    except OSError:
        return False
    return MARKER1 not in content and MARKER2 not in content


def infer_media_kind_and_ext(url):
    """按 URL 真实扩展名推断媒体类型。

    返回 (kind, ext)，如 ("audio", ".mp3")；无法识别返回 (None, None)。
    忽略查询串与锚点，扩展名统一小写。
    """
    ext = Path(urlparse(str(url)).path).suffix.lower()
    if ext in AUDIO_EXTENSIONS:
        return "audio", ext
    if ext in VIDEO_EXTENSIONS:
        return "video", ext
    return None, None


def normalize_url(url, base="https://www.bbc.co.uk"):
    """补全协议相对（//开头）与站点相对（/开头）链接。"""
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return urljoin(base, url)
    return url


def find_mpd_url(soup):
    """在页面（含脚本文本与媒体标签属性）中查找 mpd 流媒体清单链接。"""
    for tag in soup.find_all(["source", "audio", "video", "a", "div"]):
        for attr in ("src", "href", "data-media", "data-src"):
            value = tag.get(attr)
            if value and ".mpd" in value.lower():
                return normalize_url(value)
    # 注：新版 bs4 的 get_text() 默认不含 script 内容，需单独扫描
    texts = [soup.get_text()]
    for tag in soup.find_all(["script", "noscript"]):
        if tag.string:
            texts.append(tag.string)
    for text in texts:
        match = _MPD_URL_RE.search(text)
        if match:
            return match.group(0)
    return None


def has_local_media(episode):
    """统一的完成判定：JSON 记录的 local_media_path 是否真实存在。"""
    path = episode.get("local_media_path")
    return bool(path) and Path(path).is_file()


def fetch_with_retry(url, headers=None, timeout=None, retries=None,
                     backoff=None, stream=False, session=None):
    """带重试的 GET 请求。网络层错误（连接/超时）重试，耗尽后抛出最后异常。"""
    headers = config.HEADERS if headers is None else headers
    timeout = config.REQUEST_TIMEOUT if timeout is None else timeout
    retries = config.RETRIES if retries is None else retries
    backoff = config.RETRY_BACKOFF if backoff is None else backoff
    getter = session.get if session is not None else requests.get

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return getter(url, headers=headers, timeout=timeout, stream=stream)
        except (requests.RequestException, ConnectionError, TimeoutError) as error:
            last_error = error
            if backoff and attempt < retries:
                time.sleep(backoff * attempt)
    raise last_error


def setup_logging(log_file, name="bbc6"):
    """双通道日志：终端 + 文件。返回配置好的 logger。"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


# ---------- 终端输出文案（中/英双语表） ----------
# 所有用户可见文案集中于此，经 msg() 按当前语言取值；
# 两个语言表的键集合必须一致（tests/test_i18n.py 校验）。

MESSAGES = {
    "zh": {
        # json_generator
        "fetching_index": "正在获取栏目主页：{url}",
        "fetch_failed": "获取主页失败：{error}",
        "scraped_count": "本次抓取到 {n} 期节目",
        "json_rebuild": "已有 JSON 读取失败或为空，本次将重建文件",
        "saved_records": "已保存 {n} 条记录到 {file}",
        "merge_summary": "增量合并完成：已有 {old} 条 + 新抓取 {scraped} 条 → 合并后 {merged} 条（下载进度字段已保留）",
        # downloader 总流程
        "json_missing": "找不到 {file}，请先运行 json_generator.py",
        "json_loaded": "JSON 中共 {n} 条记录",
        "no_dated_records": "没有可解析日期的记录",
        "pending_summary": "总可解析记录 {total} 条，待处理 {pending} 条",
        "nothing_pending": "没有待处理的记录",
        "batch_size": "本次处理 {n} 条（按日期升序）",
        "json_saved": "  💾 JSON 已更新（进度：{i}/{n}）",
        "episode_failed": "  第 {i} 条处理失败，未保存 JSON",
        "done_summary": "===== 处理完成：本次 {total} 条，成功更新 {updated} 条 =====",
        # 单期处理
        "skip_no_link": "[{i}/{n}] 跳过（无链接）：{title}",
        "mkdir_failed": "  无法创建文件夹 {path}：{error}",
        "processing": "[{i}/{n}] 处理：{title}",
        "media_restored": "  从现有文件恢复媒体记录：{name}",
        "media_exists": "  已有媒体：{path}",
        "media_not_found": "  未找到媒体链接（直链与 mpd 均无）",
        # 页面请求
        "http_status_fallback": "  请求返回状态码 {code}，将使用旧文本（如果存在）",
        "request_error_fallback": "  请求异常：{error}，将使用旧文本（如果存在）",
        # 文字稿
        "transcript_saved": "  文字稿已保存（{n} 字符）",
        "transcript_not_extracted": "  新页面未提取到文字稿",
        "transcript_cleaned_old": "  已对旧文字稿执行清理并保存",
        "transcript_missing": "  未提取到文字稿，且无旧文件可保留",
        "transcript_placeholder": "(内容提取失败)",
        # 媒体下载
        "media_downloading": "  ↓ 下载媒体：{url}",
        "media_download_failed": "  媒体下载失败：{url}",
        "download_progress": "下载进度: {percent:.1f}%",
        "download_failed": "下载失败: {error}",
        "video_deleted": "      🗑 已删除原视频文件",
        # ffmpeg
        "ffmpeg_missing": "      ⚠ 未找到 ffmpeg，请安装并添加到 PATH",
        "ffmpeg_extracting": "      🎵 正在用 ffmpeg 提取音频...",
        "ffmpeg_success": "      ✅ 音频提取成功：{path}",
        "ffmpeg_failed": "      ❌ ffmpeg 提取失败: {error}",
        "ffmpeg_timeout": "      ❌ ffmpeg 超时",
        # yt-dlp / mpd
        "ytdlp_missing": "      ⚠ 未找到 yt-dlp，无法处理 mpd 页面（请安装并加入 PATH）",
        "ytdlp_downloading": "      🎬 正在用 yt-dlp 下载 mpd 清单...",
        "ytdlp_timeout": "      ❌ yt-dlp 超时",
        "ytdlp_failed": "      ❌ yt-dlp 下载失败: {error}",
        "ytdlp_no_output": "      ❌ yt-dlp 未产出文件",
        "ytdlp_success": "      ✅ mpd 媒体下载完成：{name}",
    },
    "en": {
        # json_generator
        "fetching_index": "Fetching the programme index page: {url}",
        "fetch_failed": "Failed to fetch the index page: {error}",
        "scraped_count": "Scraped {n} episodes",
        "json_rebuild": "Existing JSON unreadable or empty; the file will be rebuilt",
        "saved_records": "Saved {n} records to {file}",
        "merge_summary": "Incremental merge done: {old} existing + {scraped} scraped → {merged} total (download-progress fields preserved)",
        # downloader 总流程
        "json_missing": "{file} not found; run json_generator.py first",
        "json_loaded": "{n} records in JSON",
        "no_dated_records": "No records with a parsable date",
        "pending_summary": "{total} dated records, {pending} pending",
        "nothing_pending": "No pending episodes",
        "batch_size": "Processing {n} episodes this run (oldest first)",
        "json_saved": "  💾 JSON updated (progress: {i}/{n})",
        "episode_failed": "  Episode {i} failed; JSON not saved",
        "done_summary": "===== Done: {total} processed, {updated} updated =====",
        # 单期处理
        "skip_no_link": "[{i}/{n}] Skipped (no link): {title}",
        "mkdir_failed": "  Cannot create folder {path}: {error}",
        "processing": "[{i}/{n}] Processing: {title}",
        "media_restored": "  Restored media record from existing file: {name}",
        "media_exists": "  Media already present: {path}",
        "media_not_found": "  No media link found (neither direct nor mpd)",
        # 页面请求
        "http_status_fallback": "  HTTP status {code}; will use the existing transcript (if any)",
        "request_error_fallback": "  Request error: {error}; will use the existing transcript (if any)",
        # 文字稿
        "transcript_saved": "  Transcript saved ({n} chars)",
        "transcript_not_extracted": "  No transcript extracted from the fresh page",
        "transcript_cleaned_old": "  Existing transcript cleaned and saved",
        "transcript_missing": "  No transcript extracted and no existing file to keep",
        "transcript_placeholder": "(transcript unavailable)",
        # 媒体下载
        "media_downloading": "  ↓ Downloading media: {url}",
        "media_download_failed": "  Media download failed: {url}",
        "download_progress": "Progress: {percent:.1f}%",
        "download_failed": "Download failed: {error}",
        "video_deleted": "      🗑 Original video deleted",
        # ffmpeg
        "ffmpeg_missing": "      ⚠ ffmpeg not found; install it and add it to PATH",
        "ffmpeg_extracting": "      🎵 Extracting audio with ffmpeg...",
        "ffmpeg_success": "      ✅ Audio extracted: {path}",
        "ffmpeg_failed": "      ❌ ffmpeg failed: {error}",
        "ffmpeg_timeout": "      ❌ ffmpeg timed out",
        # yt-dlp / mpd
        "ytdlp_missing": "      ⚠ yt-dlp not found; cannot handle mpd pages (install it and add it to PATH)",
        "ytdlp_downloading": "      🎬 Downloading mpd manifest with yt-dlp...",
        "ytdlp_timeout": "      ❌ yt-dlp timed out",
        "ytdlp_failed": "      ❌ yt-dlp failed: {error}",
        "ytdlp_no_output": "      ❌ yt-dlp produced no file",
        "ytdlp_success": "      ✅ mpd media downloaded: {name}",
    },
}


def msg(key, **kwargs):
    """按当前输出语言（config.get_language()）取文案并用 kwargs 填充。"""
    table = MESSAGES.get(config.get_language(), MESSAGES["zh"])
    text = table.get(key) or MESSAGES["zh"][key]
    return text.format(**kwargs) if kwargs else text
