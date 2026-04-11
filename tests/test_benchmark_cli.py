import pytest

from mnemograph import cli


def test_top_level_cli_exposes_benchmark_subcommand(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["benchmark", "--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "longmemeval" in output
    assert "memoryagentbench" in output
    assert "--dataset-path" in output


def test_top_level_cli_dispatches_benchmark_runner(monkeypatch, tmp_path):
    captured = {}

    def fake_run_benchmark_cli(argv):
        captured["argv"] = argv
        return 0

    monkeypatch.setattr(
        cli,
        "run_benchmark_cli",
        fake_run_benchmark_cli,
    )

    exit_code = cli.main(
        [
            "benchmark",
            "longmemeval",
            "--dataset-path",
            str(tmp_path / "dataset.json"),
            "--case-limit",
            "2",
        ]
    )

    assert exit_code == 0
    assert captured["argv"] == [
        "longmemeval",
        "--dataset-path",
        str(tmp_path / "dataset.json"),
        "--case-limit",
        "2",
    ]


def test_dedicated_benchmark_cli_exposes_expected_flags(capsys):
    from mnemograph.benchmarks import cli as benchmark_cli

    with pytest.raises(SystemExit) as excinfo:
        benchmark_cli.main(["--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert "longmemeval" in output
    assert "memoryagentbench" in output
    assert "--result-base-dir" in output
    assert "--replay-mode" in output


def test_dedicated_benchmark_cli_dispatches_longmemeval_runner(monkeypatch, tmp_path):
    from mnemograph.benchmarks import cli as benchmark_cli

    captured = {}

    monkeypatch.setattr(
        benchmark_cli,
        "build_default_client",
        lambda model, base_url: {"model": model, "base_url": base_url},
    )
    monkeypatch.setattr(
        benchmark_cli,
        "run_longmemeval_benchmark",
        lambda **kwargs: captured.update(kwargs) or {
            "benchmark": "longmemeval",
            "status": "ok",
            "case_count": 3,
            "result_dir": str(tmp_path / "results"),
            "proxy_exact_match": 0.5,
            "proxy_relaxed_exact_match": 0.5,
            "proxy_contains_match": 1.0,
        },
    )

    exit_code = benchmark_cli.main(
        [
            "longmemeval",
            "--dataset-path",
            str(tmp_path / "dataset.json"),
            "--result-base-dir",
            str(tmp_path / "results"),
            "--base-dir",
            str(tmp_path / "working"),
            "--case-limit",
            "3",
        ]
    )

    assert exit_code == 0
    assert captured["dataset_path"] == tmp_path / "dataset.json"
    assert captured["result_base_dir"] == tmp_path / "results"
    assert captured["working_base_dir"] == tmp_path / "working"
    assert captured["case_limit"] == 3
    assert captured["replay_mode"] == "full-history"


def test_dedicated_benchmark_cli_prints_summary(monkeypatch, tmp_path, capsys):
    from mnemograph.benchmarks import cli as benchmark_cli

    monkeypatch.setattr(
        benchmark_cli,
        "build_default_client",
        lambda model, base_url: {"model": model, "base_url": base_url},
    )
    monkeypatch.setattr(
        benchmark_cli,
        "run_longmemeval_benchmark",
        lambda **kwargs: {
            "benchmark": "longmemeval",
            "status": "proxy_only",
            "case_count": 2,
            "result_dir": str(tmp_path / "results"),
            "proxy_exact_match": 0.5,
            "proxy_relaxed_exact_match": 1.0,
            "proxy_contains_match": 1.0,
        },
    )

    exit_code = benchmark_cli.main(
        [
            "longmemeval",
            "--dataset-path",
            str(tmp_path / "dataset.json"),
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "benchmark=longmemeval" in output
    assert "status=proxy_only" in output
    assert "case_count=2" in output
    assert "proxy_exact_match=0.500" in output
    assert "proxy_relaxed_exact_match=1.000" in output
    assert "proxy_contains_match=1.000" in output
