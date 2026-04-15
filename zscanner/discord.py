from __future__ import annotations

import json
from pathlib import Path
import aiohttp

EMBED_COLOR = 0x1F4E79


async def post(
    webhook_url: str,
    content: str,
    embed: dict,
    file_paths: list[str | Path],
) -> bool:
    form = aiohttp.FormData()
    payload = {"content": content, "embeds": [embed]}
    form.add_field("payload_json", json.dumps(payload), content_type="application/json")

    handles = []
    try:
        for i, p in enumerate(file_paths):
            p = Path(p)
            fh = open(p, "rb")
            handles.append(fh)
            form.add_field(
                f"files[{i}]",
                fh,
                filename=p.name,
                content_type="image/png",
            )
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, data=form) as resp:
                return resp.status in (200, 204)
    finally:
        for fh in handles:
            try:
                fh.close()
            except Exception:
                pass


def _fmt(v) -> str:
    if v is None:
        return "—"
    return f"{v:+.2f}"


def build_embed(title: str, timestamp_iso: str, top_metrics: list[dict]) -> dict:
    fields = []
    for m in top_metrics[:3]:
        sym = m["symbol"]
        line1 = (
            f"composite {_fmt(m['composite'])}  \u2022  "
            f"OI 30m {_fmt(m.get('oi_z_30m'))} / 1h {_fmt(m.get('oi_z_1h'))} / 4h {_fmt(m.get('oi_z_4h'))}"
        )
        line2 = (
            f"price {_fmt(m.get('price_z'))}  \u2022  "
            f"vol {_fmt(m.get('volume_z'))}  \u2022  "
            f"funding {_fmt(m.get('funding_z'))}  \u2022  "
            f"basis {_fmt(m.get('basis_z'))}"
        )
        fields.append({"name": sym, "value": f"{line1}\n{line2}", "inline": False})
    return {
        "title": title,
        "timestamp": timestamp_iso,
        "color": EMBED_COLOR,
        "fields": fields,
    }
