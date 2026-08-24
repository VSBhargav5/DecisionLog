from pathlib import Path

from decisionlog.config import load_config, owner_aliases, save_config


def test_config_roundtrip(tmp_path: Path):
    path = tmp_path / "config.json"
    save_config({"owner_aliases": {"sk": "Sarah"}, "default_owner": "Sarah"}, path)
    cfg = load_config(path)
    assert cfg["default_owner"] == "Sarah"
    assert owner_aliases(cfg)["sk"] == "Sarah"


def test_missing_config(tmp_path: Path):
    assert load_config(tmp_path / "nope.json") == {}
