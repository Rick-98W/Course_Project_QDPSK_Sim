# Transmitter Demo Limits

The transmitter UI and backend API both clamp the demonstration parameters:

```text
SNR:   6.0 .. 30.0 dB
Phase: -90 .. +90 deg
```

Reasoning:

- `6 dB` is already a harsh channel for this image-link demo.
- More aggressive SNR settings often damage the image header instead of producing useful visual degradation.
- The wider phase range is intentional: QPSK depends on absolute phase and can fail past roughly `45 deg`, while QDPSK cancels a common fixed phase rotation through differential detection.
- Recommended phase demo settings are high SNR (`25..30 dB`) with `0 deg`, `50 deg`, and `75 deg`.

Receiver analysis remains lenient: if the recovered `IMG0` header is damaged, it still forces a fixed `64x64x3` RGB output so degraded images can be compared visually.

Current image-size policy:

- The demo source remains fixed to `raw_pic_64.png`.
- Supported payload is fixed `64x64 RGB`.
- Arbitrary image dimensions are not supported by the current end-to-end demo.
