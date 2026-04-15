from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .setup import run_wizard
from .runner import loop_forever


CONFIG_PATH = Path("config.json")
ENV_PATH = Path(".env")


def main() -> int:
    parser = argparse.ArgumentParser(prog="zscanner")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("setup", help="interactive configuration wizard")
    args = parser.parse_args()

    if args.cmd == "setup":
        run_wizard(CONFIG_PATH, ENV_PATH)
        return 0

    if not CONFIG_PATH.exists():
        print("Run `python -m zscanner setup` first")
        return 1

    load_dotenv(ENV_PATH)
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        print("DISCORD_WEBHOOK_URL not set in .env. Run `python -m zscanner setup`.")
        return 1

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    try:
        asyncio.run(loop_forever(cfg, webhook))
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
