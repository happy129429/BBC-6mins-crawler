"""终端输出语言（i18n）测试。"""
from pathlib import Path

import config
import utils


# ---------- config.get_language ----------

def test_default_language_is_zh(monkeypatch):
    monkeypatch.delenv(config.LANGUAGE_ENV, raising=False)
    assert config.get_language() == "zh"


def test_language_env_override(monkeypatch):
    monkeypatch.setenv(config.LANGUAGE_ENV, "en")
    assert config.get_language() == "en"


def test_language_env_case_insensitive(monkeypatch):
    monkeypatch.setenv(config.LANGUAGE_ENV, "EN")
    assert config.get_language() == "en"


def test_invalid_language_falls_back_to_zh(monkeypatch):
    monkeypatch.setenv(config.LANGUAGE_ENV, "fr")
    assert config.get_language() == "zh"


# ---------- utils.msg ----------

def test_msg_chinese_by_default(monkeypatch):
    monkeypatch.delenv(config.LANGUAGE_ENV, raising=False)
    assert utils.msg("media_not_found") == utils.MESSAGES["zh"]["media_not_found"]


def test_msg_english(monkeypatch):
    monkeypatch.setenv(config.LANGUAGE_ENV, "en")
    assert utils.msg("media_not_found") == utils.MESSAGES["en"]["media_not_found"]


def test_msg_formats_kwargs(monkeypatch):
    monkeypatch.setenv(config.LANGUAGE_ENV, "en")
    assert "7" in utils.msg("json_loaded", n=7)


# ---------- 文案表完整性 ----------

def test_message_tables_have_same_keys():
    assert set(utils.MESSAGES["zh"]) == set(utils.MESSAGES["en"])
    assert len(utils.MESSAGES["zh"]) >= 30  # 覆盖全部用户可见文案


def test_scripts_route_output_through_msg():
    """两个脚本的终端文案必须经由 msg()，不得残留硬编码中文。"""
    scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
    for name in ("downloader.py", "json_generator.py"):
        src = (scripts_dir / name).read_text(encoding="utf-8")
        assert "msg(" in src
        assert "将使用旧文本" not in src
