# Build the Parakeet model yourself

> The four scripts that turn NVIDIA's Parakeet checkpoint into the 477 MB Core ML model inside Talkie, and what each one checks.

<!-- METADATA
slug: parakeet-recipe
date: 2026-11-03
tags: speech, core-ml, parakeet, quantization, evals
author: Arach
description: The four scripts that turn NVIDIA's Parakeet checkpoint into the 477 MB Core ML model inside Talkie, and what each one checks.
canonical: https://www.talkie.to/blog/parakeet-recipe
source: talkie.to
hidden: false
-->

In [We rebuilt the model that hears you](https://www.talkie.to/blog/rebuilding-parakeet), we told the story of converting NVIDIA's Parakeet to Core ML: the trace that came out wrong, the compression we chose, the tests that convinced us. This post is the recipe. The scripts are on Hugging Face at [arach/parakeet-coreml-recipe](https://huggingface.co/arach/parakeet-coreml-recipe), beside [the model they build](https://huggingface.co/arach/parakeet-tdt-0.6b-v3-coreml).

We cleaned the scripts up and ran them from scratch this week. The model they produced matched the one Vox ships: the same size, the same agreement with NVIDIA's original, and word error rates within a hundredth of a point.

1. **Trace.** `export.py` downloads NVIDIA's checkpoint and records it as four PyTorch traces, plus reference outputs to check against. *NeMo, a few minutes.*
2. **Build.** `build.py` converts the traces to Core ML and compresses the encoder to six bits per weight. *Mac, 18 minutes.*
3. **Check.** `check.py` feeds each Core ML piece the reference inputs and compares its output with NVIDIA's. *Mac, seconds.*
4. **Score.** `score.py` transcribes LibriSpeech's test sets and reports the word error rate. *Mac, 10 minutes a set.*

## What you need

Steps 2 to 4 need a Mac with Apple Silicon and macOS 15 or later. Step 1 needs NVIDIA's NeMo toolkit, which loads the checkpoint. We ran it on a Linux machine. NeMo also installs on macOS, and the trace needs no GPU, but we haven't tried that path ourselves.

Set aside about 6 GB of disk: 2.5 GB for NVIDIA's checkpoint, 2.5 GB for the traces, and 477 MB for the finished model. Scoring needs LibriSpeech's two test sets, another 700 MB.

| Step | Packages (Python 3.11 or 3.12) |
| --- | --- |
| 1 | nemo_toolkit[asr] 3.0.0 · torch 2.7.0 · huggingface_hub |
| 2 to 4 | coremltools 9.0 · torch 2.7.0 · numpy · soundfile · jiwer |

## 1 · Trace

Core ML can't read a NeMo checkpoint, but coremltools can convert a PyTorch trace, a recording of the operations a model performs on one example input. `export.py` loads the checkpoint at a pinned revision and traces four pieces: the preprocessor, which turns sound into a spectrogram; the encoder, which does most of the work; and the decoder and joint network, which pick one token at a time. It also saves NeMo's outputs on a sample recording, so later steps have something to compare with.

```bash
python export.py export sample.wav   # any 16 kHz recording under 15 seconds
```

The one thing to get right is the model's mode. A trace records whatever the code does while it watches, and in training mode Parakeet's encoder drops a random tenth of its values and normalizes each recording by its own statistics. NeMo's `transcribe()` leaves the encoder in training mode. Trace after calling it, as we first did, and the encoder agrees with NVIDIA's at 0.74 instead of 1.0. The script traces first and refuses to run if any part of the model is still training:

```python
assert not any(m.training for m in model.modules()), "trace in evaluation mode"
```

## 2 · Build

`build.py` converts each trace with coremltools and writes a folder Vox can load. The preprocessor keeps 32-bit precision, because the spectrogram is sensitive to rounding and any error flows into everything after it. The other pieces use 16 bits.

```bash
python build.py export parakeet-coreml
```

Then the encoder is compressed. Its weights are split into groups of 16 output channels, and each group gets a palette of 64 values chosen by k-means clustering. Each weight becomes a six-bit pointer into its group's palette. That takes the encoder from 1.2 GB to 440 MB, and the clustering is why this step takes 18 minutes on an M2 MacBook Air.

```python
cto.OpPalettizerConfig(
    mode="kmeans", nbits=6,
    granularity="per_grouped_channel", group_size=16,
)
```

<figure class="lab-figure">
<img src="/lab/ideas/parakeet-recipe/f-pal.png" alt="Weights from one group of the encoder, and the 64 values its palette keeps" width="640" height="497" loading="lazy" />
<figcaption><span>One group of 16 output channels in layer 12</span><a href="https://www.talkie.to/blog/parakeet-recipe#f-pal">Interactive on talkie.to ↗</a></figcaption>
</figure>

With six bits, each weight slides to the nearest of its group's 64 values. A typical weight moves by under 3% of its size, and each layer still scores 0.9996 against NVIDIA's. The encoder as a whole scores lower, 0.984, because 24 layers of small errors add up.

The file names and inputs follow FluidInference's earlier conversion, so either folder drops into Vox. The script also patches one coremltools function: version 9.0 fails on the one-element arrays NeMo uses to track audio length when NumPy 2 is installed.

## 3 · Check

`check.py` runs each Core ML piece on the inputs saved in step 1 and measures cosine similarity with NeMo's outputs. At 1.0 the two point the same way. The last two lines ask whether the joint network picks the same token and duration NeMo did.

```bash
python check.py export parakeet-coreml
{
 "preprocessor": 1.0,
 "encoder": 0.984,
 "decoder": 1.0,
 "joint_token": true,
 "joint_duration": true
}
```

The encoder's 0.984 is what six-bit compression costs. Before compression it scored 0.9966, and an encoder traced in training mode scores near 0.74, so a number far below 0.98 means something went wrong upstream.

<figure class="lab-figure">
<img src="/lab/ideas/parakeet-recipe/f-ck.png" alt="A scale of encoder cosine scores with the measured builds marked" width="640" height="259" loading="lazy" />
<figcaption><span>Where a check.py score falls · axis split at 0.97</span><a href="https://www.talkie.to/blog/parakeet-recipe#f-ck">Interactive on talkie.to ↗</a></figcaption>
</figure>

## 4 · Score

Agreement on one recording is a good sign, not proof. `score.py` transcribes a LibriSpeech test set the way Vox does, in 15-second windows with greedy decoding, and scores the text against LibriSpeech's own transcripts.

```bash
python score.py parakeet-coreml export LibriSpeech/test-clean clean.jsonl
```

| Word error rate | test-clean | test-other |
| --- | ---: | ---: |
| **Rebuilt with the recipe** | **2.77%** | **4.12%** |
| Shipped in Vox | 2.76% | 4.11% |

Full test sets, about 52,000 words each.

The rebuild and the shipped model wrote identical text for 2,611 of the 2,620 clean recordings and 2,935 of the 2,939 harder ones. They differ at all because k-means starts from random points, so two runs settle on slightly different palettes. Most of the differences are a comma or a capital letter, which the score ignores.

<figure class="lab-figure">
<img src="/lab/ideas/parakeet-recipe/f-df.png" alt="The 13 recordings where the rebuilt and shipped models wrote different text" width="640" height="1246" loading="lazy" />
<figcaption><span>Where the rebuild and the shipped model disagree</span><a href="https://www.talkie.to/blog/parakeet-recipe#f-df">Listen on talkie.to ↗</a></figcaption>
</figure>

## Using the result

The output folder is a drop-in replacement for the model Vox downloads. Talkie gets it through Vox, so most people never need to build it. The recipe is for checking our work, for converting a later Parakeet release, or for trying a different compression and measuring what it costs.

---

*Parakeet TDT 0.6B v3 © NVIDIA, CC-BY-4.0. Toolchain: NeMo 3.0.0 · torch 2.7.0 · coremltools 9.0 · macOS 15+ on Apple Silicon.*
