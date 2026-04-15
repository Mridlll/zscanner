from __future__ import annotations

import json
from pathlib import Path


INTERVAL_MAP = {
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
}


def _prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        val = input(f"{label}{suffix}: ").strip()
        if val:
            return val
        if default is not None:
            return default


def _prompt_choice(label: str, choices: list[str], default: str) -> str:
    opts = "/".join(choices)
    while True:
        val = _prompt(f"{label} ({opts})", default).lower()
        if val in choices:
            return val
        print(f"  invalid. choose one of: {opts}")


def _prompt_float(label: str, default: float) -> float:
    while True:
        val = _prompt(label, str(default))
        try:
            return float(val)
        except ValueError:
            print("  invalid number.")


def _prompt_int(label: str, default: int, minimum: int = 1) -> int:
    while True:
        val = _prompt(label, str(default))
        try:
            n = int(val)
            if n >= minimum:
                return n
        except ValueError:
            pass
        print(f"  invalid integer (>= {minimum}).")


def _write_env(env_path: Path, webhook: str) -> None:
    lines = []
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DISCORD_WEBHOOK_URL="):
                continue
            lines.append(line)
    lines.append(f"DISCORD_WEBHOOK_URL={webhook}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_wizard(config_path: Path, env_path: Path) -> None:
    existing = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}

    print("zscanner setup")
    print("--------------")

    while True:
        webhook = _prompt("Discord webhook URL")
        if webhook.startswith("https://discord.com/api/webhooks/") or webhook.startswith(
            "https://discordapp.com/api/webhooks/"
        ):
            break
        print("  must start with https://discord.com/api/webhooks/")

    cur_interval = existing.get("scan_interval", "15m")
    interval_choice = _prompt_choice(
        "Scan interval", ["5m", "15m", "30m", "1h", "custom"], cur_interval if cur_interval in INTERVAL_MAP else "15m"
    )
    if interval_choice == "custom":
        mins = _prompt_int("Custom interval minutes", max(1, existing.get("scan_interval_seconds", 900) // 60))
        scan_interval_seconds = mins * 60
        scan_interval_label = f"{mins}m"
    else:
        scan_interval_seconds = INTERVAL_MAP[interval_choice]
        scan_interval_label = interval_choice

    cur_universe = existing.get("universe", "top_volume")
    universe = _prompt_choice("Symbol universe", ["all", "top_volume"], cur_universe)
    top_n_universe = existing.get("top_n_universe", 100)
    if universe == "top_volume":
        top_n_universe = _prompt_int("Top N by 24h quote volume", top_n_universe)

    threshold = _prompt_float("Z-score threshold to flag", existing.get("z_threshold", 2.0))
    top_n_chart = _prompt_int("Top N in charts", existing.get("top_n_chart", 15))
    cooldown_minutes = _prompt_int("Cooldown minutes per symbol", existing.get("cooldown_minutes", 240))

    w = existing.get("weights", {"oi": 0.4, "price": 0.2, "funding": 0.2, "volume": 0.1, "basis": 0.1})
    w_oi = _prompt_float("Weight: OI", w.get("oi", 0.4))
    w_price = _prompt_float("Weight: Price", w.get("price", 0.2))
    w_funding = _prompt_float("Weight: Funding", w.get("funding", 0.2))
    w_volume = _prompt_float("Weight: Volume", w.get("volume", 0.1))
    w_basis = _prompt_float("Weight: Basis", w.get("basis", 0.1))
    total = w_oi + w_price + w_funding + w_volume + w_basis
    if total <= 0:
        w_oi, w_price, w_funding, w_volume, w_basis = 0.4, 0.2, 0.2, 0.1, 0.1
        total = 1.0
    weights = {
        "oi": w_oi / total,
        "price": w_price / total,
        "funding": w_funding / total,
        "volume": w_volume / total,
        "basis": w_basis / total,
    }

    config = {
        "scan_interval": scan_interval_label,
        "scan_interval_seconds": scan_interval_seconds,
        "universe": universe,
        "top_n_universe": top_n_universe,
        "z_threshold": threshold,
        "top_n_chart": top_n_chart,
        "cooldown_minutes": cooldown_minutes,
        "weights": weights,
    }

    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    _write_env(env_path, webhook)

    print()
    print("Setup complete. Run with: python -m zscanner")
