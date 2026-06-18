"""Receiver DSP helpers for capture analysis."""

from __future__ import annotations

import numpy as np


def rrc_filter(beta: float, sps: int, span: int) -> np.ndarray:
    """Create unit-energy root-raised-cosine taps matching the transmitter."""
    if not 0.0 < beta <= 1.0:
        raise ValueError("beta must be in the range (0, 1]")
    if sps < 2:
        raise ValueError("sps must be at least 2")
    if span < 2:
        raise ValueError("span must be at least 2 symbols")

    half = span * sps // 2
    time = np.arange(-half, half + 1, dtype=np.float64) / float(sps)
    taps = np.empty_like(time)

    for index, t_value in enumerate(time):
        if np.isclose(t_value, 0.0):
            taps[index] = 1.0 + beta * (4.0 / np.pi - 1.0)
        elif np.isclose(abs(t_value), 1.0 / (4.0 * beta)):
            taps[index] = (
                beta
                / np.sqrt(2.0)
                * (
                    (1.0 + 2.0 / np.pi) * np.sin(np.pi / (4.0 * beta))
                    + (1.0 - 2.0 / np.pi) * np.cos(np.pi / (4.0 * beta))
                )
            )
        else:
            numerator = (
                np.sin(np.pi * t_value * (1.0 - beta))
                + 4.0 * beta * t_value * np.cos(np.pi * t_value * (1.0 + beta))
            )
            denominator = np.pi * t_value * (1.0 - (4.0 * beta * t_value) ** 2)
            taps[index] = numerator / denominator

    taps /= np.sqrt(np.sum(taps**2))
    return taps.astype(np.float64)


def matched_filter(iq: np.ndarray, taps: np.ndarray) -> np.ndarray:
    """Apply a linear matched filter and return the full convolution."""
    iq_array = np.asarray(iq, dtype=np.complex64)
    tap_array = np.asarray(taps, dtype=np.float64)
    filtered = np.convolve(iq_array, tap_array, mode="full")
    return filtered.astype(np.complex64)


def fixed_symbol_sample(
    iq: np.ndarray,
    sps: int,
    filter_delay_samples: int,
    sample_offset: int = 0,
) -> np.ndarray:
    """Take one sample per symbol using a fixed timing offset."""
    if sps < 1:
        raise ValueError("sps must be positive")
    iq_array = np.asarray(iq, dtype=np.complex64)
    start = int(filter_delay_samples) + int(sample_offset)
    if start < 0:
        raise ValueError("sample start must be non-negative")
    return iq_array[start::sps].copy()


def average_power(samples: np.ndarray) -> float:
    """Return mean power."""
    arr = np.asarray(samples)
    if arr.size == 0:
        return 0.0
    return float(np.mean(np.abs(arr) ** 2))


def constellation_points(samples: np.ndarray, limit: int = 6000) -> np.ndarray:
    """Return up to limit samples for constellation inspection."""
    arr = np.asarray(samples, dtype=np.complex64)
    if arr.size <= int(limit):
        return arr.copy()
    return arr[: int(limit)].copy()
