# Training on a Mac Mini

> The model that ships isn't the one you planned. It's the one that survived your mistakes.

<!-- METADATA
slug: training-on-a-mac-mini
series: teaching-a-tiny-model-to-hear-bash
part: 2
date: 2026-03-05
tags: mlx, fine-tuning, on-device-ml, apple-silicon
author: Arach
-->

## Series context

- **Part 1** — Fine-tuned a 1.5B model to reconstruct bash from dictation. 97% accuracy, 3GB RAM, under a second on a phone.
- **Part 2** (this post) — VLM vs text-only, where to draw the line between code and model, and why picking the right model size is harder than it sounds.

---

## The plan

Part 1 proved a small model could do the job. The natural next step: try the newest, best small model and see if we can push accuracy higher.

Qwen3.5-2B was the obvious candidate. It was the latest in the Qwen small model series, it benchmarked well against models twice its size, and the 2B parameter count fit our constraint of running on phones and laptops. We set up a Colab notebook, pointed it at a free T4 GPU, and started training.

Colab worked well for this. 5,044 training examples, short sequences, small model. The free tier handled it. After 90 minutes we had 79.2% exact match on 510 of our 630 test cases.

But the path there taught us things we didn't expect about model selection.

## VLM vs text-only

The entire Qwen3.5 Small series (0.8B, 2B, 4B, 9B) are vision-language models. All of them. This isn't obvious from the model cards. If you're looking for a small Qwen to fine-tune on a text task, you might grab Qwen3.5-2B without realizing you've picked up a multimodal architecture.

For us, this caused two problems.

The first: a VL model's tokenizer is actually a `Processor` that expects multimodal input. Call `apply_chat_template()` with plain text messages and it crashes:

```
TypeError: string indices must be integers
```

The workaround is to bypass the Processor and talk to the text tokenizer underneath it, then format your prompts by hand using the model's chat markup instead of the template function. It works, but it's fragile and undocumented.

The second: Qwen3.5 has a thinking mode that's on by default. If you don't explicitly close the think block in your prompt, the model burns all its output tokens on internal reasoning about your one-line bash command. We ran a full eval pass and got 0/30 exact matches before we realized what was happening. Every response was reasoning tokens. No actual answer.

Both problems have fixes. But they're friction that vanishes with a text-only model. When we later switched to Qwen3-1.7B (part of the older Qwen3 series, text-only), the standard template function worked out of the box and thinking mode had a clean off switch: `enable_thinking=False`.

If your fine-tuning job is text in, text out, start with a text-only model. The multimodal models carry assumptions about input format and generation behavior that you'll spend hours working around for zero benefit.

## Where does code end and the model begin?

Part 1 ended with a split architecture. Some inputs can be reconstructed with plain string substitution: "git space push space dash u space origin space main" maps mechanically to `git push -u origin main`. Other inputs need language understanding: "okay so the command is git push to origin on main" requires stripping the filler and normalizing the phrasing. A deterministic processor handles the first kind. An LLM handles the second.

The question that kept coming up: where exactly is the boundary?

Take "chmod space seven five five space slash etc slash nginx dot conf". Every token maps to a character. A processor handles it perfectly.

Now take "change permissions to seven fifty five on the nginx config in etsy". This needs a model. "Seven fifty five" is 755. "The nginx config" could mean `/etc/nginx.conf` or `/etc/nginx/nginx.conf`. And "etsy" is a Whisper transcription error for "/etc", which is part of the reality of working with voice input: your system has to handle upstream mistakes, not just clean dictation.

The tricky part is the middle zone. "chmod space seven five five space forward slash etsy forward slash nginx dot conf". The structure is protocol-formatted, so it looks like a processor job. But "etsy" is a transcription error hiding inside clean-looking input. A processor gets most of it right and silently gets one piece wrong.

We don't have a clean answer for the middle zone yet. The classifier gate (Part 3) routes inputs to the right handler, but the boundary between "code can handle this" and "this needs a model" is fuzzier than we expected. Some clean-looking inputs have subtle errors. Some messy-looking inputs have perfect structure underneath the filler words.

In practice, we err toward the model. A 0.7-second inference pass is better than silently wrong output from a processor that was too confident.

## The model size question

This is the part we're still figuring out.

First, a quick note on how we measure accuracy. "Exact match" means the model's output is character-for-character identical to the expected command. "Effective accuracy" includes near matches (above 90% string similarity), which in practice are whitespace differences or a trailing newline. The command is functionally correct. For a keyboard dictation product, effective accuracy is the number that matters: does the user get the right command?

With that in mind:

| Model | Params | Type | Exact | Effective | Training |
|-------|--------|------|-------|-----------|----------|
| Qwen2.5-1.5B | 1.5B | text-only | — | 97% | MLX, local |
| Qwen3.5-2B | 2B | VLM | 79.2%* | — | Unsloth, Colab T4 |
| Qwen3-1.7B | 1.7B | text-only | 67.8% | 93.3% | MLX, Mac Mini M4 |

*Partial eval (510/630 cases, session timed out)

The 1.7B text-only model outperformed the 2B multimodal model on the cases we could compare. Is that because text-only architectures are better for text tasks? Because the MLX training pipeline produced a cleaner signal than Colab/Unsloth? Because the Qwen3.5-2B eval was incomplete?

Probably some combination. We don't have a controlled experiment that isolates one variable. The honest answer is that at this scale, with this dataset, the difference between 1.5B and 2B parameters is small. The choice of architecture and training setup mattered more than we expected.

What we can say: for a short-sequence, constrained-vocabulary task like bash reconstruction, you don't need a big model. 1.7B parameters, 4-bit quantized to 948MB, trained in 10 minutes on an M4 Mac Mini using 4.8GB of memory. That's a model you can ship to users without asking them to clear space or give up their RAM.

## Getting it out the door

A LoRA adapter on its own is useless to end users. It's a set of weight differences that only work when paired with the original base model. To ship something standalone, you merge the adapter into the base weights ("fusing"), then quantize the merged model down to 4-bit precision.

The fused model was 3.2GB. After quantization: 948MB. We pushed it to HuggingFace as `arach/qwen3-1.7b-bash-v1` and registered it in TalkieInference, our on-device inference service that starts when needed and shuts down when idle.

It's the first model in a new "Talkie" family in the catalog. We planned to ship Qwen3.5-2B. We shipped Qwen3-1.7B.

## What's ahead

The model works. The inference service works. The next piece is the classifier gate that routes inputs to the right handler: deterministic processor for clean protocol input, on-device LLM for everything else. That's Part 3.

The whole pipeline (Whisper transcription, classifier gate, LLM normalization) runs on-device, offline, in under two seconds.

---

*Part of the [Teaching a Tiny Model to Hear Bash](/ideas/teaching-a-tiny-model-to-hear-bash) series.*
