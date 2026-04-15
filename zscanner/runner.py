from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .binance import BinanceFutures
from .zscore import build_metrics
from .chart import scatter_oi_vs_price, bar_top_composite
from .discord import post, build_embed

log = logging.getLogger("zscanner")


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

    oi_task = asyncio.gather(*[
        client.oi_window_pct(s, cfg["oi_period"], cfg["oi_lookback_bars"]) for s in symbols
    ])
    fund_task = asyncio.gather(*[client.funding_apr(s) for s in symbols])
    tick_task = asyncio.gather(*[client.ticker_24h(s) for s in symbols])

    oi_results, fund_results, tick_results = await asyncio.gather(oi_task, fund_task, tick_task)

    oi_changes: dict[str, float] = {}
    price_changes: dict[str, float] = {}
    funding_aprs: dict[str, float] = {}
    for i, s in enumerate(symbols):
        if oi_results[i] is not None:
            oi_changes[s] = oi_results[i]
        if fund_results[i] is not None:
            funding_aprs[s] = fund_results[i]
        t = tick_results[i]
        if isinstance(t, dict) and "priceChangePercent" in t:
            try:
                price_changes[s] = float(t["priceChangePercent"])
            except (ValueError, TypeError):
                pass

    metrics = build_metrics(symbols, oi_changes, price_changes, funding_aprs, cfg["weights"])
    if not metrics:
        log.warning("no metrics produced")
        return
    log.info("metrics: %d symbols scored", len(metrics))

    tmp = Path(tempfile.mkdtemp(prefix="zscanner_"))
    scatter_path = tmp / "scatter.png"
    bar_path = tmp / "top.png"
    scatter_oi_vs_price(metrics, scatter_path)
    bar_top_composite(metrics, cfg["top_n_chart"], bar_path)

    top_sorted = sorted(metrics, key=lambda m: m["composite"], reverse=True)
    flagged = [m for m in top_sorted if abs(m["composite"]) >= cfg["z_threshold"]]

    ts = datetime.now(timezone.utc).isoformat()
    title = f"zscanner — {cfg['oi_lookback']} OI window, {len(metrics)} symbols"
    embed = build_embed(title, ts, top_sorted)

    content = f"Flagged (|composite| >= {cfg['z_threshold']:.1f}): {len(flagged)}"
    ok = await post(webhook_url, content, embed, [scatter_path, bar_path])
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
