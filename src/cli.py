"""BioAgent CLI - command-line interface for BioAgent."""

import argparse
import logging
import sys

from .agent import BioAgent
from .config import config


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main():
    # Force UTF-8 on Windows: default locale encoding (GBK/cp936) corrupts
    # non-ASCII output (e.g. en-dashes in gene coordinates) when redirected.
    for stream in (sys.stdout, sys.stderr):
        if stream.encoding and stream.encoding.lower() not in ("utf-8", "utf8"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="BioAgent - AI-Powered Bioinformatics Research Assistant"
    )
    parser.add_argument("-q", "--query", type=str, help="Single query mode")
    parser.add_argument("--web", action="store_true", help="Start web UI (same as --serve)")
    parser.add_argument("--serve", action="store_true", help="Start web server")
    parser.add_argument("--port", type=int, default=8000, help="Web server port (default: 8000)")
    parser.add_argument("--version", action="version", version=f"BioAgent v{config.VERSION}")
    args = parser.parse_args()

    setup_logging()
    config.check()

    if args.web or args.serve or (not args.query):
        # Web mode (default for Docker / no arguments)
        from .web import start_server

        print(f"Starting BioAgent web server on http://0.0.0.0:{args.port}")
        start_server(port=args.port)
    else:
        # Single query mode
        agent = BioAgent()
        print(f"BioAgent v{config.VERSION} | Provider: {config.AGENT_PROVIDER} | Model: {config.AGENT_MODEL}")
        print(f"\nQuery: {args.query}\n")
        print("=" * 60)
        try:
            result = agent.chat(args.query)
            print(result)
        except KeyboardInterrupt:
            print("\n\nInterrupted.")
            sys.exit(0)
        except Exception as e:
            print(f"\nError: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
