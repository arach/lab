# Recommended Open Models

Current shortlist for the Talkie local-intelligence eval pack on this machine:

1. `mlx-community/NVIDIA-Nemotron-3-Nano-4B-4bit`
   - Plain `mlx-lm` model
   - Good fit for structured JSON tasks without pushing memory too hard
2. `mlx-community/gemma-4-e4b-it-mxfp8`
   - Runs through `mlx-vlm`
   - Stronger modern general-purpose open model, but heavier than the Nemotron 4B path
3. `mlx-community/Qwen3.5-2B-4bit`
   - Existing local baseline already partly in cache
   - Useful as the control model for before/after comparisons

Suggested first pass:
- `Nemotron 4B` on all 24 cards
- `Gemma 4 E4B` on all 24 cards
- `Qwen3.5 2B` as baseline
