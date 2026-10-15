"""Shared number and time formatting for the report and the dashboard."""

from __future__ import annotations


def commas(value: float) -> str:
    return f"{int(round(value)):,}"


def pct(value: float, digits: int = 1) -> str:
    scaled = value * 100
    rounded = round(scaled, digits)
    if rounded == 0 and scaled != 0:
        return f"{scaled:.2f}%" if abs(scaled) >= 0.01 else f"{scaled:.4f}%"
    nearest = round(rounded)
    if abs(rounded - nearest) <= 1e-9:
        return f"{nearest:.0f}%"
    return f"{rounded:.{digits}f}%"


def money(value: float) -> str:
    if abs(value - round(value)) < 0.005:
        return f"${value:,.0f}"
    return f"${value:,.2f}"


def mph(value: float) -> str:
    return f"{value:.1f} mph"


def miles(value: float) -> str:
    return f"{value:.1f} mi"


def hour_label(hour: int) -> str:
    hour = int(hour)
    if hour == 0:
        return "12 a.m."
    if hour < 12:
        return f"{hour} a.m."
    if hour == 12:
        return "12 p.m."
    return f"{hour - 12} p.m."


def ratio(value: float) -> str:
    return f"{value:.2f}×"
