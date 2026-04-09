# Model Guide

Practical guide for choosing models in this repo.

Last updated: 2026-04-07 (America/Toronto)

Hosted pricing and subscription details drift. Re-check the official provider
pages in the Sources section before spending real money.

## Hosted Choices

This is the real decision surface.

| Path | How to call it | Use when | Strength | Cost shape | Notes |
|---|---|---|---|---|---|
| `github_models` | `--provider github_models --model openai/gpt-4.1-mini` | Easiest hosted sanity check | Good default anchor | Free/rate-limited or paid | Start here before getting fancy |
| `github_models` | `--provider github_models --model openai/gpt-4.1` | Stronger anchor on same easy path | Strong | Free/rate-limited or paid | Best clean comparison to `4.1-mini` |
| `openrouter` | `--provider openrouter --model anthropic/claude-sonnet-4.5` | We want a strong non-OpenAI comparison | Strong | Pay-as-you-go | Good "different family" challenger |
| `openrouter` | `--provider openrouter --model google/gemini-2.5-pro` | We want another serious frontier comparison | Strong | Pay-as-you-go | Good breadth check |
| `openrouter` | `--provider openrouter --model openai/gpt-5.4` | We want a stronger premium anchor | Very strong | Pay-as-you-go | Use sparingly |
| `openrouter` | `--provider openrouter --model x-ai/grok-4.1-fast` | We want a fast frontier-ish challenger | Strong | Pay-as-you-go | Useful for breadth, not default |
| `nous` | `--provider nous --model Hermes-4-70B` | We specifically care about Hermes | Strong | Pay-as-you-go | Best when Hermes is part of the hypothesis |
| `groq` | `--provider groq --model <cheap-open-model>` | We want cheap fast hosted runs | Medium to good | Pay-as-you-go | Best cheap hosted comparison path |
| `hf` | `--provider hf --model <hf-model-id>` | We want HF-native billing/workflows | Varies | Credits + pay-as-you-go | Better for HF-shaped infra than quick comparison |

## My Heuristics

| Goal | Call this first | Then maybe | Avoid |
|---|---|---|---|
| Quick benchmark sanity check | `github_models` + `openai/gpt-4.1-mini` | `github_models` + `openai/gpt-4.1` | Big sweeps on `openrouter` |
| Strong hosted comparison | `github_models` + `openai/gpt-4.1` | `openrouter` + `claude-sonnet-4.5` or `gemini-2.5-pro` | jumping straight to 5+ models |
| Premium frontier check | `openrouter` + `openai/gpt-5.4` | one more challenger only | repeated premium runs before the eval is stable |
| Cheap hosted comparison | `groq` | lower-cost `openrouter` models | expensive frontier models |
| Hermes question | `nous` + `Hermes-4-70B` | compare once against `gpt-4.1` | broad catalog shopping |
| HF-native workflow | `hf` | HF Jobs / HF infra paths | using HF just to avoid choosing a simpler hosted path |

## What We’ve Already Used

| Path | Models already used in saved runs |
|---|---|
| `github_models` | `openai/gpt-4.1`, `openai/gpt-4.1-mini`, `openai/gpt-4o-mini` |
| `openrouter` | `openai/gpt-5.4`, `anthropic/claude-sonnet-4.5`, `google/gemini-2.5-pro`, `x-ai/grok-4-fast`, `x-ai/grok-4.1-fast`, `x-ai/grok-3-mini`, `meta-llama/llama-3.3-70b-instruct`, `meta-llama/llama-3.1-8b-instruct`, `mistralai/mistral-small-2603`, `nousresearch/hermes-2-pro-llama-3-8b`, `nvidia/nemotron-3-super-120b-a12b` |
| `nous` | `Hermes-4-70B` |
| `mlx` | `mlx-community/Llama-3.2-1B-Instruct-4bit`, `mlx-community/Qwen2.5-0.5B-Instruct-4bit`, `mlx-community/Qwen2.5-1.5B-Instruct-4bit` |

## Local / Free Appendix

These are simpler and usually do not require much strategy.

| Path | How to call it | Use when |
|---|---|---|
| `replay` | `--provider replay --replay-file <file>` | We are changing grading and want deterministic reruns |
| `apple` | `--provider apple --apple-command <bridge>` | We want Apple on-device product plausibility |
| `mlx` | `--provider mlx --model <mlx-model>` | We want local open-model runs on this machine |
| `mlx_vlm` | `--provider mlx_vlm --model <mlx-model>` | A specific local model wants this path |
| `ollama` | `--provider ollama --model <ollama-model>` | The local server path is easier than MLX |

Open-model shortlist already noted in
[eval/local_intelligence/model_candidates.md](/Users/arach/dev/lab/eval/local_intelligence/model_candidates.md):

- `mlx-community/NVIDIA-Nemotron-3-Nano-4B-4bit`
- `mlx-community/gemma-4-e4b-it-mxfp8`
- `mlx-community/Qwen3.5-2B-4bit`

## For This Repo Right Now

For the current `title_intent_v1` work:

1. `github_models` + `openai/gpt-4.1-mini`
2. `github_models` + `openai/gpt-4.1`
3. one strong third-party challenger:
   `openrouter` or `nous`
4. one cheap hosted comparison:
   `groq`
5. only then local `mlx`

## Sources

- [GitHub Models billing](https://docs.github.com/en/billing/concepts/product-billing/github-models)
- [OpenRouter pricing](https://openrouter.ai/pricing)
- [OpenRouter FAQ](https://openrouter.ai/docs/faq)
- [Hugging Face Inference Providers pricing](https://huggingface.co/docs/inference-providers/en/pricing)
- [Hugging Face pricing](https://huggingface.co/pricing)
- [Groq pricing](https://groq.com/pricing)
- [Nous Portal models](https://portal.nousresearch.com/models)
- [Apple Foundation Models docs](https://developer.apple.com/documentation/FoundationModels)
