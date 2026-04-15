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


def build_embed(title: str, timestamp_iso: str, top_metrics: list[dict]) -> dict:
    fields = []
    for m in top_metrics[:3]:
        sym = m["symbol"]
        val = (
            f"composite: {m['composite']:+.2f}\n"
            f"oi_z: {m['oi_z']:+.2f}\n"
            f"price_z: {m['price_z']:+.2f}\n"
            f"funding_z: {m['funding_z']:+.2f}"
        )
        fields.append({"name": sym, "value": val, "inline": True})
    return {
        "title": title,
        "timestamp": timestamp_iso,
        "color": EMBED_COLOR,
        "fields": fields,
    }
