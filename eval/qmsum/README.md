# QMSum Pilot

This folder holds a lightweight experiment harness for kicking the tires on
QMSum as an external calibration benchmark for memo and meeting understanding.

The pilot is intentionally small:

- downloads the official QMSum split from the Yale-LILY repo
- samples real query/answer pairs
- builds clipped transcript excerpts from the annotated relevant spans
- runs the prompt through an existing provider from `eval/local_intelligence`
- reports simple lexical overlap metrics plus raw model outputs

It is not meant to replace the local benchmark. It is a separate external
calibration experiment.

## Metrics

The pilot now reports:

- `token_f1`: lightweight lexical overlap
- `rouge_l_f1_approx`: cheap local approximation
- `rouge1_f1`, `rouge2_f1`, `rougeL_f1`: proper ROUGE, if `rouge-score` is installed
- `bertscore_f1`: semantic similarity, if `bert-score` and its runtime deps are installed

The overlap metrics are useful baselines, but they should not be treated as the
final truth metric for memo understanding.

## Typical run

```bash
GH_TOKEN="$(gh auth token)" \
python eval/qmsum/run_qmsum_pilot.py \
  --provider github_models \
  --model openai/gpt-4.1 \
  --split test \
  --query-mode specific \
  --limit 5
```

To enable proper ROUGE and BERTScore:

```bash
python3 -m pip install -r eval/qmsum/requirements.txt
```

## Output

Results are written to `eval/qmsum/results/`.

Each run stores:

- the sampled query cases
- the transcript excerpt shown to the model
- the gold answer
- the model answer
- token F1
- ROUGE scores when available
- BERTScore when available
- latency

## Why clipped excerpts?

Full QMSum meetings can be very long. For this pilot, specific queries are
paired with the gold `relevant_text_span` plus a small context window so we can
quickly test whether a model can answer the right question from the right slice
of meeting context.
