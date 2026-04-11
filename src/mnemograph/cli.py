"""CLI entrypoint for Mnemograph."""

from argparse import ArgumentParser
import json
from pathlib import Path

from mnemograph.benchmarks.cli import add_benchmark_arguments
from mnemograph.benchmarks.cli import main as run_benchmark_cli
from mnemograph.chat.loop import ChatSession
from mnemograph.demo import build_default_client, render_demo_report, run_demo
from mnemograph.engine import Mnemograph


def main(argv: list[str] | None = None) -> int:
    """Run the Mnemograph command-line interface."""
    parser = ArgumentParser(prog="mnemograph")
    subparsers = parser.add_subparsers(dest="command")

    demo_parser = subparsers.add_parser("demo")
    demo_parser.add_argument("--base-dir", default="demo-output")
    demo_parser.add_argument("--company-url", default="https://stripe.com")
    demo_parser.add_argument("--model", default="qwen3.5:latest")
    demo_parser.add_argument("--base-url", default="http://localhost:11434/v1")
    demo_parser.add_argument("--max-pages", default=3, type=int)

    ingest_url_parser = subparsers.add_parser("ingest-url")
    ingest_url_parser.add_argument("url")
    ingest_url_parser.add_argument("--base-dir", default="demo-output")
    ingest_url_parser.add_argument("--model", default="qwen3.5:latest")
    ingest_url_parser.add_argument("--base-url", default="http://localhost:11434/v1")

    ingest_text_parser = subparsers.add_parser("ingest-text")
    ingest_text_parser.add_argument("text")
    ingest_text_parser.add_argument("--source", default="user")
    ingest_text_parser.add_argument("--base-dir", default="demo-output")
    ingest_text_parser.add_argument("--model", default="qwen3.5:latest")
    ingest_text_parser.add_argument("--base-url", default="http://localhost:11434/v1")

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("question")
    query_parser.add_argument("--base-dir", default="demo-output")
    query_parser.add_argument("--model", default="qwen3.5:latest")
    query_parser.add_argument("--base-url", default="http://localhost:11434/v1")

    chat_parser = subparsers.add_parser("chat")
    chat_parser.add_argument("--base-dir", default="demo-output")
    chat_parser.add_argument("--model", default="qwen3.5:latest")
    chat_parser.add_argument("--base-url", default="http://localhost:11434/v1")

    benchmark_parser = subparsers.add_parser("benchmark")
    add_benchmark_arguments(benchmark_parser)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    client = build_default_client(args.model, args.base_url)

    if args.command == "demo":
        result = run_demo(
            base_dir=Path(args.base_dir),
            llm_client=client,
            company_url=args.company_url,
            max_pages=args.max_pages,
        )
        result["company_url"] = args.company_url
        print(render_demo_report(result))
        return 0

    engine = Mnemograph(Path(args.base_dir), llm_client=client)

    if args.command == "ingest-url":
        result = engine.ingest_url(args.url)
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
        return 0

    if args.command == "ingest-text":
        result = engine.ingest_text(args.text, source=args.source)
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
        return 0

    if args.command == "query":
        result = engine.query(args.question)
        print(json.dumps(result.__dict__, indent=2, sort_keys=True))
        return 0

    if args.command == "benchmark":
        return run_benchmark_cli(argv[1:] if argv is not None else None)

    session = ChatSession(engine)
    while True:
        try:
            user_input = input("you> ").strip()
        except EOFError:
            break
        if user_input.lower() in {"exit", "quit"}:
            break
        result = session.handle_turn(user_input)
        print(f"assistant> {result.answer}")
    return 0
