"""抓取 6 Minute English 栏目主页元数据，增量合并写入 JSON。

增量合并规则：以 episode_number（缺失时回退 link）为键。新抓取的元数据
（标题/链接/日期/简介）覆盖旧值；旧记录中的下载进度字段
（media_download_url、local_media_path 等）全部保留，绝不丢失，
因此反复运行本脚本是安全的。
"""

import json
import os
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
import utils

BASE_URL = "https://www.bbc.co.uk"
MAIN_URL = urljoin(BASE_URL, "/learningenglish/english/features/6-minute-english")

# 下载进度字段：合并时一律保留旧值
_PROGRESS_FIELDS = ("media_download_url", "local_media_path")


def fetch_page(url):
    """获取页面 HTML。网络异常自动重试；HTTP 4xx/5xx 立即抛出。"""
    last_error = None
    for attempt in range(1, config.RETRIES + 1):
        try:
            resp = requests.get(url, headers=config.HEADERS)
            resp.raise_for_status()
            # BBC 页面通常使用 UTF-8 编码
            resp.encoding = "utf-8"
            return resp.text
        except requests.HTTPError:
            raise
        except requests.RequestException as error:
            last_error = error
            if config.RETRY_BACKOFF and attempt < config.RETRIES:
                time.sleep(config.RETRY_BACKOFF * attempt)
    raise last_error


def parse_main_page(html):
    """解析主页，提取所有节目条目。"""
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("li.course-content-item")
    results = []

    for li in items:
        link_tag = li.select_one("div.text h2 a")
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        href = link_tag.get("href")
        full_url = urljoin(BASE_URL, href) if href else None

        desc_tag = li.select_one("div.text div.details p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        episode_part = ""
        date_part = ""
        details_div = li.select_one("div.text div.details")
        if details_div:
            h3 = details_div.select_one("h3")
            if h3:
                # h3 内容如: "Episode 260723 / 23 Jul 2026"
                parts = h3.get_text(separator=" ", strip=True).split("/")
                if len(parts) >= 2:
                    episode_part = parts[0].strip()
                    date_part = parts[1].strip()

        ep_match = re.search(r"Episode\s*(\d+)", episode_part)
        episode_number = ep_match.group(1) if ep_match else ""

        results.append({
            "episode_number": episode_number,
            "title": title,
            "link": full_url,
            "description": description,
            "date": date_part,
        })
    return results


def episode_key(record):
    """记录的唯一键：episode_number 优先，回退 link，再回退 title。"""
    return record.get("episode_number") or record.get("link") or record.get("title") or ""


def merge_episodes(existing, scraped):
    """增量合并两组记录。

    - 键相同的记录：新元数据覆盖旧元数据，旧进度字段全部保留；
    - 仅在新列表中的记录：追加；
    - 仅在旧列表中的记录（如主页已下架的节目）：原样保留。
    """
    old_by_key = {episode_key(rec): rec for rec in existing}
    merged = []
    seen = set()

    for rec in scraped:
        key = episode_key(rec)
        old = old_by_key.get(key)
        if old is not None:
            combined = dict(old)
            combined.update(rec)
            for field in _PROGRESS_FIELDS:
                if field in old:
                    combined[field] = old[field]
            merged.append(combined)
        else:
            merged.append(dict(rec))
        seen.add(key)

    for rec in existing:
        if episode_key(rec) not in seen:
            merged.append(dict(rec))
    return merged


def save_to_json(data, filename=config.JSON_FILE):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(utils.msg("saved_records", n=len(data), file=filename))


def load_existing(filename=config.JSON_FILE):
    """读取已有 JSON；不存在或损坏时返回空列表。"""
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def main():
    logger = utils.setup_logging(config.JSON_GENERATOR_LOG)
    logger.info(utils.msg("fetching_index", url=MAIN_URL))
    try:
        html = fetch_page(MAIN_URL)
    except requests.RequestException as error:
        logger.error(utils.msg("fetch_failed", error=error))
        return 1

    episodes = parse_main_page(html)
    logger.info(utils.msg("scraped_count", n=len(episodes)))

    existing = load_existing(config.JSON_FILE)
    if os.path.exists(config.JSON_FILE) and not existing:
        logger.warning(utils.msg("json_rebuild"))

    merged = merge_episodes(existing, episodes)
    save_to_json(merged, config.JSON_FILE)
    logger.info(utils.msg(
        "merge_summary",
        old=len(existing), scraped=len(episodes), merged=len(merged),
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
