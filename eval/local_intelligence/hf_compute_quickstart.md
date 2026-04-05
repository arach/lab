# Hugging Face Compute Quickstart

Use this when you want to run the 24-card local-intelligence eval pack on Hugging Face
compute without Colab or notebook sessions.

## Best option: Hugging Face Jobs

Hugging Face Jobs are available to Pro users and let you run batch commands on HF
infrastructure with a selected hardware flavor.

Recommended first models:
- `google/gemma-4-E4B-it`
- `nvidia/Llama-3.1-Nemotron-Nano-4B-v1.1`
- `Qwen/Qwen3.5-4B-Instruct-2507`

## Launch a job from this repo

```bash
python3 eval/local_intelligence/launch_hf_job.py \
  --sync-code \
  --image ghcr.io/<your-github-owner>/training-lab-local-intelligence-eval:latest \
  --flavor a10g-small \
  --timeout 2h \
  --limit 24
```

This launches a Hugging Face Job that:
- syncs the current eval harness into your HF repo
- downloads the synced harness from `arach/training-lab`
- starts from your prebuilt eval image
- runs the matrix runner on HF compute
- uploads result JSON files back into `eval/local_intelligence/results/jobs/$JOB_ID`

## Build the custom image once

```bash
chmod +x eval/local_intelligence/build_image.sh
eval/local_intelligence/build_image.sh arach/local-intelligence-eval:latest
docker push arach/local-intelligence-eval:latest
```

The Dockerfile bakes in the Python runtime dependencies so future Jobs can skip install time.

## Or publish the image with GitHub Actions

Use:
- [.github/workflows/build-local-intelligence-image.yml](/Users/arach/dev/training-lab/.github/workflows/build-local-intelligence-image.yml)

Published image shape:

```text
ghcr.io/<your-github-owner>/training-lab-local-intelligence-eval:latest
```

If you want to keep results in a separate repo:

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

## Run a single model on HF compute manually

```bash
python3 eval/local_intelligence/run_hf_transformers.py \
  --model google/gemma-4-E4B-it \
  --limit 24 \
  --verbose
```

## Run the default matrix manually

```bash
python3 eval/local_intelligence/run_hf_matrix.py \
  --limit 24 \
  --keep-going
```

## Notes

- The runner prefers a tokenizer chat template when the model exposes one.
- Use `--trust-remote-code` if a model requires it.
- Result files land under `eval/local_intelligence/results/`.
- The HF Jobs path is the best fit for repeatable batch evals; notebooks are optional, not required.
- The best long-term path is a custom image with deps preinstalled, so Jobs mostly spend time on model load and eval.
