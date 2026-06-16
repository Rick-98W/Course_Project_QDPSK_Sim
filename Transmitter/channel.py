"""Shared phase rotation and AWGN channel impairments."""

import numpy as np


def apply_phase_rotation(iq, phase_deg):
    """Rotate complex baseband samples by a fixed phase."""
    signal = np.asarray(iq, dtype=np.complex64)
    theta = np.deg2rad(float(phase_deg))
    return (signal * np.exp(1j * theta)).astype(np.complex64)


def awgn_sigma(iq, snr_db):
    """Return complex AWGN sigma for a target SNR in dB."""
    signal = np.asarray(iq, dtype=np.complex64)
    power = float(np.mean(np.abs(signal) ** 2))
    snr_linear = 10.0 ** (float(snr_db) / 10.0)
    noise_power = power / snr_linear
    return float(np.sqrt(noise_power / 2.0))


def add_awgn(iq, snr_db, rng):
    """Add circularly symmetric complex Gaussian noise."""
    signal = np.asarray(iq, dtype=np.complex64)
    sigma = awgn_sigma(signal, snr_db)
    noise = rng.normal(0.0, sigma, size=signal.shape) + 1j * rng.normal(
        0.0, sigma, size=signal.shape
    )
    return (signal + noise.astype(np.complex64)).astype(np.complex64)


def apply_channel(iq, snr_db, phase_deg, rng):
    """Apply phase rotation followed by AWGN."""
    rotated = apply_phase_rotation(iq, phase_deg)
    return add_awgn(rotated, snr_db, rng)


def channel_summary(clean, impaired):
    """Return basic impairment statistics."""
    clean_signal = np.asarray(clean, dtype=np.complex64)
    impaired_signal = np.asarray(impaired, dtype=np.complex64)
    min_size = min(clean_signal.size, impaired_signal.size)
    if min_size == 0:
        return {
            "clean_power": 0.0,
            "impaired_power": 0.0,
            "noise_power": 0.0,
            "estimated_snr_db": float("nan"),
        }

    clean_signal = clean_signal[:min_size]
    impaired_signal = impaired_signal[:min_size]
    noise = impaired_signal - clean_signal
    clean_power = float(np.mean(np.abs(clean_signal) ** 2))
    impaired_power = float(np.mean(np.abs(impaired_signal) ** 2))
    noise_power = float(np.mean(np.abs(noise) ** 2))
    estimated_snr_db = 10.0 * np.log10(clean_power / max(noise_power, np.finfo(float).eps))
    return {
        "clean_power": clean_power,
        "impaired_power": impaired_power,
        "noise_power": noise_power,
        "estimated_snr_db": float(estimated_snr_db),
    }
