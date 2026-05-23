"""Tests for Pydantic validators in schemas/template.py (FFmpeg injection protection)."""
import pytest
from pydantic import ValidationError
from app.schemas.template import TemplateCreate


def _make(**kwargs) -> TemplateCreate:
    defaults = {"name": "Test"}
    defaults.update(kwargs)
    return TemplateCreate(**defaults)


# ── Color validator ───────────────────────────────────────────────────────────

def test_color_uppercase_passes():
    t = _make(title_color="#FFFFFF")
    assert t.title_color == "#FFFFFF"


def test_color_lowercase_passes():
    t = _make(waveform_color="#00ff88")
    assert t.waveform_color == "#00ff88"


def test_color_mixed_case_passes():
    t = _make(title_color="#aAbBcC")
    assert t.title_color == "#aAbBcC"


def test_color_eight_digits_rejected():
    with pytest.raises(ValidationError):
        _make(title_color="#FFFFFFFF")


def test_color_no_hash_rejected():
    with pytest.raises(ValidationError):
        _make(title_color="FFFFFF")


def test_color_named_rejected():
    with pytest.raises(ValidationError):
        _make(waveform_color="red")


def test_color_short_hex_rejected():
    with pytest.raises(ValidationError):
        _make(title_color="#FFF")


# ── Expression validator ──────────────────────────────────────────────────────

def test_expr_center_passes():
    t = _make(title_x="(w-text_w)/2")
    assert t.title_x == "(w-text_w)/2"


def test_expr_plain_number_passes():
    t = _make(watermark_y="40")
    assert t.watermark_y == "40"


def test_expr_watermark_x_passes():
    t = _make(watermark_x="w-overlay_w-40")
    assert t.watermark_x == "w-overlay_w-40"


def test_expr_semicolon_rejected():
    with pytest.raises(ValidationError):
        _make(title_x="; rm -rf /")


def test_expr_dollar_rejected():
    with pytest.raises(ValidationError):
        _make(watermark_x="$(reboot)")


def test_expr_backtick_rejected():
    with pytest.raises(ValidationError):
        _make(title_x="`id`")


def test_expr_colon_rejected():
    with pytest.raises(ValidationError):
        _make(watermark_y="40:option=value")


# ── waveform_mode validator ───────────────────────────────────────────────────

def test_waveform_mode_bars_passes():
    t = _make(waveform_mode="bars")
    assert t.waveform_mode == "bars"


def test_waveform_mode_cline_rejected():
    with pytest.raises(ValidationError):
        _make(waveform_mode="cline")


def test_waveform_mode_arbitrary_rejected():
    with pytest.raises(ValidationError):
        _make(waveform_mode="showfreqs")


# ── title_font validator ──────────────────────────────────────────────────────

def test_title_font_valid_passes():
    for font in ("liberation", "montserrat", "lato", "bebas", "ubuntu"):
        t = _make(title_font=font)
        assert t.title_font == font


def test_title_font_invalid_rejected():
    with pytest.raises(ValidationError):
        _make(title_font="comic_sans")
