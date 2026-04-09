# News Summarization Pilot

Small, paper-aligned pilot based on:

- [Evaluating Small Language Models for News Summarization: Implications and Factors Influencing Performance](https://aclanthology.org/2025.naacl-long.253/)
- benchmark repo: [Xtra-Computing/SLM_Summary_Benchmark](https://github.com/Xtra-Computing/SLM_Summary_Benchmark)

Why this exists:

- It is a cleaner first external probe for `rewrite clearly` and `what matters most` than QMSum.
- The paper found that strong SLMs can approach much larger models on summarization quality.
- The paper also found that simple prompts often work better than more detailed prompts for SLMs.

Current scope:

- dataset: `bbc2024_qwen_reference`
- reference: `qwen_reference_summary` from the released benchmark sample
- prompts:
  - `simple`: closest to the paper default
  - `helpful`: light assistant framing
  - `detailed`: tests the paper's "more prompt detail is not always better" claim

Metrics:

- `token_f1`
- `ROUGE-1 / ROUGE-2 / ROUGE-L`
- `BERTScore`
- `word_count`
- `latency_ms`

Quick run:

```bash
GH_TOKEN="$(gh auth token)" eval/qmsum/.venv/bin/python eval/news_summarization/run_news_summary_pilot.py \
  --provider github_models \
  --model openai/gpt-4.1-mini \
  --limit 5 \
  --prompt-style simple \
  --verbose
```

Compare prompt styles on the same sample:

```bash
GH_TOKEN="$(gh auth token)" eval/qmsum/.venv/bin/python eval/news_summarization/run_news_summary_pilot.py \
  --provider github_models \
  --model openai/gpt-4.1-mini \
  --limit 10 \
  --seed 7 \
  --prompt-style simple

GH_TOKEN="$(gh auth token)" eval/qmsum/.venv/bin/python eval/news_summarization/run_news_summary_pilot.py \
  --provider github_models \
  --model openai/gpt-4.1-mini \
  --limit 10 \
  --seed 7 \
  --prompt-style detailed
```

Interpretation:

- Use this as an external calibration point for memo rewrite quality, not as the whole memo eval.
- Strong scores here suggest a model may be viable for `rewrite clearly` and `what matters most`.
- Weak scores here do not say much about reminder/calendar/action extraction.

## Colab

For a strong open-weight comparison path, use:

- [`COLAB_QUICKSTART.md`](/Users/arach/dev/lab/eval/news_summarization/COLAB_QUICKSTART.md)
- [`run_hf_transformers.py`](/Users/arach/dev/lab/eval/news_summarization/run_hf_transformers.py)
- [`notebook.ipynb`](/Users/arach/dev/lab/eval/news_summarization/notebook.ipynb)

## Hugging Face Jobs

For a more reliable cloud path than Colab:

- [`launch_hf_job.py`](/Users/arach/dev/lab/eval/news_summarization/launch_hf_job.py)

Example:

```bash
python3 eval/news_summarization/launch_hf_job.py \
  --sync-code \
  --model Qwen/Qwen2.5-7B-Instruct \
  --limit 50 \
  --disable-bertscore \
  --flavor a10g-small \
  --timeout 2h
```

This:

- syncs the news-summarization harness to `arach/training-lab`
- launches a GPU job on Hugging Face
- runs the HF transformers eval there
- uploads results back under `eval/news_summarization/results/jobs/$JOB_ID`
