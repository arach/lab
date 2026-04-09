# Colab Quickstart

Use this when we want one strong open-weight model on the news-summarization benchmark without depending on hosted API limits.

Recommended first model:

- `Qwen/Qwen3.5-8B-Instruct-2507`

Good heavier option if the Colab runtime can handle it:

- `Qwen/Qwen3.5-14B-Instruct-2507`

## Colab Setup

Runtime:

- `GPU`
- ideally `A100` or `L4`

Install deps:

```bash
!pip install -q transformers accelerate sentencepiece bert-score rouge-score
```

Clone the repo and enter it:

```bash
!git clone https://github.com/arach/lab.git
%cd /content/lab
```

Run a first 50-case pass:

```bash
!python eval/news_summarization/run_hf_transformers.py \
  --model Qwen/Qwen3.5-8B-Instruct-2507 \
  --limit 50 \
  --prompt-style simple \
  --trust-remote-code \
  --dtype bfloat16 \
  --verbose
```

Resume if the Colab runtime disconnects:

```bash
!python eval/news_summarization/run_hf_transformers.py \
  --model Qwen/Qwen3.5-8B-Instruct-2507 \
  --limit 50 \
  --prompt-style simple \
  --trust-remote-code \
  --dtype bfloat16 \
  --resume
```

## What This Gives Us

- one strong open model
- visible progress every 5 cases
- resumable output in:
  - `/content/lab/eval/news_summarization/results/`

## Suggested Comparison

Match this against the hosted frontier baseline we already ran:

- `anthropic/claude-sonnet-4.5`

That gives us:

- best hosted high-end model so far
- one serious open-weight Colab model

## Notes

- This runner uses the same dataset and scoring path as the local news pilot.
- `simple` prompt is the default because it behaved well in our earlier tests.
- For first passes, prefer `50` cases over `500`.
