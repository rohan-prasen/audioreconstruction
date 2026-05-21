# Usage

This directory contains python scripts to test the similarity between audio signals of two files of any kind one for FLAC and one for FLAC and mp3.

## FLAC-to-FLAC comparison

The command to use this script is as follows:

> Assuming that you have created a virtual environment and have all the dependecies installed and setup. If not reach out to [README](../README.md)

```bash
uv run python -m test.eval_FLAC "path to the original FLAC" "path to the reconstructed FLAC"
```

### Sample Output

```markdown
                  Comparison Results
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Metric                 ┃    Value ┃ Interpretation ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ SNR                    │ 12.29 dB │ Moderate       │
│ Spectrogram Similarity │   99.68% │ Near-identical │
│ Duration               │   203.8s │ 2ch @ 44100 Hz │
└────────────────────────┴──────────┴────────────────┘
```

## FLAC-to-MP3

```bash
uv run python -m test.eval_mp3 "path to FLAC file" "path to the mp3 file"
```

### Sample Output

```markdown

```
