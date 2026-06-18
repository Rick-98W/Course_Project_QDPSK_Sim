"""QPSK/QDPSK symbol mapping and RRC pulse shaping."""

import numpy as np


SQRT2 = np.sqrt(2.0)

# Gray QPSK mapping:
# 00 ->  1 + 1j
# 01 -> -1 + 1j
# 11 -> -1 - 1j
# 10 ->  1 - 1j
_PHASE_TO_SYMBOL = np.array(
    [
        (1.0 + 1.0j) / SQRT2,
        (-1.0 + 1.0j) / SQRT2,
        (-1.0 - 1.0j) / SQRT2,
        (1.0 - 1.0j) / SQRT2,
    ],
    dtype=np.complex64,
)


def bits_to_dibits(bits):
    """Convert a one-dimensional bit array to dibit phase indices 0..3."""
    bit_array = np.asarray(bits, dtype=np.uint8)
    if bit_array.ndim != 1:
        raise ValueError("bits must be a one-dimensional array")
    if np.any((bit_array != 0) & (bit_array != 1)):
        raise ValueError("bits must contain only 0 and 1")
    if bit_array.size % 2:
        bit_array = np.concatenate([bit_array, np.zeros(1, dtype=np.uint8)])

    pairs = bit_array.reshape(-1, 2)
    return ((pairs[:, 0] << 1) | pairs[:, 1]).astype(np.uint8)


def qpsk_modulate(bits):
    """Map bits directly to Gray-coded QPSK symbols."""
    phase_indices = bits_to_dibits(bits)
    return _PHASE_TO_SYMBOL[phase_indices]


def differential_encode(phase_steps, initial_phase=0):
    """Accumulate QDPSK phase steps modulo 4."""
    steps = np.asarray(phase_steps, dtype=np.uint8)
    if steps.ndim != 1:
        raise ValueError("phase_steps must be a one-dimensional array")
    if np.any(steps > 3):
        raise ValueError("phase_steps must be in the range 0..3")

    accumulated = (np.cumsum(steps, dtype=np.int64) + int(initial_phase)) % 4
    return accumulated.astype(np.uint8)


def qdpsk_modulate(bits, initial_phase=0):
    """Differentially encode dibits and map them to QPSK constellation points."""
    phase_steps = bits_to_dibits(bits)
    phase_indices = differential_encode(phase_steps, initial_phase=initial_phase)
    return _PHASE_TO_SYMBOL[phase_indices]


def average_power(symbols):
    """Return mean symbol power."""
    symbol_array = np.asarray(symbols)
    if symbol_array.size == 0:
        return 0.0
    return float(np.mean(np.abs(symbol_array) ** 2))


def unique_constellation_points(symbols):
    """Return unique ideal constellation points used by a symbol sequence."""
    symbol_array = np.asarray(symbols)
    if symbol_array.size == 0:
        return np.array([], dtype=np.complex64)
    rounded = np.round(symbol_array.real, 6) + 1j * np.round(symbol_array.imag, 6)
    return np.unique(rounded.astype(np.complex64))


def rrc_filter(beta, sps, span):
    """Create unit-energy root-raised-cosine taps.

    ``span`` is measured in symbols and the returned tap count is
    ``span * sps + 1``.
    """
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
                + 4.0
                * beta
                * t_value
                * np.cos(np.pi * t_value * (1.0 + beta))
            )
            denominator = np.pi * t_value * (1.0 - (4.0 * beta * t_value) ** 2)
            taps[index] = numerator / denominator

    taps /= np.sqrt(np.sum(taps**2))
    return taps.astype(np.float64)


def upsample_symbols(symbols, sps):
    """Insert sps-1 zeros between symbols."""
    symbol_array = np.asarray(symbols, dtype=np.complex64)
    if symbol_array.ndim != 1:
        raise ValueError("symbols must be a one-dimensional array")
    if sps < 2:
        raise ValueError("sps must be at least 2")

    upsampled = np.zeros(symbol_array.size * sps, dtype=np.complex64)
    upsampled[::sps] = symbol_array
    return upsampled


def pulse_shape(symbols, taps, sps):
    """Upsample symbols and convolve them with RRC taps."""
    upsampled = upsample_symbols(symbols, sps)
    shaped = np.convolve(upsampled, np.asarray(taps, dtype=np.float64), mode="full")
    return shaped.astype(np.complex64)


def filter_delay_samples(taps):
    """Return the group delay in samples for an odd-length FIR filter."""
    tap_count = np.asarray(taps).size
    return (tap_count - 1) // 2
