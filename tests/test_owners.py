from decisionlog.owners import load_alias_map, normalize_owner


def test_normalize_basic():
    assert normalize_owner("  sarah k. ") == "Sarah K"
    assert normalize_owner("") is None
    assert normalize_owner(None) is None


def test_alias_map():
    aliases = load_alias_map({"sk": "Sarah", "sarah k": "Sarah"})
    assert normalize_owner("sk", aliases) == "Sarah"
    assert normalize_owner("Sarah K", aliases) == "Sarah"
