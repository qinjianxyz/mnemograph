from mnemograph.paths import mirror_paths


def test_mirror_paths_match_hobbes_layout():
    paths = mirror_paths("memory")
    assert paths["working"].endswith("memory/working")
    assert paths["knowledge"].endswith("memory/knowledge")
    assert paths["sources"].endswith("memory/sources")
