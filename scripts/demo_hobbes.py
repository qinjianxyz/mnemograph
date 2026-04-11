#!/usr/bin/env python3
"""Run the public Mnemograph demo flow."""

from argparse import ArgumentParser
from pathlib import Path

from mnemograph.demo import build_default_client, render_demo_report, run_demo, write_demo_report


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument("--base-dir", default="demo-output")
    parser.add_argument("--company-url", default="https://stripe.com")
    parser.add_argument("--model", default="qwen3.5:latest")
    parser.add_argument("--base-url", default="http://localhost:11434/v1")
    parser.add_argument("--max-pages", default=3, type=int)
    args = parser.parse_args()

    result = run_demo(
        base_dir=Path(args.base_dir),
        llm_client=build_default_client(model=args.model, base_url=args.base_url),
        company_url=args.company_url,
        max_pages=args.max_pages,
    )
    result["company_url"] = args.company_url
    report = render_demo_report(result)
    write_demo_report(Path(args.base_dir), report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
