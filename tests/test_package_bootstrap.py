from importlib import metadata


def test_package_metadata_and_cli_entrypoint_exist():
    dist = metadata.distribution("mnemograph")
    console_scripts = {
        entry_point.name: entry_point.value
        for entry_point in dist.entry_points
        if entry_point.group == "console_scripts"
    }
    assert "mnemograph" in console_scripts
