# Test — Audio Similarity Evaluation

Scripts for comparing audio signal similarity between file pairs. Useful for evaluating reconstruction quality against original lossless sources.

> Requires all Python dependencies installed. See the [root README](../README.md) for setup.

## FLAC-to-FLAC Comparison

Compare an original FLAC against a reconstructed FLAC:

```bash
uv run python -m test.eval_FLAC "path/to/original.flac" "path/to/reconstructed.flac"
```

### Sample Output

```
                  Comparison Results
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Metric                 ┃    Value ┃ Interpretation ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ SNR                    │ 12.29 dB │ Moderate       │
│ Spectrogram Similarity │   99.68% │ Near-identical │
│ Duration               │   203.8s │ 2ch @ 44100 Hz │
└────────────────────────┴──────────┴────────────────┘
```

## FLAC-to-MP3 Comparison

Compare a FLAC reference against an MP3 (measures compression loss):

```bash
uv run python -m test.eval_mp3 "path/to/reference.flac" "path/to/compressed.mp3"
```

## Metrics

| Metric | What it measures |
|--------|-----------------|
| SNR | Signal-to-noise ratio in dB |
| Spectrogram Similarity | Frequency-domain similarity (%) |
