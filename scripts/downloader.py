import os
import json
import re
import time
import subprocess
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path

# ==================== 配置区 ====================
BASE_SAVE_DIR = r"D:\BBC6minute" # 请根据实际需要修改下载目录
JSON_INPUT = "6minute_english_episodes.json"

MAX_ITEMS = None              # 处理前 N 条（按日期升序，即最早的 N 条），None代表无限制
EXTRACT_AUDIO_FROM_VIDEO = True
KEEP_VIDEO_AFTER_EXTRACT = False

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
REQUEST_TIMEOUT = 20
DOWNLOAD_CHUNK_SIZE = 8192
MARKER1 = "Latest 6 Minute English"
MARKER2 = """Next
Find an
A-Z list of our programmes"""
# ================================================

def sanitize_filename(name):
    # 移除开头和结尾的空白字符
    name = name.strip()
    # 替换非法字符
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    # 限制长度
    if len(name) > 40:
        name = name[:40]
    # 再次去除首尾空格
    return name.strip()

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%d %b %Y")
    except (ValueError, TypeError):
        return None

def clean_transcript(text):
    if not text:
        return ""
    if MARKER1 in text:
        text = text.split(MARKER1, 1)[0].strip()
    if MARKER2 in text:
        text = text.split(MARKER2, 1)[0].strip()
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'\n\s*$', '', text)
    return text

import requests
import json
from urllib.parse import urljoin

def get_media_url(soup, page_url):
    # 1. 优先从下载区域（widget-pagelink-download）查找音频/视频链接
    download_area = soup.select_one('div.widget-pagelink-download')
    if download_area:
        mp3_link = download_area.select_one('a.bbcle-download-extension-mp3, a[href*=".mp3"]')
        if mp3_link:
            return mp3_link['href'], 'audio'
        mp4_link = download_area.select_one('a.bbcle-download-extension-mp4, a[href*=".mp4"]')
        if mp4_link:
            return mp4_link['href'], 'video'

    # 2. 原有用标签查找
    audio_source = soup.select_one('audio source[src]')
    if audio_source:
        return audio_source['src'], 'audio'
    video_source = soup.select_one('video source[src]')
    if video_source:
        return video_source['src'], 'video'

    # 3. 查找 data-media 属性
    media_tag = soup.select_one('[data-media]')
    if media_tag and media_tag.get('data-media'):
        url = media_tag['data-media']
        return url, 'video' if '.mp4' in url.lower() else 'audio'

    # 4. 直接找 .mp3/.mp4 链接
    mp3_link = soup.select_one('a[href*=".mp3"]')
    if mp3_link:
        return mp3_link['href'], 'audio'
    mp4_link = soup.select_one('a[href*=".mp4"]')
    if mp4_link:
        return mp4_link['href'], 'video'

    # 5. 通过 BBC 媒体 API 获取（尝试多个 mediaset）
    video_div = soup.select_one('div.video[data-pid]')
    if video_div:
        pid = video_div['data-pid']
        # 尝试不同的 mediaset 值
        mediasets = ['pc', 'mobile', 'tablet', 'iptv']
        api_urls = [
            f"https://open.live.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/{ms}/vpid/{pid}/format/json"
            for ms in mediasets
        ] + [
            f"https://www.bbc.co.uk/mediaselector/5/select/version/2.0/mediaset/{ms}/vpid/{pid}/format/json"
            for ms in mediasets
        ]
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': page_url,
            'Accept': 'application/json'
        }
        for url in api_urls:
            try:
                resp = requests.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    # 遍历 media 数组
                    for media_item in data.get('media', []):
                        for connection in media_item.get('connection', []):
                            href = connection.get('href')
                            if href:
                                # 优先返回 MP3，否则 MP4
                                if '.mp3' in href.lower():
                                    return href, 'audio'
                                elif '.mp4' in href.lower():
                                    return href, 'video'
                    # 如果没有明确的 MP3/MP4，尝试返回第一个 https 链接（可能是音频）
                    for media_item in data.get('media', []):
                        for connection in media_item.get('connection', []):
                            href = connection.get('href')
                            if href and href.startswith('http'):
                                return href, 'audio'
                else:
                    # 非200状态码继续尝试下一个
                    continue
            except Exception as e:
                continue  # 忽略单个端点的错误，继续尝试下一个
        # 所有端点都失败
        print(f"  ⚠️ 所有媒体 API 端点均无法获取媒体链接 (PID: {pid})")

    return None, None

def extract_text_content(soup):
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

def download_file(url, dest_path):
    try:
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            url = urljoin('https://www.bbc.co.uk', url)
        with requests.get(url, headers=HEADERS, stream=True, timeout=REQUEST_TIMEOUT) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            downloaded = 0
            with open(dest_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\r      下载进度: {percent:.1f}%", end="")
            if total_size > 0:
                print()
            return True
    except Exception as e:
        print(f"\n      下载失败: {e}")
        if os.path.exists(dest_path):
            os.remove(dest_path)
        return False

def extract_audio_from_video(video_path, audio_path):
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("      ⚠ 未找到 ffmpeg，请安装并添加到 PATH")
        return False
    print(f"\n      🎵 正在用 ffmpeg 提取音频...")
    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-vn', '-ab', '128k', '-y', str(audio_path)
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0 and os.path.exists(audio_path):
            print(f"      ✅ 音频提取成功：{audio_path}")
            return True
        else:
            print(f"      ❌ ffmpeg 提取失败: {result.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print("      ❌ ffmpeg 超时")
        return False

def process_episode(ep, idx, total):
    title = ep.get('title', '未知标题')
    ep_num = ep.get('episode_number', f'EP_{idx+1:06d}')
    link = ep.get('link')
    if not link:
        print(f"[{idx+1}/{total}] 跳过：{title} (无链接)")
        return False

    safe_title = sanitize_filename(title)
    folder_name = f"{ep_num}_{safe_title}"
    save_folder = Path(BASE_SAVE_DIR) / folder_name

    folder_exists = save_folder.exists()
    media_files = list(save_folder.glob("media.*")) if folder_exists else []
    has_media = len(media_files) > 0

    if has_media:
        print(f"[{idx+1}/{total}] 📁 文件夹已存在，发现媒体文件：{media_files[0].name}")
        if not ep.get('local_media_path'):
            ep['local_media_path'] = str(media_files[0])
    else:
        print(f"[{idx+1}/{total}] 📄 处理：{title}")

    # ---- 1. 尝试获取页面内容 ----
    soup = None
    try:
        resp = requests.get(link, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.encoding = 'utf-8'
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
        else:
            print(f"  请求返回状态码 {resp.status_code}，将使用旧文本（如果存在）")
    except Exception as e:
        print(f"  请求异常：{e}，将使用旧文本（如果存在）")

    # ---- 2. 处理文本（无论请求是否成功） ----
    save_folder.mkdir(parents=True, exist_ok=True)
    if not save_folder.exists():
        print(f"  ❌ 无法创建文件夹：{save_folder}")
        return False
    text_path = save_folder / "transcript.txt"

    if soup is not None:
        # 请求成功：提取新文本并清理
        text_content = extract_text_content(soup)
        if text_content:
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            print(f"  ✅ 文本已保存 ({len(text_content)} 字符)")
        else:
            # 新页面没有提取到文本，尝试保留旧文本并清理
            if text_path.exists():
                old_text = text_path.read_text(encoding='utf-8')
                cleaned = clean_transcript(old_text)
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned)
                print(f"  ⚠️ 新页面未提取到文本，已对旧文本执行清理")
            else:
                text_path.write_text("(内容提取失败)", encoding='utf-8')
                print("  ⚠️ 未提取到文本，且无旧文本可保留")
    else:
        # 请求失败：尝试使用旧文本并清理
        if text_path.exists():
            old_text = text_path.read_text(encoding='utf-8')
            cleaned = clean_transcript(old_text)
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(cleaned)
            print(f"  ✅ 已对旧文本执行清理并保存")
        else:
            text_path.write_text("(页面请求失败，且无旧文本)", encoding='utf-8')
            print("  ⚠️ 页面请求失败，且无旧文本可保留")

    # ---- 3. 处理媒体（仅当请求成功且没有媒体文件时） ----
    if soup is not None:
        media_url, media_type = get_media_url(soup, link)
    else:
        media_url = None

    if not media_url:
        # 如果没有找到链接，记录 None，但如果有旧链接且已有媒体，可能保留旧链接
        print("  ⚠️ 未找到媒体链接（或请求失败）")
        if not ep.get('media_download_url'):
            ep['media_download_url'] = None
        if not ep.get('local_media_path') and has_media:
            ep['local_media_path'] = str(media_files[0])
        # 如果请求失败但已有媒体，我们仍然可以返回 True
        return True

    # 补全 URL
    if media_url.startswith('//'):
        media_url = 'https:' + media_url
    elif media_url.startswith('/'):
        media_url = urljoin('https://www.bbc.co.uk', media_url)

    # 只有没有媒体文件时才下载
    if not has_media:
        is_video = '.mp4' in media_url.lower()
        ext = '.mp4' if is_video else '.mp3'
        media_path = save_folder / f"downloaded{ext}"
        print(f"  ↓ 下载媒体：{media_url}")
        success = download_file(media_url, media_path)

        if not success:
            print("  ❌ 下载失败")
            ep['media_download_url'] = media_url
            ep['local_media_path'] = None
            return True

        # 处理视频转音频
        final_media_path = media_path
        if is_video and EXTRACT_AUDIO_FROM_VIDEO:
            audio_path = save_folder / "media.mp3"
            if extract_audio_from_video(media_path, audio_path):
                final_media_path = audio_path
                if not KEEP_VIDEO_AFTER_EXTRACT:
                    os.remove(media_path)
                    print(f"      🗑 已删除原视频文件")
            else:
                final_media_path = media_path
        else:
            if not is_video:
                audio_path = save_folder / "media.mp3"
                os.rename(media_path, audio_path)
                final_media_path = audio_path
            else:
                video_path = save_folder / "media.mp4"
                os.rename(media_path, video_path)
                final_media_path = video_path

        print(f"  ✅ 媒体最终保存为：{final_media_path}")
        ep['media_download_url'] = media_url
        ep['local_media_path'] = str(final_media_path)
    else:
        # 已有媒体，确保 JSON 中有路径
        if not ep.get('local_media_path'):
            ep['local_media_path'] = str(media_files[0])
        if not ep.get('media_download_url'):
            ep['media_download_url'] = media_url

    return True

def is_transcript_cleaned(folder_path):
    """检查 transcript.txt 是否已经清理完毕（不包含需要截断的标记）"""
    text_path = Path(folder_path) / "transcript.txt"
    if not text_path.exists():
        return False
    try:
        content = text_path.read_text(encoding='utf-8')
        # 如果包含任一标记，说明未清理
        if MARKER1 in content or MARKER2 in content:
            return False
        return True
    except:
        return False

def main():
    Path(BASE_SAVE_DIR).mkdir(parents=True, exist_ok=True)

    if not os.path.exists(JSON_INPUT):
        print(f"错误：找不到 {JSON_INPUT}")
        return

    with open(JSON_INPUT, 'r', encoding='utf-8') as f:
        all_episodes = json.load(f)

    print(f"JSON 中共有 {len(all_episodes)} 条记录")

    # ---- 解析日期，排序 ----
    episodes_with_date = []
    for ep in all_episodes:
        dt = parse_date(ep.get('date', ''))
        if dt is None:
            continue
        ep['_datetime'] = dt
        episodes_with_date.append(ep)

    if not episodes_with_date:
        print("没有可解析日期的记录")
        return

    episodes_with_date.sort(key=lambda x: x['_datetime'])

    # ---- 清除临时 _datetime 字段，避免 JSON 序列化错误 ----
    for ep in episodes_with_date:
        ep.pop('_datetime', None)

    # ---- 过滤出需要处理的记录：媒体缺失 或 文本未清理 ----
    pending_episodes = []
    for ep in episodes_with_date:
        local_path = ep.get('local_media_path')
        # 判断媒体是否存在
        media_exists = local_path and os.path.exists(local_path)
        if media_exists:
            folder = Path(local_path).parent
            # 如果媒体存在但文本未清理，仍然需要处理
            if not is_transcript_cleaned(folder):
                pending_episodes.append(ep)
                continue
            # 否则（媒体存在且文本已清理）跳过
        else:
            # 媒体缺失，需要处理
            pending_episodes.append(ep)

    total_pending = len(pending_episodes)
    print(f"总可解析记录 {len(episodes_with_date)} 条，待处理 {total_pending} 条")

    # ---- 取前 N 条待处理记录 ----
    if MAX_ITEMS is not None:
        episodes = pending_episodes[:MAX_ITEMS]
    else:
        episodes = pending_episodes

    if not episodes:
        print("没有待处理的记录")
        return

    print(f"本次处理前 {len(episodes)} 条（按日期升序）\n")

    updated_count = 0
    for idx, ep in enumerate(episodes):
        ep.pop('_datetime', None)
        success = process_episode(ep, idx, len(episodes))
        if success:
            updated_count += 1
            # 立即保存 JSON
            with open(JSON_INPUT, 'w', encoding='utf-8') as f:
                json.dump(all_episodes, f, ensure_ascii=False, indent=2)
            print(f"  💾 JSON 已更新（进度：{idx+1}/{len(episodes)}）")
        else:
            print(f"  ⚠️ 第 {idx+1} 条处理失败，未保存 JSON")

        time.sleep(1.5)

    # 最终保存
    with open(JSON_INPUT, 'w', encoding='utf-8') as f:
        json.dump(all_episodes, f, ensure_ascii=False, indent=2)

    print(f"\n===== 处理完成 =====")
    print(f"本次处理：{len(episodes)} 条")
    print(f"成功更新：{updated_count} 条")
    print(f"JSON 已更新：{JSON_INPUT}")

if __name__ == "__main__":
    main()
