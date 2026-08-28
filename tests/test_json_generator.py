"""json_generator 现有行为测试（全部离线，不发真实网络请求）。"""
import json

import json_generator


# ---------- fetch_page ----------

class _FakeResp:
    def __init__(self, text="<html></html>"):
        self.text = text
        self.encoding = None

    def raise_for_status(self):
        pass


def test_fetch_page_returns_text_and_sets_utf8(monkeypatch):
    captured = {}

    def fake_get(url, headers=None):
        captured["url"] = url
        return _FakeResp("<html>hi</html>")

    monkeypatch.setattr(json_generator.requests, "get", fake_get)
    html = json_generator.fetch_page("http://example.com/page")
    assert html == "<html>hi</html>"
    assert captured["url"] == "http://example.com/page"


def test_fetch_page_raises_on_http_error(monkeypatch):
    import requests

    def raise_for_status(self):
        raise requests.HTTPError("404")

    _FakeResp.raise_for_status = raise_for_status
    monkeypatch.setattr(json_generator.requests, "get", lambda url, headers=None: _FakeResp())
    import pytest

    with pytest.raises(requests.HTTPError):
        json_generator.fetch_page("http://example.com/bad")


# ---------- parse_main_page ----------

def test_parse_main_page_extracts_all_fields(main_page_html):
    eps = json_generator.parse_main_page(main_page_html)
    assert len(eps) == 3
    first = eps[0]
    assert first["episode_number"] == "260723"
    assert first["title"] == "When does sadness become depression?"
    assert first["link"] == (
        "https://www.bbc.co.uk/learningenglish/english/features/6-minute-english/ep-260723"
    )
    assert first["description"] == "Phil and Georgie discuss mental health."
    assert first["date"] == "23 Jul 2026"


def test_parse_main_page_returns_empty_on_no_items():
    assert json_generator.parse_main_page("<html><body></body></html>") == []


# ---------- save_to_json ----------

def test_save_to_json_writes_file(tmp_path):
    p = tmp_path / "episodes.json"
    data = [{"episode_number": "260723", "title": "T"}]
    json_generator.save_to_json(data, str(p))
    assert json.loads(p.read_text(encoding="utf-8")) == data


def test_save_to_json_prints_count(tmp_path, capsys):
    p = tmp_path / "episodes.json"
    data = [{"episode_number": str(i)} for i in range(5)]
    json_generator.save_to_json(data, str(p))
    out = capsys.readouterr().out
    assert "5" in out
    assert p.exists()
