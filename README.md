# zscanner

A standalone z-score scanner for Binance USDT-M perpetuals that posts Discord
alerts. No API key required. Single process, asyncio, runs on any VPS.

## What it does

- Fetches open interest, funding rate, and 24h price change for every USDT-M perpetual on Binance Futures.
- Computes cross-sectional z-scores (Bessel-corrected sample std) for OI change, price change, and funding APR, then a weighted composite.
- Posts an embed with the top movers plus two charts (OI-vs-price scatter and top-N composite bars) to a Discord webhook on a fixed interval.

## Install

```
git clone https://github.com/mridlll/zscanner.git
cd zscanner
pip install -r requirements.txt
```

Python 3.11+ required.

## Configure

```
python -m zscanner setup
```

The wizard asks for a Discord webhook, scan interval, OI lookback window,
symbol universe (all perpetuals or top-N by 24h volume), z-score threshold,
chart top-N, and composite weights. It writes `config.json` and `.env`.

## Run

```
python -m zscanner
```

Ctrl-C to stop. Errors inside the loop are logged and the loop continues.

## VPS setup (systemd)

Copy `systemd/zscanner.service`, edit `User`, `WorkingDirectory`,
`EnvironmentFile`, and `ExecStart` to match your install, then:

```
sudo cp systemd/zscanner.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now zscanner
journalctl -u zscanner -f
```

## Tuning

- **Composite weights**: the defaults 0.5 / 0.3 / 0.2 (oi / price / funding)
  emphasize OI breakouts. Bump price weight to catch momentum-led moves.
- **OI lookback**: shorter windows (1h, 2h) react faster but are noisier.
  4h is the default and matches the original monolith's behavior.
- **Scan interval**: too frequent will spam Discord; 15m or 30m is reasonable.
- **Universe**: `all` scans ~400 symbols. `top_volume` with N=100 is faster
  and avoids illiquid noise.

## License

MIT. See `LICENSE`.
