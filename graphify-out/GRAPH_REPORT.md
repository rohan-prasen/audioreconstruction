# Graph Report - audioreconstruction  (2026-09-12)

## Corpus Check
- Large corpus: 254 files · ~18,827,447 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 575 nodes · 972 edges · 36 communities (25 shown, 4 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 56 edges (avg confidence: 0.89)
- Token cost: 313,855 input · 0 output

## Community Hubs (Navigation)
- Model Core & Config
- CLI Enhance & Setup
- Doc Concepts (Frontend/Model)
- Frontend Dependencies & Config
- CLI Test Suite
- Production Server & Batching
- ONNX Inference Runtime
- Frontend App Logic
- Release Manifest Assets
- Generator U-Net Blocks
- Server Generator Blocks
- Mel-Spectrogram SSIM Metric
- Log-Spectral Distance Metric
- PESQ Metric
- SI-SDR Metric
- SNR Metric
- Backend Inference (dev)
- Discriminator Blocks
- FLAC Similarity Eval
- MP3 Similarity Eval
- Frontend Icon Sprite
- Data Preparation (FFmpeg)
- Modal Deployment App
- Manifest Generator Tool
- Server Model Config
- MCP / shadcn Config
- Brand Mark & Favicon
- Health Check Endpoint
- Audioreconstructor Entry

## God Nodes (most connected - your core abstractions)
1. `ModelConfig` - 25 edges
2. `main()` - 19 edges
3. `CliTests` - 19 edges
4. `setup_assets()` - 17 edges
5. `Generator` - 16 edges
6. `App()` - 15 edges
7. `train_one_epoch()` - 14 edges
8. `CliError` - 13 edges
9. `load_generator()` - 12 edges
10. `run_inference()` - 12 edges

## Surprising Connections (you probably didn't know these)
- `reconstructAll Queue Processor` --semantically_similar_to--> `Setup Download Retry Logic (v1.1.0)`  [INFERRED] [semantically similar]
  frontend/CLAUDE.md → onnx/cli/CHANGELOG.md
- `Server Dependencies (fastapi/torch/modal)` --semantically_similar_to--> `ONNX Inference Dependencies (torch-free)`  [INFERRED] [semantically similar]
  server/requirements.txt → onnx/requirements.txt
- `_reconstruct_sf()` --uses--> `Generator`  [INFERRED]
  backend/main.py → model/generator.py
- `Generator` --uses--> `ModelConfig`  [INFERRED]
  server/model/generator.py → model/config.py
- `model_serve()` --calls--> `copy_metadata()`  [EXTRACTED]
  backend/main.py → model/utils.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **GAN Training Loss Objective** — model_readme_lsgan_loss, model_readme_spectral_loss, model_readme_feature_matching_loss [EXTRACTED 1.00]
- **audioreconstructor CLI Subcommands** — onnx_cli_readme_setup, onnx_cli_readme_enhance, onnx_cli_readme_doctor [EXTRACTED 1.00]
- **Torch-free ONNX Inference Pipeline** — onnx_readme_inference, onnx_readme_model_onnx, onnx_readme_execution_providers, onnx_readme_stdout_contract [INFERRED 0.85]
- **Icons Sprite Symbol Set** — frontend_public_icons_bluesky, frontend_public_icons_discord, frontend_public_icons_documentation, frontend_public_icons_github, frontend_public_icons_social, frontend_public_icons_x [EXTRACTED 1.00]

## Communities (36 total, 4 thin omitted)

### Community 0 - "Model Core & Config"
Cohesion: 0.05
Nodes (67): health_check(), hello(), lifespan(), FastAPI, get, DataLoader, Dataset, GradScaler (+59 more)

### Community 1 - "CLI Enhance & Setup"
Cohesion: 0.07
Nodes (64): doctor(), enhance(), _enhance_folder(), _enhance_single(), command, option, Path, Click command-line interface for audioreconstructor. (+56 more)

### Community 2 - "Doc Concepts (Frontend/Model)"
Cohesion: 0.05
Nodes (48): Frontend AGENTS Guide, Frontend App Component (single React tree), Vite Backend Proxy (/api → backend), POST /model-serve Endpoint, reconstructAll Queue Processor, Frontend State Model (files/jobMap/serverStatus/themeChoice), CSS Custom Properties Styling, Frontend HTML Entry Point (+40 more)

### Community 3 - "Frontend Dependencies & Config"
Cohesion: 0.05
Nodes (42): dependencies, framer-motion, ogl, react, react-dom, tailwindcss, @tailwindcss/vite, devDependencies (+34 more)

### Community 4 - "CLI Test Suite"
Cohesion: 0.07
Nodes (14): group, cli(), Enhance audio with the Audioreconstructor ONNX model., PyPI launcher for the Audioreconstructor native ONNX executable., CliTests, flaky_urlopen(), description(), FakeProcess (+6 more)

### Community 5 - "Production Server & Batching"
Cohesion: 0.08
Nodes (27): inference_mode, limit, Request, _encode_flac(), _get_model_cfg(), health_check(), _ISTFormatter, lifespan() (+19 more)

### Community 6 - "ONNX Inference Runtime"
Cohesion: 0.14
Nodes (25): InferenceSession, Namespace, convert(), copy_metadata(), create_session(), InputReadError, load_audio(), main() (+17 more)

### Community 7 - "Frontend App Logic"
Cohesion: 0.14
Nodes (18): App(), onDragEnter(), onDragLeave(), onDragOver(), onDrop(), prevent(), processOneFile(), reconstructAll() (+10 more)

### Community 8 - "Release Manifest Assets"
Cohesion: 0.12
Nodes (16): bytes, sha256, bytes, sha256, bytes, sha256, files, audioreconstructor-linux-x86_64 (+8 more)

### Community 9 - "Generator U-Net Blocks"
Cohesion: 0.23
Nodes (6): Bottleneck, ConvBlock, DecoderBlock, EncoderBlock, Generator, Tensor

### Community 10 - "Server Generator Blocks"
Cohesion: 0.23
Nodes (5): Bottleneck, ConvBlock, DecoderBlock, EncoderBlock, Tensor

### Community 11 - "Mel-Spectrogram SSIM Metric"
Cohesion: 0.22
Nodes (12): compute_mel_ssim(), load_mono(), main(), argument, command, ndarray, option, Path (+4 more)

### Community 12 - "Log-Spectral Distance Metric"
Cohesion: 0.23
Nodes (11): compute_lsd(), load_mono(), main(), argument, command, option, Path, Tensor (+3 more)

### Community 13 - "PESQ Metric"
Cohesion: 0.25
Nodes (10): compute_pesq(), load_mono(), main(), argument, command, ndarray, option, Path (+2 more)

### Community 14 - "SI-SDR Metric"
Cohesion: 0.25
Nodes (10): compute_si_sdr(), load_mono(), main(), argument, command, ndarray, option, Path (+2 more)

### Community 15 - "SNR Metric"
Cohesion: 0.25
Nodes (10): compute_snr(), load_mono(), main(), argument, command, ndarray, option, Path (+2 more)

### Community 16 - "Backend Inference (dev)"
Cohesion: 0.31
Nodes (9): _load_audio_sf(), model_serve(), device, no_grad, Path, post, Tensor, UploadFile (+1 more)

### Community 17 - "Discriminator Blocks"
Cohesion: 0.33
Nodes (3): DiscriminatorBlock, Tensor, ScaleDiscriminator

### Community 18 - "FLAC Similarity Eval"
Cohesion: 0.50
Nodes (7): align_pair(), compute_snr(), compute_spectrogram_similarity(), load_flac(), main(), ndarray, Path

### Community 19 - "MP3 Similarity Eval"
Cohesion: 0.50
Nodes (7): align_pair(), compute_snr(), compute_spectrogram_similarity(), load_audio(), main(), ndarray, Path

### Community 20 - "Frontend Icon Sprite"
Cohesion: 0.29
Nodes (7): Bluesky Icon, Discord Icon, Documentation Icon, GitHub Icon, Social Icon, Icons SVG Sprite, X (Twitter) Icon

### Community 21 - "Data Preparation (FFmpeg)"
Cohesion: 0.43
Nodes (6): check_ffmpeg(), main(), command, option, Path, transcode_file()

### Community 22 - "Modal Deployment App"
Cohesion: 0.40
Nodes (4): asgi_app, concurrent, function, fastapi_app()

### Community 23 - "Manifest Generator Tool"
Cohesion: 0.50
Nodes (4): describe(), main(), Path, Create the manifest.json required by an Audioreconstructor GitHub Release.

### Community 26 - "Brand Mark & Favicon"
Cohesion: 0.67
Nodes (3): Lightning Bolt Brand Mark, Audio Reconstruction Frontend App, Frontend Favicon Logo

## Knowledge Gaps
- **75 isolated node(s):** `npx`, `name`, `private`, `version`, `type` (+70 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 208 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **4 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ModelConfig` connect `Model Core & Config` to `Generator U-Net Blocks`, `Server Generator Blocks`, `Production Server & Batching`?**
  _High betweenness centrality (0.046) - this node is a cross-community bridge._
- **Why does `Generator` connect `Model Core & Config` to `Backend Inference (dev)`, `Server Generator Blocks`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Why does `load_generator()` connect `Model Core & Config` to `Production Server & Batching`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `ModelConfig` (e.g. with `AudioPairDataset` and `build_splits()`) actually correct?**
  _`ModelConfig` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `main()` (e.g. with `DataConfig` and `ModelConfig`) actually correct?**
  _`main()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `Generator` (e.g. with `_reconstruct_sf()` and `reconstruct()`) actually correct?**
  _`Generator` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `npx`, `name`, `private` to the rest of the system?**
  _75 weakly-connected nodes found - possible documentation gaps or missing edges._