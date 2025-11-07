"""Tests for warmup pack helpers."""

from pathlib import Path

import pytest

from src.qnwis.cache import warmup


def test_list_warmup_packs_default() -> None:
    """Default warmup packs file provides named packs."""
    packs = warmup.list_warmup_packs(warmup.PACKS_PATH)
    assert "core_kpis" in packs
    assert "energy_focus" in packs


def test_load_warmup_pack_returns_specs() -> None:
    """Warmup pack entries are dictionaries with fn/params."""
    specs = warmup.load_warmup_pack("core_kpis", warmup.PACKS_PATH)
    assert isinstance(specs, list)
    assert all("fn" in spec and "params" in spec for spec in specs)


def test_unknown_pack_raises(tmp_path: Path) -> None:
    """Unknown pack raises WarmupPackError."""
    pack_file = tmp_path / "packs.yml"
    pack_file.write_text("example: []", encoding="utf-8")
    with pytest.raises(warmup.WarmupPackError):
        warmup.load_warmup_pack("missing", pack_file)
