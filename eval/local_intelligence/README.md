# Local Intelligence Eval Harness

Canonical home for the reconstructed Use Talkie local-intelligence eval pack.

What lives here:
- `cards.json`: 24 machine-graded Talkie workflow tasks
- `run_eval.py`: provider-agnostic runner
- `run_hf_transformers.py`: Hugging Face compute runner using `transformers`
- `run_hf_matrix.py`: batch runner for the recommended HF model matrix
- `launch_hf_job.py`: Hugging Face Jobs launcher for non-notebook cloud runs
- `Dockerfile`: custom dependency image for repeat HF Jobs runs
- `job-requirements.txt`: pinned runtime deps baked into the custom image
- `build_image.sh`: local helper to build the custom image
- `.github/workflows/build-local-intelligence-image.yml`: GitHub Actions workflow that publishes the image to GHCR
- `sync_to_hf.py`: uploads just this eval harness to a Hugging Face repo
- `upload_results.py`: uploads result JSON files back to the HF repo
- `grader.py`: assertion-based JSON grader
- `template.py`: prompt rendering helpers
- `providers/`: Apple, MLX, Ollama, and Hugging Face adapters
- `push_to_hf.py`: export pack for notebook or dataset use
- `hf_compute_quickstart.md`: copy-paste guide for HF Pro compute
- `notebook.ipynb`: optional notebook entrypoint

Quick examples:

```bash
python3 eval/local_intelligence/run_eval.py \
  --provider replay \
  --replay-file /tmp/local-intelligence-replay.jsonl \
  --limit 1 \
  --verbose

python3 eval/local_intelligence/launch_hf_job.py \
  --sync-code \
  --image pytorch/pytorch:2.6.0-cuda12.4-cudnn9-devel \
  --flavor a10g-small \
  --timeout 2h \
  --limit 24
```

## Hugging Face Compute

Run a single model on HF compute:

```bash
python3 eval/local_intelligence/run_hf_transformers.py \
  --model google/gemma-4-E4B-it \
  --limit 24 \
  --verbose
```

The HF compute runners record poor benchmark scores without failing the whole job.
Use `--fail-on-incomplete` only when you explicitly want non-passing evals to exit nonzero.

## Custom Image

Build a reusable Jobs image that already contains the runtime dependencies:

```bash
chmod +x eval/local_intelligence/build_image.sh
eval/local_intelligence/build_image.sh arach/local-intelligence-eval:latest
docker push arach/local-intelligence-eval:latest
```

Or publish it from GitHub Actions to GHCR:

```text
ghcr.io/<your-github-owner>/training-lab-local-intelligence-eval:latest
```

The workflow lives at:
- [.github/workflows/build-local-intelligence-image.yml](/Users/arach/dev/training-lab/.github/workflows/build-local-intelligence-image.yml)

It publishes on:
- manual `workflow_dispatch`
- pushes to `main` when the image files change

Then launch Jobs with that image:

```bash
python3 eval/local_intelligence/launch_hf_job.py \
  --sync-code \
  --image ghcr.io/<your-github-owner>/training-lab-local-intelligence-eval:latest \
  --flavor a10g-small \
  --timeout 2h \
  --limit 24
```

Run the default model matrix:

```bash
python3 eval/local_intelligence/run_hf_matrix.py \
  --limit 24 \
  --keep-going
```

Launch the cloud batch job on HF Jobs:

```bash
python3 eval/local_intelligence/launch_hf_job.py \
  --sync-code \
  --image ghcr.io/<your-github-owner>/training-lab-local-intelligence-eval:latest \
  --flavor a10g-small \
  --timeout 2h \
  --limit 24
```

Recommended first pass:
- `google/gemma-4-E4B-it`
- `nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1`
- `Qwen/Qwen3.5-4B-Instruct-2507`

If you want results in a separate repo:

```bash
python3 eval/local_intelligence/launch_hf_job.py \
  --sync-code \
  --source-repo-id arach/training-lab \
  --results-repo-id arach/training-lab-results \
  --image ghcr.io/<your-github-owner>/training-lab-local-intelligence-eval:latest \
  --flavor a10g-small \
  --timeout 2h \
  --limit 24
```
