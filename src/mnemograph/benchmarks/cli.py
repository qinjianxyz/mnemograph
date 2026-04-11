"""CLI entrypoints for public benchmark runs."""

from argparse import ArgumentParser
from pathlib import Path

from mnemograph.demo import build_default_client
from mnemograph.benchmarks.longmemeval import run_longmemeval_benchmark


def add_benchmark_arguments(parser: ArgumentParser) -> ArgumentParser:
    """Add shared benchmark CLI arguments to a parser."""
    parser.add_argument(
        "benchmark",
        choices=("longmemeval", "memoryagentbench"),
        help="Benchmark adapter to run.",
    )
    parser.add_argument("--dataset-path", required=False, help="Path to the benchmark dataset or split file.")
    parser.add_argument("--result-base-dir", default="benchmarks/results", help="Directory where benchmark artifacts are stored.")
    parser.add_argument("--base-dir", default="/tmp/mnemograph-benchmark-run", help="Base working directory for Mnemograph state during the run.")
    parser.add_argument("--model", default="qwen3.5:latest", help="Model name for the local or hosted OpenAI-compatible endpoint.")
    parser.add_argument("--base-url", default="http://localhost:11434/v1", help="OpenAI-compatible API base URL.")
    parser.add_argument("--replay-mode", choices=("oracle-history", "full-history"), default="full-history", help="How benchmark history is replayed into Mnemograph.")
    parser.add_argument("--case-limit", type=int, default=None, help="Optional cap on the number of benchmark cases to execute.")
    return parser


def build_parser() -> ArgumentParser:
    """Build the standalone benchmark CLI parser."""
    parser = ArgumentParser(prog="mnemograph-benchmark")
    return add_benchmark_arguments(parser)


def main(argv: list[str] | None = None) -> int:
    """Parse benchmark CLI arguments."""
    parser = build_parser()
    args = parser.parse_args(argv)
    llm_client = build_default_client(args.model, args.base_url)
    if args.benchmark == "longmemeval":
        result = run_longmemeval_benchmark(
            dataset_path=Path(args.dataset_path) if args.dataset_path else None,
            result_base_dir=Path(args.result_base_dir),
            working_base_dir=Path(args.base_dir),
            llm_client=llm_client,
            replay_mode=args.replay_mode,
            case_limit=args.case_limit,
        )
        print(
            " ".join(
                [
                    f"benchmark={result['benchmark']}",
                    f"status={result['status']}",
                    f"case_count={result['case_count']}",
                    f"result_dir={result['result_dir']}",
                    f"proxy_exact_match={result['proxy_exact_match']:.3f}",
                    f"proxy_relaxed_exact_match={result['proxy_relaxed_exact_match']:.3f}",
                    f"proxy_contains_match={result['proxy_contains_match']:.3f}",
                ]
            )
        )
        return 0
    raise NotImplementedError("MemoryAgentBench adapter is not implemented yet")
    return 0
