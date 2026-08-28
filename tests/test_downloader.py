"""downloader 现有行为测试（全部离线，不发真实网络请求）。"""
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

import downloader


# ---------- sanitize_filename ----------

def test_sanitize_filename_replaces_illegal_chars():
    assert downloader.sanitize_filename('a<b>:c"/d\\e|f?g*h') == "a_b__c__d_e_f_g_h"


def test_sanitize_filename_truncates_to_40():
    assert len(downloader.sanitize_filename("x" * 50)) == 40


def test_sanitize_filename_strips_whitespace():
    assert downloader.sanitize_filename("  title  ") == "title"


# ---------- parse_date ----------

def test_parse_date_valid():
    assert downloader.parse_date("23 Jul 2026") == datetime(2026, 7, 23)


def test_parse_date_invalid_returns_none():
    assert downloader.parse_date("not a date") is None
    assert downloader.parse_date("") is None
    assert downloader.parse_date(None) is None


# ---------- clean_transcript ----------

def test_clean_transcript_cuts_at_marker1():
    assert downloader.clean_transcript("Hello\n\nLatest 6 Minute English\nJUNK") == "Hello"


def test_clean_transcript_cuts_at_marker2():
    text = "Body\nNext\nFind an\nA-Z list of our programmes\nJUNK"
    assert downloader.clean_transcript(text) == "Body"


def test_clean_transcript_collapses_blank_lines():
    assert downloader.clean_transcript("a\n\n\n\nb") == "a\n\nb"


def test_clean_transcript_empty():
    assert downloader.clean_transcript("") == ""
    assert downloader.clean_transcript(None) == ""


# ---------- get_media_url（当前行为） ----------

def test_get_media_url_prefers_download_area_mp3(episode_page_html):
    soup = BeautifulSoup(episode_page_html, "html.parser")
    url, kind = downloader.get_media_url(soup, "https://www.bbc.co.uk/fake")
    assert kind == "audio"
    assert url.endswith(".mp3")


def test_get_media_url_audio_source_fallback():
    html = '<audio controls><source src="https://downloads.bbc.co.uk/x/audio.wav"></audio>'
    soup = BeautifulSoup(html, "html.parser")
    url, kind = downloader.get_media_url(soup, "https://www.bbc.co.uk/fake")
    assert kind == "audio"
    assert url.endswith(".wav")


def test_get_media_url_data_media_attribute():
    html = '<div data-media="https://example.com/v.mp4"></div>'
    soup = BeautifulSoup(html, "html.parser")
    url, kind = downloader.get_media_url(soup, "https://www.bbc.co.uk/fake")
    assert (url, kind) == ("https://example.com/v.mp4", "video")


def test_get_media_url_returns_none_on_mpd_only_page(episode_page_mpd_html):
    """当前行为：只有 mpd 清单的页面找不到直链（这正是重构要解决的问题）。"""
    soup = BeautifulSoup(episode_page_mpd_html, "html.parser")
    assert downloader.get_media_url(soup, "https://www.bbc.co.uk/fake") == (None, None)


# ---------- extract_text_content ----------

def test_extract_text_content_removes_junk(episode_page_html):
    soup = BeautifulSoup(episode_page_html, "html.parser")
    text = downloader.extract_text_content(soup)
    assert "sample transcript sentence" in text
    assert "Latest 6 Minute English" not in text
    assert "A-Z list" not in text
    assert "tracker" not in text  # script 标签被移除


# ---------- is_transcript_cleaned ----------

def test_is_transcript_cleaned(tmp_path):
    folder = tmp_path
    assert downloader.is_transcript_cleaned(folder) is False  # 文件不存在

    t = folder / "transcript.txt"
    t.write_text("hello\nLatest 6 Minute English\njunk", encoding="utf-8")
    assert downloader.is_transcript_cleaned(folder) is False

    t.write_text("clean text", encoding="utf-8")
    assert downloader.is_transcript_cleaned(folder) is True


# ---------- download_file ----------

class _FakeStreamResp:
    def __init__(self, chunks):
        self.headers = {"content-length": str(sum(len(c) for c in chunks))}
        self._chunks = chunks

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield from self._chunks

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_download_file_success(tmp_path, monkeypatch):
    captured = {}

    def fake_get(url, headers=None, stream=False, timeout=None):
        captured["url"] = url
        return _FakeStreamResp([b"ab", b"cd"])

    monkeypatch.setattr(downloader.requests, "get", fake_get)
    dest = tmp_path / "media.mp3"
    assert downloader.download_file("https://example.com/a.mp3", dest) is True
    assert dest.read_bytes() == b"abcd"
    assert captured["url"] == "https://example.com/a.mp3"


def test_download_file_normalizes_protocol_relative_url(tmp_path, monkeypatch):
    captured = {}

    def fake_get(url, headers=None, stream=False, timeout=None):
        captured["url"] = url
        return _FakeStreamResp([b"x"])

    monkeypatch.setattr(downloader.requests, "get", fake_get)
    dest = tmp_path / "media.mp3"
    downloader.download_file("//example.com/a.mp3", dest)
    assert captured["url"] == "https://example.com/a.mp3"


def test_download_file_removes_partial_file_on_error(tmp_path, monkeypatch):
    class _BrokenResp(_FakeStreamResp):
        def iter_content(self, chunk_size):
            yield b"partial"
            raise RuntimeError("connection reset")

    monkeypatch.setattr(downloader.requests, "get",
                        lambda url, **kw: _BrokenResp([b"partial"]))
    dest = tmp_path / "media.mp3"
    assert downloader.download_file("https://example.com/a.mp3", dest) is False
    assert not dest.exists()  # 失败后清理残留文件


# ---------- extract_audio_from_video ----------

def test_extract_audio_missing_ffmpeg(monkeypatch, tmp_path):
    def fake_run(cmd, **kw):
        if cmd and cmd[0] == "ffmpeg":
            raise FileNotFoundError("no ffmpeg")
        raise AssertionError("unexpected subprocess call")

    monkeypatch.setattr(downloader.subprocess, "run", fake_run)
    assert downloader.extract_audio_from_video(tmp_path / "v.mp4", tmp_path / "a.mp3") is False


def test_extract_audio_success(monkeypatch, tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"video")
    audio = tmp_path / "a.mp3"

    def fake_run(cmd, **kw):
        if "-version" in cmd:
            return SimpleNamespace(returncode=0)
        audio.write_bytes(b"audio")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(downloader.subprocess, "run", fake_run)
    assert downloader.extract_audio_from_video(video, audio) is True
    assert audio.exists()
