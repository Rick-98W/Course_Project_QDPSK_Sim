"""Hard-decision demodulation for QPSK and QDPSK."""

from __future__ import annotations

import numpy as np

from core.packet import CHANNEL_QDPSK, CHANNEL_QPSK


# This mirrors the transmitter's actual _PHASE_TO_SYMBOL array index order.
# The transmitter comment calls it Gray mapping, but bits_to_dibits indexes the
# array directly, so index 2 is dibit 10 and index 3 is dibit 11.
_CONSTELLATION_TO_BITS = {
    (1, 1): (0, 0),
    (-1, 1): (0, 1),
    (-1, -1): (1, 0),
    (1, -1): (1, 1),
}

_STEP_TO_BITS = {
    0: (0, 0),
    1: (0, 1),
    2: (1, 0),
    3: (1, 1),
}


def hard_decide_qpsk(symbols: np.ndarray) -> np.ndarray:
    """Convert QPSK symbols to bits using the transmitter's Gray mapping."""
    arr = np.asarray(symbols, dtype=np.complex64)
    if arr.ndim != 1:
        raise ValueError("symbols must be one-dimensional")
    real = np.where(arr.real >= 0.0, 1, -1)
    imag = np.where(arr.imag >= 0.0, 1, -1)
    bits = np.empty(arr.size * 2, dtype=np.uint8)
    for index, (r_val, i_val) in enumerate(zip(real, imag)):
        first, second = _CONSTELLATION_TO_BITS[(int(r_val), int(i_val))]
        bits[2 * index] = first
        bits[2 * index + 1] = second
    return bits


def hard_decide_qdpsk(symbols: np.ndarray) -> np.ndarray:
    """Differentially decode QDPSK symbols back to dibits, then bits."""
    arr = np.asarray(symbols, dtype=np.complex64)
    if arr.ndim != 1:
        raise ValueError("symbols must be one-dimensional")
    if arr.size == 0:
        return np.array([], dtype=np.uint8)

    bits = np.empty(arr.size * 2, dtype=np.uint8)

    first_real = 1 if arr[0].real >= 0.0 else -1
    first_imag = 1 if arr[0].imag >= 0.0 else -1
    first_bits = _CONSTELLATION_TO_BITS[(first_real, first_imag)]
    bits[0] = first_bits[0]
    bits[1] = first_bits[1]

    if arr.size == 1:
        return bits

    differential = arr[1:] * np.conjugate(arr[:-1])
    bits = np.empty(arr.size * 2, dtype=np.uint8)
    bits[0] = first_bits[0]
    bits[1] = first_bits[1]

    steps = _hard_decide_phase_steps(differential)
    for index, step in enumerate(steps, start=1):
        first, second = _STEP_TO_BITS[int(step)]
        bits[2 * index] = first
        bits[2 * index + 1] = second
    return bits


def _hard_decide_phase_steps(values: np.ndarray) -> np.ndarray:
    """Decide differential phase steps nearest to 0, +90, 180, or -90 deg."""
    arr = np.asarray(values, dtype=np.complex64)
    steps = np.empty(arr.size, dtype=np.uint8)
    abs_real = np.abs(arr.real)
    abs_imag = np.abs(arr.imag)

    horizontal = abs_real >= abs_imag
    steps[horizontal & (arr.real >= 0.0)] = 0
    steps[~horizontal & (arr.imag >= 0.0)] = 1
    steps[horizontal & (arr.real < 0.0)] = 2
    steps[~horizontal & (arr.imag < 0.0)] = 3
    return steps


def demodulate_symbols(symbols: np.ndarray, channel_id: int) -> np.ndarray:
    """Dispatch to the correct hard-decision demodulator."""
    if channel_id == CHANNEL_QPSK:
        return hard_decide_qpsk(symbols)
    if channel_id == CHANNEL_QDPSK:
        return hard_decide_qdpsk(symbols)
    raise ValueError("unsupported channel_id %r" % (channel_id,))


def bits_to_bytes(bits: np.ndarray) -> bytes:
    """Pack a 0/1 bit array into bytes using big-endian bit order."""
    bit_array = np.asarray(bits, dtype=np.uint8)
    if bit_array.ndim != 1:
        raise ValueError("bits must be one-dimensional")
    if bit_array.size == 0:
        return b""
    remainder = bit_array.size % 8
    if remainder:
        pad = np.zeros(8 - remainder, dtype=np.uint8)
        bit_array = np.concatenate([bit_array, pad])
    return np.packbits(bit_array, bitorder="big").tobytes()
