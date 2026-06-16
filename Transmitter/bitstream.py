"""Byte/bit conversion helpers for the transmitter chain."""

import numpy as np


def bytes_to_bits(data):
    """Convert bytes to a big-endian uint8 bit array."""
    byte_array = np.frombuffer(data, dtype=np.uint8)
    return np.unpackbits(byte_array, bitorder="big")


def bits_to_bytes(bits):
    """Pack a uint8 bit array back into bytes, padding the tail with zeros."""
    bit_array = np.asarray(bits, dtype=np.uint8)
    if bit_array.ndim != 1:
        raise ValueError("bits must be a one-dimensional array")
    if bit_array.size == 0:
        return b""
    if np.any((bit_array != 0) & (bit_array != 1)):
        raise ValueError("bits must contain only 0 and 1")

    remainder = bit_array.size % 8
    if remainder:
        pad = np.zeros(8 - remainder, dtype=np.uint8)
        bit_array = np.concatenate([bit_array, pad])
    return np.packbits(bit_array, bitorder="big").tobytes()
