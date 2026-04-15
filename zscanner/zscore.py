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


def _cross_section_z(values_by_symbol: dict[str, float]) -> dict[str, float]:
    syms = [s for s, v in values_by_symbol.items() if v is not None]
    vals = [values_by_symbol[s] for s in syms]
    zs = sample_zscore(vals)
    return {s: z for s, z in zip(syms, zs)}


def build_metrics(
    symbols: list[str],
    oi_changes_by_window: dict[str, dict[str, float]],
    price_changes: dict[str, float],
    funding_aprs: dict[str, float],
    volumes: dict[str, float],
    basis_pcts: dict[str, float],
    weights: dict,
) -> list[dict]:
    w = _normalize_weights({
        "oi": float(weights.get("oi", 0.4)),
        "price": float(weights.get("price", 0.2)),
        "funding": float(weights.get("funding", 0.2)),
        "volume": float(weights.get("volume", 0.1)),
        "basis": float(weights.get("basis", 0.1)),
    })

    windows = ["30m", "1h", "4h"]
    oi_z_by_window: dict[str, dict[str, float]] = {}
    for win in windows:
        raw = oi_changes_by_window.get(win, {})
        oi_z_by_window[win] = _cross_section_z(raw)

    price_z_map = _cross_section_z(price_changes)
    funding_z_map = _cross_section_z(funding_aprs)
    volume_z_map = _cross_section_z(volumes)
    basis_z_map = _cross_section_z(basis_pcts)

    out = []
    for s in symbols:
        oi_zs_present = [oi_z_by_window[win].get(s) for win in windows]
        oi_zs_present = [z for z in oi_zs_present if z is not None]
        if not oi_zs_present:
            continue
        oi_z_30m = oi_z_by_window["30m"].get(s)
        oi_z_1h = oi_z_by_window["1h"].get(s)
        oi_z_4h = oi_z_by_window["4h"].get(s)
        oi_avg = sum(oi_zs_present) / len(oi_zs_present)

        price_z = price_z_map.get(s)
        funding_z = funding_z_map.get(s)
        volume_z = volume_z_map.get(s)
        basis_z = basis_z_map.get(s)

        if price_z is None or funding_z is None or volume_z is None:
            continue

        components = {
            "oi": oi_avg,
            "price": price_z,
            "funding": funding_z,
            "volume": volume_z,
        }
        if basis_z is not None:
            components["basis"] = basis_z

        present_w = {k: w[k] for k in components}
        present_w = _normalize_weights(present_w)
        composite = sum(components[k] * present_w[k] for k in components)

        out.append({
            "symbol": s,
            "oi_z_30m": oi_z_30m,
            "oi_z_1h": oi_z_1h,
            "oi_z_4h": oi_z_4h,
            "oi_z_avg": oi_avg,
            "price_z": price_z,
            "funding_z": funding_z,
            "volume_z": volume_z,
            "basis_z": basis_z,
            "composite": composite,
        })
    return out
