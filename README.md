# zscanner

A standalone z-score scanner for Binance USDT-M perpetuals that posts Discord
alerts. No API key required. Single process, asyncio, runs on any VPS.

## What it does

- Fetches open interest (three fixed windows: 30m, 1h, 4h), funding rate, 24h
  price change, 24h quote volume, and spot/futures basis for every USDT-M
  perpetual on Binance Futures.
- Computes cross-sectional z-scores (Bessel-corrected sample std) for each
  signal. The OI component of the composite is the average of the three
  timeframe z-scores, so it catches both budding 30m moves and sustained 4h
  moves in one pass.
- Composite is a weighted average over whatever components a symbol has.
  Defaults: `oi 0.4 / price 0.2 / funding 0.2 / volume 0.1 / basis 0.1`.
  Symbols with no spot pair (perp-only listings) just skip the basis component
  and weights renormalize.
- Posts an embed with the top movers plus three charts (OI-avg vs price
  scatter, top-N composite bars, top-N 30m OI bars for early movers) to a
  Discord webhook on a fixed interval.
- In-memory per-symbol cooldown (default 240 min) suppresses repeat flags on
  the same symbol. The cooldown state is held in process memory only and
  resets on restart. Symbols still appear in the embed and charts regardless.

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

The wizard asks for a Discord webhook, scan interval, symbol universe (all
perpetuals or top-N by 24h volume), z-score threshold, chart top-N, cooldown
minutes, and the five composite weights. It writes `config.json` and `.env`.

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

- **Composite weights**: defaults emphasize OI. Bump `price` or `volume` for
  momentum-led catches, `basis` for futures premium dislocations.
- **Scan interval**: too frequent will spam Discord; 15m or 30m is reasonable.
- **Cooldown**: 240 min by default. Lower for more alerts, higher for less
  noise. Not persisted across restarts.
- **Universe**: `all` scans ~400 symbols. `top_volume` with N=100 is faster
  and avoids illiquid noise.

## License

MIT. See `LICENSE`.
