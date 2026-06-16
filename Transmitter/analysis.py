"""Numerical analysis helpers for transmitter-side plots."""

import numpy as np


def compute_eye_traces(waveform, sps, traces=120, span_symbols=2, start=None):
    """Slice a complex baseband waveform into eye-diagram traces.

    The real component is used because the transmitter-side eye diagram is
    intended to show pulse shaping and ISI behavior in one baseband dimension.
    """
    signal = np.asarray(waveform)
    if signal.ndim != 1:
        raise ValueError("waveform must be a one-dimensional array")
    if sps < 2:
        raise ValueError("sps must be at least 2")
    if traces < 1:
        raise ValueError("traces must be positive")
    if span_symbols < 1:
        raise ValueError("span_symbols must be positive")

    span_samples = int(span_symbols * sps)
    if start is None:
        start = span_samples * 2

    available = max(0, (signal.size - start - span_samples) // sps)
    count = min(int(traces), available)
    if count <= 0:
        return np.empty((0, span_samples), dtype=np.float64)

    output = np.empty((count, span_samples), dtype=np.float64)
    real_signal = signal.real.astype(np.float64, copy=False)
    for row in range(count):
        offset = start + row * sps
        output[row] = real_signal[offset : offset + span_samples]
    return output


def sample_constellation(symbols, max_points=6000):
    """Return a deterministic subset of constellation symbols for plotting."""
    symbol_array = np.asarray(symbols, dtype=np.complex64)
    if symbol_array.ndim != 1:
        raise ValueError("symbols must be a one-dimensional array")
    if symbol_array.size <= max_points:
        return symbol_array
    indices = np.linspace(0, symbol_array.size - 1, int(max_points), dtype=np.int64)
    return symbol_array[indices]


def compute_psd(waveform, sample_rate, nfft=4096):
    """Compute a normalized baseband PSD estimate in dB."""
    signal = np.asarray(waveform, dtype=np.complex64)
    if signal.ndim != 1:
        raise ValueError("waveform must be a one-dimensional array")
    if signal.size == 0:
        return np.array([], dtype=np.float64), np.array([], dtype=np.float64)
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if nfft < 16:
        raise ValueError("nfft must be at least 16")

    count = min(int(nfft), signal.size)
    segment = signal[:count].astype(np.complex128)
    window = np.hanning(count)
    spectrum = np.fft.fftshift(np.fft.fft(segment * window, n=int(nfft)))
    power = np.abs(spectrum) ** 2
    power /= max(np.sum(window**2), np.finfo(np.float64).eps)
    power_db = 10.0 * np.log10(power + np.finfo(np.float64).eps)
    power_db -= np.max(power_db)
    freqs = np.fft.fftshift(np.fft.fftfreq(int(nfft), d=1.0 / sample_rate))
    return freqs.astype(np.float64), power_db.astype(np.float64)
