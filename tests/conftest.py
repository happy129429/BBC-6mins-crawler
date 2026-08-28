import sys
from pathlib import Path

# 让测试可以直接 import scripts/ 下的模块（downloader / json_generator / utils / config）
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def main_page_html():
    return (FIXTURES / "main_page.html").read_text(encoding="utf-8")


@pytest.fixture
def episode_page_html():
    return (FIXTURES / "episode_page.html").read_text(encoding="utf-8")


@pytest.fixture
def episode_page_mpd_html():
    return (FIXTURES / "episode_page_mpd.html").read_text(encoding="utf-8")
