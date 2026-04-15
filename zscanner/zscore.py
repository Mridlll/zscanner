from __future__ import annotations


def sample_zscore(values: list[float]) -> list[float]:
    n = len(values)
    if n < 2:
        return [0.0 for _ in values]
    mean = sum(values) / n
    var = sum((x - mean) ** 2 for x in values) / (n - 1)
    std = var ** 0.5
    if std == 0:
        return [0.0 for _ in values]
    return [(x - mean) / std for x in values]


def _normalize_weights(weights: dict) -> dict:
    total = sum(weights.values())
    if total == 0:
        return {k: 0.0 for k in weights}
    return {k: v / total for k, v in weights.items()}


def build_metrics(
    symbols: list[str],
    oi_changes: dict[str, float],
    price_changes: dict[str, float],
    funding_aprs: dict[str, float],
    weights: dict,
) -> list[dict]:
    w = _normalize_weights({
        "oi": float(weights.get("oi", 0.5)),
        "price": float(weights.get("price", 0.3)),
        "funding": float(weights.get("funding", 0.2)),
    })

    valid = [
        s for s in symbols
        if s in oi_changes and s in price_changes and s in funding_aprs
        and oi_changes[s] is not None
        and price_changes[s] is not None
        and funding_aprs[s] is not None
    ]
    if not valid:
        return []

    oi_vals = [oi_changes[s] for s in valid]
    price_vals = [price_changes[s] for s in valid]
    funding_vals = [funding_aprs[s] for s in valid]

    oi_z = sample_zscore(oi_vals)
    price_z = sample_zscore(price_vals)
    funding_z = sample_zscore(funding_vals)

    out = []
    for i, s in enumerate(valid):
        composite = (
            oi_z[i] * w["oi"]
            + price_z[i] * w["price"]
            + funding_z[i] * w["funding"]
        )
        out.append({
            "symbol": s,
            "oi_z": oi_z[i],
            "price_z": price_z[i],
            "funding_z": funding_z[i],
            "composite": composite,
        })
    return out
