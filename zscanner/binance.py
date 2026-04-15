from __future__ import annotations

import asyncio
import aiohttp

BASE = "https://fapi.binance.com"

PERIOD_TO_MINUTES = {
    "5m": 5, "15m": 15, "30m": 30, "1h": 60,
    "2h": 120, "4h": 240, "6h": 360, "12h": 720, "1d": 1440,
}


class BinanceFutures:
    def __init__(self, concurrency: int = 10, timeout: float = 10.0):
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._sem = asyncio.Semaphore(concurrency)
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session:
            await self._session.close()

    async def _get(self, path: str, params: dict | None = None):
        assert self._session is not None
        url = f"{BASE}{path}"
        for attempt in range(2):
            try:
                async with self._sem:
                    async with self._session.get(url, params=params) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        if resp.status in (429, 500, 502, 503, 504):
                            if attempt == 0:
                                await asyncio.sleep(2.0)
                                continue
                        return None
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == 0:
                    await asyncio.sleep(2.0)
                    continue
                return None
        return None

    async def list_perpetuals(self) -> list[str]:
        data = await self._get("/fapi/v1/exchangeInfo")
        if not data:
            return []
        out = []
        for s in data.get("symbols", []):
            if (
                s.get("contractType") == "PERPETUAL"
                and s.get("status") == "TRADING"
                and s.get("quoteAsset") == "USDT"
            ):
                out.append(s["symbol"])
        return out

    async def oi_window_pct(self, symbol: str, period: str, lookback_bars: int) -> float | None:
        limit = max(2, min(500, lookback_bars + 1))
        data = await self._get(
            "/futures/data/openInterestHist",
            {"symbol": symbol, "period": period, "limit": limit},
        )
        if not data or len(data) < 2:
            return None
        try:
            first = float(data[0]["sumOpenInterest"])
            last = float(data[-1]["sumOpenInterest"])
        except (KeyError, ValueError, TypeError):
            return None
        if first == 0:
            return None
        return (last - first) / first * 100.0

    async def funding_apr(self, symbol: str) -> float | None:
        data = await self._get("/fapi/v1/premiumIndex", {"symbol": symbol})
        if not data:
            return None
        try:
            rate = float(data["lastFundingRate"])
        except (KeyError, ValueError, TypeError):
            return None
        return rate * 3 * 365 * 100.0

    async def ticker_24h(self, symbol: str | None = None) -> dict | list | None:
        params = {"symbol": symbol} if symbol else None
        return await self._get("/fapi/v1/ticker/24hr", params)
