# zscanner

A standalone z-score scanner for Binance USDT-M perpetuals that posts Discord
alerts. No exchange API key required. Single process, asyncio, runs on any VPS.

## What it does

- Fetches open interest (three fixed windows: **30m, 1h, 4h**), funding rate,
  24h price change, 24h quote volume, and spot/futures basis for every USDT-M
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
- In-memory per-symbol cooldown (default 240 min) suppresses repeat flags.
  Resets on restart. Symbols still appear in the embed and charts regardless.

## Requirements

- Python 3.11 or newer
- A Discord webhook URL (see below — takes 30 seconds to create)
- Outbound HTTPS to `fapi.binance.com`, `api.binance.com`, and `discord.com`

## 1. Create a Discord webhook

In Discord:

1. Open the server and channel where you want alerts to land.
2. Channel settings → **Integrations** → **Webhooks** → **New Webhook**.
3. Name it (e.g. `zscanner`), copy the **Webhook URL**, save.

You'll paste this URL into the setup wizard in step 3.

## 2. Install (local or VPS)

```bash
git clone https://github.com/Mridlll/zscanner.git
cd zscanner
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

On a fresh Ubuntu/Debian VPS, install Python first:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

## 3. Configure

```bash
python -m zscanner setup
```

The wizard asks for:

- **Discord webhook URL** — paste from step 1
- **Scan interval** — `5m`, `15m`, `30m`, `1h`, or custom minutes
- **Symbol universe** — `all` (~500 perps) or `top_volume` (top N by 24h
  quote volume; default N=100, faster, less illiquid noise)
- **Z-score threshold** — `|composite|` to flag a symbol (default `2.0`)
- **Top N for charts** — bars displayed in the chart (default `15`)
- **Cooldown minutes** — minimum gap between flags for the same symbol
  (default `240`, in-memory)
- **Composite weights** — five values for `oi / price / funding / volume /
  basis` (defaults `0.4 / 0.2 / 0.2 / 0.1 / 0.1`, normalized on save)

The wizard writes `config.json` (gitignored) and `.env` (gitignored). Re-run
the wizard any time to change settings; current values appear as `[bracket]`
defaults.

## 4. Run

```bash
python -m zscanner
```

You should see logs like:

```
2026-04-16 01:16:44 INFO universe: 100 symbols
2026-04-16 01:16:54 INFO metrics: 100 symbols scored
2026-04-16 01:16:57 INFO posted to discord: True
```

Then a Discord message in your channel with three charts and a top-symbol
embed. Ctrl-C to stop. Any per-cycle exception is logged and the loop
continues — it will not crash on a transient Binance or Discord error.

## 5. Run as a service (systemd)

For unattended operation on a Linux VPS:

```bash
sudo tee /etc/systemd/system/zscanner.service > /dev/null <<'EOF'
[Unit]
Description=zscanner — cross-sectional z-score scanner for Binance perpetuals
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/home/YOUR_USER/zscanner
EnvironmentFile=/home/YOUR_USER/zscanner/.env
ExecStart=/home/YOUR_USER/zscanner/.venv/bin/python -m zscanner
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now zscanner
sudo systemctl status zscanner
journalctl -u zscanner -f
```

Replace `YOUR_USER` with your actual Linux username. A template lives at
`systemd/zscanner.service`.

## Updating

```bash
cd zscanner
git pull
source .venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart zscanner       # if running as a service
```

Your `config.json` and `.env` are gitignored and will not be overwritten.

## Tuning

- **Composite weights**: defaults emphasize OI. Bump `price` or `volume` for
  momentum-led catches, `basis` for futures-premium dislocations, `funding`
  for crowded-positioning catches.
- **Scan interval**: 30m is the recommended default. 15m doubles cost; 5m is
  noisy and may rate-limit on very large universes.
- **Cooldown**: 240 min default. Lower for more alerts, higher for less
  noise. Not persisted across restarts.
- **Universe**: `all` scans every USDT-M perp (~500 symbols). `top_volume`
  with N=100 is faster and skips illiquid coins.

## Troubleshooting

- **`Run python -m zscanner setup first`** — no `config.json` in the working
  directory. Run the wizard.
- **`DISCORD_WEBHOOK_URL not set`** — `.env` is missing or empty. Re-run the
  wizard or paste the line into `.env` manually:
  `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`
- **`posted to discord: False`** — webhook is invalid, deleted, or
  rate-limited. Recreate it in Discord and re-run setup.
- **`no symbols returned`** — Binance fAPI is unreachable from your VPS.
  Check `curl https://fapi.binance.com/fapi/v1/exchangeInfo`. Some hosting
  regions block Binance; use a different provider or region.
- **Matplotlib font warnings** — cosmetic only, charts still render. If a
  Chinese-named coin label looks like boxes, install a CJK font:
  `sudo apt install -y fonts-noto-cjk`.
- **Cooldown not respected after restart** — by design, cooldown is
  in-memory.

## License

MIT. See `LICENSE`.
