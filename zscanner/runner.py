from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .binance import BinanceFutures
from .zscore import build_metrics
from .chart import scatter_oi_vs_price, bar_top_composite, bar_top_oi_30m
from .discord import post, build_embed

log = logging.getLogger("zscanner")

OI_WINDOWS = [
    ("30m", "5m", 6),
    ("1h", "5m", 12),
    ("4h", "5m", 48),
]

_last_alert: dict[str, float] = {}


async def _gather_universe(client: BinanceFutures, cfg: dict) -> list[str]:
    if cfg["universe"] == "all":
        return await client.list_perpetuals()

    perps = set(await client.list_perpetuals())
    tickers = await client.ticker_24h()
    if not isinstance(tickers, list):
        return []
    filtered = [t for t in tickers if t.get("symbol") in perps]
    filtered.sort(key=lambda t: float(t.get("quoteVolume", 0) or 0), reverse=True)
    top = filtered[: cfg["top_n_universe"]]
    return [t["symbol"] for t in top]


async def run_once(client: BinanceFutures, cfg: dict, webhook_url: str) -> None:
    symbols = await _gather_universe(client, cfg)
    if not symbols:
        log.warning("no symbols returned")
        return
    log.info("universe: %d symbols", len(symbols))

    oi_tasks = {
        win_name: asyncio.gather(*[client.oi_window_pct(s, period, bars) for s in symbols])
        for win_name, period, bars in OI_WINDOWS
    }
    fund_task = asyncio.gather(*[client.funding_apr(s) for s in symbols])
    tick_task = asyncio.gather(*[client.ticker_24h(s) for s in symbols])
    fut_price_task = asyncio.gather(*[client.futures_price(s) for s in symbols])
    spot_price_task = asyncio.gather(*[client.spot_price(s) for s in symbols])

    oi_results_by_window = {win: await t for win, t in oi_tasks.items()}
    fund_results, tick_results, fut_prices, spot_prices = await asyncio.gather(
        fund_task, tick_task, fut_price_task, spot_price_task
    )

    oi_changes_by_window: dict[str, dict[str, float]] = {win: {} for win in oi_results_by_window}
    price_changes: dict[str, float] = {}
    funding_aprs: dict[str, float] = {}
    volumes: dict[str, float] = {}
    basis_pcts: dict[str, float] = {}

    for i, s in enumerate(symbols):
        for win, results in oi_results_by_window.items():
            if results[i] is not None:
                oi_changes_by_window[win][s] = results[i]
        if fund_results[i] is not None:
            funding_aprs[s] = fund_results[i]
        t = tick_results[i]
        if isinstance(t, dict):
            try:
                price_changes[s] = float(t["priceChangePercent"])
            except (KeyError, ValueError, TypeError):
                pass
            try:
                volumes[s] = float(t["quoteVolume"])
            except (KeyError, ValueError, TypeError):
                pass
        fp = fut_prices[i]
        sp = spot_prices[i]
        if fp is not None and sp is not None and sp != 0:
            basis_pcts[s] = (fp - sp) / sp * 100.0

    metrics = build_metrics(
        symbols,
        oi_changes_by_window,
        price_changes,
        funding_aprs,
        volumes,
        basis_pcts,
        cfg["weights"],
    )
    if not metrics:
        log.warning("no metrics produced")
        return
    log.info("metrics: %d symbols scored", len(metrics))

    tmp = Path(tempfile.mkdtemp(prefix="zscanner_"))
    scatter_path = tmp / "scatter.png"
    bar_path = tmp / "top.png"
    early_path = tmp / "early.png"
    scatter_oi_vs_price(metrics, scatter_path)
    bar_top_composite(metrics, cfg["top_n_chart"], bar_path)
    bar_top_oi_30m(metrics, cfg["top_n_chart"], early_path)

    top_sorted = sorted(metrics, key=lambda m: m["composite"], reverse=True)

    cooldown_seconds = float(cfg.get("cooldown_minutes", 240)) * 60.0
    now = time.time()
    flagged = []
    for m in top_sorted:
        if abs(m["composite"]) < cfg["z_threshold"]:
            continue
        last = _last_alert.get(m["symbol"], 0.0)
        if now - last < cooldown_seconds:
            continue
        flagged.append(m)
        _last_alert[m["symbol"]] = now

    ts = datetime.now(timezone.utc).isoformat()
    title = f"zscanner — multi-timeframe OI, {len(metrics)} symbols"
    embed = build_embed(title, ts, top_sorted)

    content = f"Flagged (|composite| >= {cfg['z_threshold']:.1f}): {len(flagged)}"
    ok = await post(webhook_url, content, embed, [scatter_path, bar_path, early_path])
    log.info("posted to discord: %s", ok)


async def loop_forever(cfg: dict, webhook_url: str) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    async with BinanceFutures(concurrency=10) as client:
        while True:
            try:
                await run_once(client, cfg, webhook_url)
            except Exception as e:
                log.exception("run_once failed: %s", e)
            await asyncio.sleep(cfg["scan_interval_seconds"])
