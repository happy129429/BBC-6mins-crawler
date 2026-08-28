"""重构目标契约测试（TDD）。

这些测试定义第 3 步重构后的预期行为；重构完成前因模块/函数尚不存在而跳过，
重构完成后必须全部通过，不允许再跳过。
"""
import logging
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

import json_generator

# 模块级跳过守卫：重构创建 scripts/utils.py、scripts/config.py 之前整体跳过
utils = pytest.importorskip("utils", reason="待第 3 步重构创建 scripts/utils.py")
config = pytest.importorskip("config", reason="待第 3 步重构创建 scripts/config.py")


# ---------- utils：媒体扩展名与类型推断（解决 wav/m4a 被存成 .mp3 的问题） ----------

@pytest.mark.parametrize("url,kind,ext", [
    ("https://x.com/a.mp3", "audio", ".mp3"),
    ("https://x.com/a.wav", "audio", ".wav"),
    ("https://x.com/a.m4a", "audio", ".m4a"),
    ("https://x.com/a.mp4", "video", ".mp4"),
])
def test_infer_media_kind_and_ext(url, kind, ext):
    assert utils.infer_media_kind_and_ext(url) == (kind, ext)


def test_infer_media_kind_and_ext_ignores_query_string():
    assert utils.infer_media_kind_and_ext("https://x.com/a.mp3?token=abc") == ("audio", ".mp3")


def test_infer_media_kind_and_ext_unknown():
    assert utils.infer_media_kind_and_ext("https://x.com/page.html") == (None, None)


# ---------- utils：mpd 清单发现（解决三个页面找不到下载按钮的问题） ----------

def test_find_mpd_url_from_page(episode_page_mpd_html):
    soup = BeautifulSoup(episode_page_mpd_html, "html.parser")
    url = utils.find_mpd_url(soup)
    assert url is not None
    assert url.startswith("http")
    assert url.endswith(".mpd")


def test_find_mpd_url_returns_none_on_normal_page(episode_page_html):
    soup = BeautifulSoup(episode_page_html, "html.parser")
    assert utils.find_mpd_url(soup) is None


# ---------- utils：统一的媒体存在性判断（替代 glob("media.*") 猜测） ----------

def test_has_local_media(tmp_path):
    assert utils.has_local_media({}) is False                       # 无字段
    f = tmp_path / "media.mp3"
    assert utils.has_local_media({"local_media_path": str(f)}) is False  # 文件不存在
    f.write_bytes(b"x")
    assert utils.has_local_media({"local_media_path": str(f)}) is True


# ---------- utils：带重试的网络请求 ----------

def test_fetch_with_retry_recovers(monkeypatch):
    calls = []

    class _Resp:
        status_code = 200

    def fake_get(url, **kw):
        calls.append(url)
        if len(calls) < 3:
            raise ConnectionError("boom")
        return _Resp()

    monkeypatch.setattr(utils.requests, "get", fake_get)
    resp = utils.fetch_with_retry("http://x", retries=3, backoff=0)
    assert resp.status_code == 200
    assert len(calls) == 3


def test_fetch_with_retry_raises_after_exhaustion(monkeypatch):
    monkeypatch.setattr(utils.requests, "get",
                        lambda url, **kw: (_ for _ in ()).throw(ConnectionError("down")))
    with pytest.raises(ConnectionError):
        utils.fetch_with_retry("http://x", retries=2, backoff=0)


# ---------- utils：日志落盘 ----------

def test_setup_logging_writes_to_file(tmp_path):
    log_file = tmp_path / "crawler.log"
    logger = utils.setup_logging(log_file)
    logger.info("hello-pytest-log")
    for h in logger.handlers:
        h.flush()
    assert log_file.exists()
    assert "hello-pytest-log" in log_file.read_text(encoding="utf-8")


# ---------- json_generator：增量合并（核心需求：不覆盖已有下载地址） ----------

@pytest.mark.skipif(not hasattr(json_generator, "merge_episodes"),
                    reason="待第 3 步重构实现 merge_episodes")
class TestMergeEpisodes:
    OLD = [{
        "episode_number": "260723", "title": "旧标题",
        "link": "https://www.bbc.co.uk/ep-260723",
        "description": "旧描述", "date": "23 Jul 2026",
        "media_download_url": "https://downloads.bbc.co.uk/a.mp3",
        "local_media_path": "/downloads/260723/a.mp3",
    }]

    NEW = [{
        "episode_number": "260723", "title": "新标题",
        "link": "https://www.bbc.co.uk/ep-260723",
        "description": "新描述", "date": "23 Jul 2026",
    }, {
        "episode_number": "260730", "title": "全新一期",
        "link": "https://www.bbc.co.uk/ep-260730",
        "description": "", "date": "30 Jul 2026",
    }]

    def test_preserves_media_fields(self):
        merged = json_generator.merge_episodes(self.OLD, self.NEW)
        rec = next(r for r in merged if r["episode_number"] == "260723")
        assert rec["media_download_url"] == "https://downloads.bbc.co.uk/a.mp3"
        assert rec["local_media_path"] == "/downloads/260723/a.mp3"

    def test_updates_metadata(self):
        merged = json_generator.merge_episodes(self.OLD, self.NEW)
        rec = next(r for r in merged if r["episode_number"] == "260723")
        assert rec["title"] == "新标题"
        assert rec["description"] == "新描述"

    def test_appends_new_episode(self):
        merged = json_generator.merge_episodes(self.OLD, self.NEW)
        assert any(r["episode_number"] == "260730" for r in merged)
        assert len(merged) == 2

    def test_keeps_old_records_not_on_page(self):
        merged = json_generator.merge_episodes(self.OLD, [])
        assert len(merged) == 1
        assert merged[0]["episode_number"] == "260723"


# ---------- config：跨平台路径与可覆盖配置 ----------

def test_default_save_dir_is_portable(monkeypatch):
    monkeypatch.delenv("BBC6_SAVE_DIR", raising=False)
    d = config.get_save_dir()
    assert isinstance(d, Path)
    assert not str(d).startswith("D:")


def test_save_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("BBC6_SAVE_DIR", str(tmp_path / "custom"))
    assert config.get_save_dir() == tmp_path / "custom"
