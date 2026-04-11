"""CLI for running Mnemograph eval cases."""

from argparse import ArgumentParser
from pathlib import Path

from mnemograph.demo import build_default_client
from mnemograph.evals.harness import evaluate_scenario, expand_case_paths, load_eval_case


def main(argv: list[str] | None = None) -> int:
    """Run one or more eval cases and print a compact report."""
    parser = ArgumentParser(prog="mnemograph-eval")
    parser.add_argument("cases", nargs="+", help="YAML files, directories, or glob patterns")
    parser.add_argument("--base-dir", default="eval-output")
    parser.add_argument("--model", default="qwen3.5:latest")
    parser.add_argument("--base-url", default="http://localhost:11434/v1")
    args = parser.parse_args(argv)

    case_paths = expand_case_paths(args.cases)
    client = build_default_client(args.model, args.base_url)
    base_root = Path(args.base_dir)
    base_root.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    print("Local eval run (self-reported, reproducible)")
    for case_path in case_paths:
        case = load_eval_case(case_path)
        case_base_dir = base_root / case["id"]
        result = evaluate_scenario(case, case_base_dir, client)
        results.append(result)
        print(
            f"{result['case_id']}: passed={result['score']['passed']} "
            f"failed={result['score']['failed']} "
            f"assertions={len(result['assertions'])} "
            f"latency_ms={result['metrics']['latency_ms']:.1f} "
            f"cost_usd={result['metrics']['cost_usd']:.4f}"
        )

    total_passed = sum(result["score"]["passed"] for result in results)
    total_failed = sum(result["score"]["failed"] for result in results)
    total_assertions = sum(len(result["assertions"]) for result in results)
    print("Summary")
    print(
        f"cases={len(results)} assertions={total_assertions} "
        f"passed={total_passed} failed={total_failed}"
    )
    return 0 if total_failed == 0 else 1
