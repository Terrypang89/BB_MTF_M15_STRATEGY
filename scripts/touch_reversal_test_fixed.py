def baseline_reversion_rate(d: dict, target: float) -> bool:
    """Baseline: directional reversion rate — only count if price reaches midline
    in the direction implied by its starting position relative to midline.
    (close < midline => expect UP; close > midline => expect DOWN)."""
    # Determine expected direction from starting position
    if d["close"] is None:
        return False
    if d["close"] < target:  # below midline, expect to rise
        for _ in range(HORIZON_BARS):
            if d["close"] >= target:
                return True
    elif d["close"] > target:  # above midline, expect to fall
        for _ in range(HORIZON_BARS):
            if d["close"] <= target:
                return True
    return False
