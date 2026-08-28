"""逐期下载文字稿与媒体文件，并把进度回写 JSON。

媒体获取策略（按顺序，命中即停）：
1. 页面下载区/媒体标签中的直链（按真实扩展名保存，支持 mp3/wav/m4a/mp4 等）；
2. 无直链时扫描页面中的 mpd 流媒体清单，交给 yt-dlp 下载，再用 ffmpeg 提取音频。

完成判定以 JSON 中 local_media_path 的真实存在性为准（utils.has_local_media），
配合每期处理后的即时 JSON 落盘，中断后重跑只会处理未完成的节目。
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import config
import utils
from utils import (
    clean_transcript,
    extract_text_content,
    is_transcript_cleaned,
    msg,
    parse_date,
    sanitize_filename,
)


def get_media_url(soup, page_url=None):
    """从节目页查找媒体直链，返回 (url, kind)；找不到返回 (None, None)。

    查找顺序：下载区直链 → audio/video source 标签 → data-media 属性 →
    页面任意已知扩展名链接。音频优先于视频。
    （page_url 参数保留以兼容旧签名；原先基于它的 mediaselector API
    兜底已移除——该接口不可用，mpd 页面改由 utils.find_mpd_url 处理。）
    """
    candidates = []

    download_area = soup.select_one('div.widget-pagelink-download')
    if download_area:
        for a in download_area.find_all("a", href=True):
            kind, _ = utils.infer_media_kind_and_ext(a["href"])
            if kind:
                candidates.append((a["href"], kind))
        result = _pick_preferred(candidates)
        if result[0]:
            return result

    for source in soup.select("audio source[src], video source[src]"):
        kind, _ = utils.infer_media_kind_and_ext(source["src"])
        if kind:
            return source["src"], kind
    # source 存在但扩展名无法识别：按标签类型兜底
    audio_source = soup.select_one("audio source[src]")
    if audio_source:
        return audio_source["src"], "audio"
    video_source = soup.select_one("video source[src]")
    if video_source:
        return video_source["src"], "video"

    media_tag = soup.select_one("[data-media]")
    if media_tag and media_tag.get("data-media"):
        url = media_tag["data-media"]
        kind, _ = utils.infer_media_kind_and_ext(url)
        if kind:
            return url, kind
        return url, "video" if ".mp4" in url.lower() else "audio"

    for a in soup.select("a[href]"):
        kind, _ = utils.infer_media_kind_and_ext(a["href"])
        if kind:
            candidates.append((a["href"], kind))
    return _pick_preferred(candidates)


def _pick_preferred(candidates):
    """从 (href, kind) 列表中选音频优先的第一条。"""
    for href, kind in candidates:
        if kind == "audio":
            return href, kind
    for href, kind in candidates:
        if kind == "video":
            return href, kind
    return None, None


def fetch_episode_page(link):
    """拉取节目页并返回 BeautifulSoup；失败返回 None。"""
    try:
        resp = utils.fetch_with_retry(link)
        if resp.status_code == 200:
            resp.encoding = "utf-8"
            return BeautifulSoup(resp.text, "html.parser")
        print(msg("http_status_fallback", code=resp.status_code))
    except (requests.RequestException, ConnectionError, TimeoutError) as error:
        print(msg("request_error_fallback", error=error))
    return None


def download_file(url, dest_path):
    """流式下载文件；失败时清理残留文件并返回 False。"""
    try:
        url = utils.normalize_url(url)
        with requests.get(url, headers=config.HEADERS, stream=True,
                          timeout=config.REQUEST_TIMEOUT) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=config.DOWNLOAD_CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print("\r      " + msg("download_progress", percent=percent),
                                  end="")
            if total_size > 0:
                print()
            return True
    except Exception as error:
        print("\n      " + msg("download_failed", error=error))
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False


def extract_audio_from_video(video_path, audio_path):
    """用 ffmpeg 从视频提取 128k mp3 音频。"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print(msg("ffmpeg_missing"))
        return False
    print(msg("ffmpeg_extracting"))
    cmd = ["ffmpeg", "-i", str(video_path), "-vn", "-ab", "128k", "-y", str(audio_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=config.FFMPEG_TIMEOUT)
        if result.returncode == 0 and os.path.exists(audio_path):
            print(msg("ffmpeg_success", path=audio_path))
            return True
        print(msg("ffmpeg_failed", error=result.stderr[:200]))
        return False
    except subprocess.TimeoutExpired:
        print(msg("ffmpeg_timeout"))
        return False


def download_via_yt_dlp(mpd_url, save_folder):
    """用 yt-dlp 下载 mpd 清单媒体，统一命名为 media.<ext>。

    返回 (是否成功, 最终媒体文件路径)。
    """
    if shutil.which("yt-dlp") is None:
        print(msg("ytdlp_missing"))
        return False, None
    print(msg("ytdlp_downloading"))
    output_template = str(Path(save_folder) / "source.%(ext)s")
    cmd = ["yt-dlp", "-o", output_template, "--no-playlist", mpd_url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=config.YTDLP_TIMEOUT)
    except subprocess.TimeoutExpired:
        print(msg("ytdlp_timeout"))
        return False, None
    if result.returncode != 0:
        print(msg("ytdlp_failed", error=(result.stderr or "")[:200]))
        return False, None

    candidates = sorted(Path(save_folder).glob("source.*"))
    if not candidates:
        print(msg("ytdlp_no_output"))
        return False, None
    source = candidates[0]
    _, ext = utils.infer_media_kind_and_ext(source.name)
    if ext is None:
        ext = ".mp4"  # 兜底：yt-dlp 常见产出为 mp4/webm
    final_path = Path(save_folder) / f"media{ext}"
    if final_path.exists():
        final_path.unlink()
    source.replace(final_path)
    print(msg("ytdlp_success", name=final_path.name))
    return True, final_path


def _find_existing_media(save_folder):
    """在节目文件夹中查找已存在的媒体文件（media.* > downloaded.* > source.*）。"""
    folder = Path(save_folder)
    if not folder.is_dir():
        return None
    for pattern in ("media.*", "downloaded.*", "source.*"):
        for candidate in sorted(folder.glob(pattern)):
            if candidate.is_file():
                return candidate
    return None


def _handle_transcript(soup, save_folder, logger):
    """保存/清理文字稿：新文本优先，失败时回退旧文本。"""
    text_path = Path(save_folder) / "transcript.txt"
    if soup is not None:
        content = extract_text_content(soup)
        if content:
            text_path.write_text(content, encoding="utf-8")
            logger.info(msg("transcript_saved", n=len(content)))
            return
        logger.warning(msg("transcript_not_extracted"))
    if text_path.exists():
        old = text_path.read_text(encoding="utf-8")
        text_path.write_text(clean_transcript(old), encoding="utf-8")
        logger.info(msg("transcript_cleaned_old"))
    else:
        text_path.write_text(msg("transcript_placeholder"), encoding="utf-8")
        logger.warning(msg("transcript_missing"))


def _download_direct(media_url, kind, save_folder, logger):
    """下载直链媒体并统一命名为 media.<真实扩展名>；返回最终路径或 None。"""
    inferred_kind, ext = utils.infer_media_kind_and_ext(media_url)
    if ext is None:
        ext = ".mp3" if kind == "audio" else ".mp4"
    kind = inferred_kind or kind

    temp_path = Path(save_folder) / f"downloaded{ext}"
    final_path = Path(save_folder) / f"media{ext}"
    print(msg("media_downloading", url=media_url))
    if not download_file(media_url, temp_path):
        logger.warning(msg("media_download_failed", url=media_url))
        return None

    # 立即定名为 media.<ext>：即使后续转码失败，下次运行也能识别为已完成
    if final_path.exists():
        final_path.unlink()
    temp_path.replace(final_path)

    if kind == "video" and config.EXTRACT_AUDIO_FROM_VIDEO:
        audio_path = final_path.with_suffix(".mp3")
        if extract_audio_from_video(final_path, audio_path):
            if not config.KEEP_VIDEO_AFTER_EXTRACT:
                final_path.unlink()
                print(msg("video_deleted"))
            return audio_path
    return final_path


def _finalize_video(path, logger):
    """若文件是视频且开启提取，转出 mp3 并按配置清理原视频；返回最终路径。"""
    final_path = Path(path)
    kind, _ = utils.infer_media_kind_and_ext(final_path.name)
    if kind == "video" and config.EXTRACT_AUDIO_FROM_VIDEO:
        audio_path = final_path.with_suffix(".mp3")
        if extract_audio_from_video(final_path, audio_path):
            if not config.KEEP_VIDEO_AFTER_EXTRACT:
                final_path.unlink()
                print(msg("video_deleted"))
            return audio_path
    return final_path


def process_episode(ep, idx, total, logger):
    """处理单期节目：文字稿 + 媒体，并把进度写回 ep（就地修改）。"""
    title = ep.get("title", "")
    ep_num = ep.get("episode_number") or f"EP_{idx + 1:06d}"
    link = ep.get("link")
    if not link:
        logger.info(msg("skip_no_link", i=idx + 1, n=total, title=title))
        return False

    safe_title = sanitize_filename(title)
    save_folder = config.get_save_dir() / f"{ep_num}_{safe_title}"
    try:
        save_folder.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        logger.error(msg("mkdir_failed", path=save_folder, error=error))
        return False

    logger.info(msg("processing", i=idx + 1, n=total, title=title))

    # ---- 0. 恢复：JSON 缺路径但文件夹里已有媒体 ----
    if not utils.has_local_media(ep):
        existing = _find_existing_media(save_folder)
        if existing is not None:
            ep["local_media_path"] = str(existing)
            logger.info(msg("media_restored", name=existing.name))

    media_done = utils.has_local_media(ep)

    # ---- 1. 拉取页面 ----
    soup = fetch_episode_page(link)

    # ---- 2. 文字稿 ----
    _handle_transcript(soup, save_folder, logger)

    # ---- 3. 媒体 ----
    if media_done:
        logger.info(msg("media_exists", path=ep.get("local_media_path")))
        if not ep.get("media_download_url") and soup is not None:
            media_url, _ = get_media_url(soup, link)
            if not media_url:
                media_url = utils.find_mpd_url(soup)
            if media_url:
                ep["media_download_url"] = utils.normalize_url(media_url)
        return True

    media_url, kind = (None, None)
    if soup is not None:
        media_url, kind = get_media_url(soup, link)
        if media_url:
            media_url = utils.normalize_url(media_url)

    if media_url:
        final_path = _download_direct(media_url, kind, save_folder, logger)
        ep["media_download_url"] = media_url
        ep["local_media_path"] = str(final_path) if final_path else None
        return True

    # 直链未命中 → 尝试 mpd 清单 + yt-dlp
    if soup is not None:
        mpd_url = utils.find_mpd_url(soup)
        if mpd_url:
            mpd_url = utils.normalize_url(mpd_url)
            ok, path = download_via_yt_dlp(mpd_url, save_folder)
            ep["media_download_url"] = mpd_url
            ep["local_media_path"] = str(_finalize_video(path, logger)) if ok else None
            return True

    logger.warning(msg("media_not_found"))
    ep.setdefault("media_download_url", None)
    return True


def _save_json(episodes):
    with open(config.JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)


def _needs_processing(ep):
    """待处理判定：媒体缺失，或文字稿尚未清理。"""
    if not utils.has_local_media(ep):
        return True
    folder = Path(ep["local_media_path"]).parent
    return not is_transcript_cleaned(folder)


def main():
    logger = utils.setup_logging(config.DOWNLOADER_LOG)
    config.get_save_dir().mkdir(parents=True, exist_ok=True)

    if not os.path.exists(config.JSON_FILE):
        logger.error(msg("json_missing", file=config.JSON_FILE))
        return 1

    with open(config.JSON_FILE, "r", encoding="utf-8") as f:
        all_episodes = json.load(f)
    logger.info(msg("json_loaded", n=len(all_episodes)))

    dated = []
    for ep in all_episodes:
        dt = parse_date(ep.get("date", ""))
        if dt is not None:
            dated.append((dt, ep))
    if not dated:
        logger.error(msg("no_dated_records"))
        return 1
    dated.sort(key=lambda pair: pair[0])
    episodes = [ep for _, ep in dated]

    pending = [ep for ep in episodes if _needs_processing(ep)]
    logger.info(msg("pending_summary", total=len(episodes), pending=len(pending)))

    if config.MAX_ITEMS is not None:
        pending = pending[:config.MAX_ITEMS]
    if not pending:
        logger.info(msg("nothing_pending"))
        return 0

    logger.info(msg("batch_size", n=len(pending)))

    updated = 0
    for idx, ep in enumerate(pending):
        if process_episode(ep, idx, len(pending), logger):
            updated += 1
            _save_json(all_episodes)  # 每期即时落盘，断点可续
            logger.info(msg("json_saved", i=idx + 1, n=len(pending)))
        else:
            logger.warning(msg("episode_failed", i=idx + 1))
        time.sleep(config.REQUEST_INTERVAL)

    _save_json(all_episodes)
    logger.info(msg("done_summary", total=len(pending), updated=updated))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
