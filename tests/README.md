# Usage

This  directory only contains one file `test.py` which is just a comparison script that will give us how identical are the reconstructed and actual FLAC audios are. 

The command to use this script is as follows:

> Assuming that you have created a virtual environment and have all the dependecies installed and setup. If not reach out to [README](../README.md)

```bash
uv run python -m tests.test "path to the original FLAC" "path to the reconstructed FLAC"
```

## Sample Output

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
