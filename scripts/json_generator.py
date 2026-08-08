import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin
import re

BASE_URL = "https://www.bbc.co.uk"
MAIN_URL = urljoin(BASE_URL, "/learningenglish/english/features/6-minute-english")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

def fetch_page(url):
    """获取页面 HTML"""
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()
    # BBC 页面通常使用 UTF-8 编码
    resp.encoding = "utf-8"
    return resp.text

def parse_main_page(html):
    """解析主页，提取所有节目条目"""
    soup = BeautifulSoup(html, "html.parser")
    # 所有条目位于 li.course-content-item 中
    items = soup.select("li.course-content-item")
    results = []

    for li in items:

        # 提取标题和链接
        link_tag = li.select_one("div.text h2 a")
        if not link_tag:
            continue
        title = link_tag.get_text(strip=True)
        href = link_tag.get("href")
        full_url = urljoin(BASE_URL, href) if href else None

        # 提取描述
        desc_tag = li.select_one("div.text div.details p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # 提取日期和 episode 编号
        details_div = li.select_one("div.text div.details")
        if details_div:
            h3 = details_div.select_one("h3")
            if h3:
                # h3 内容如: "<b>Episode 260723 </b> / 23 Jul 2026"
                parts = h3.get_text(separator=" ", strip=True).split("/")
                if len(parts) >= 2:
                    episode_part = parts[0].strip()  # "Episode 260723"
                    date_part = parts[1].strip()     # "23 Jul 2026"
                else:
                    episode_part = ""
                    date_part = ""
            else:
                episode_part = ""
                date_part = ""
        else:
            episode_part = ""
            date_part = ""

        # 提取 episode 编号（数字）
        ep_match = re.search(r"Episode\s*(\d+)", episode_part)
        episode_number = ep_match.group(1) if ep_match else ""

        # 构建记录
        record = {
            "episode_number": episode_number,  # 例如 "260723"
            "title": title,
            "link": full_url,
            "description": description,
            "date": date_part,                 # 例如 "23 Jul 2026"
        }
        results.append(record)

    return results

def save_to_json(data, filename="6minute_english_episodes.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已保存 {len(data)} 条记录到 {filename}")

def main():
    print("正在获取主页...")
    html = fetch_page(MAIN_URL)
    print("解析页面...")
    episodes = parse_main_page(html)
    print(f"共找到 {len(episodes)} 期节目")
    save_to_json(episodes)

if __name__ == "__main__":
    main()
